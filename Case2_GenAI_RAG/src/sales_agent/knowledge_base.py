"""Knowledge base: PDF loading, chunking, embedding and a FAISS vector index persisted to disk."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import faiss
import numpy as np
import pymupdf
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import Settings

log = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    source: str
    page: int
    chunk_id: int

    @property
    def citation(self) -> str:
        return f"{self.source}, p.{self.page}"


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float          # cosine similarity, 1.0 = identical


# Legacy Thai fonts draw shifted tone marks / vowels as Private Use Area glyphs (U+F700-U+F71A); map them back to
# standard Thai, e.g. U+F70A -> U+0E48 (mai ek) and U+F70E -> U+0E4C (thanthakhat), so the JustOne leaflet
# reads "ซ่อมอู่" and "กรมธรรม์" instead of "ซอมอู" and "กรมธรรม".
THAI_PUA = {
    0xF700: 0x0E10, 0xF701: 0x0E34, 0xF702: 0x0E35, 0xF703: 0x0E36, 0xF704: 0x0E37, 0xF705: 0x0E48,
    0xF706: 0x0E49, 0xF707: 0x0E4A, 0xF708: 0x0E4B, 0xF709: 0x0E4C, 0xF70A: 0x0E48, 0xF70B: 0x0E49,
    0xF70C: 0x0E4A, 0xF70D: 0x0E4B, 0xF70E: 0x0E4C, 0xF70F: 0x0E0D, 0xF710: 0x0E31, 0xF711: 0x0E4D,
    0xF712: 0x0E47, 0xF713: 0x0E48, 0xF714: 0x0E49, 0xF715: 0x0E4A, 0xF716: 0x0E4B, 0xF717: 0x0E4C,
    0xF718: 0x0E38, 0xF719: 0x0E39, 0xF71A: 0x0E3A}


class PdfLoader:
    """Extracts text page by page from every PDF in a folder, plus a label per page.

    PyMuPDF is used because pypdf drops Thai tone marks and upper vowels. Text lines that share a baseline are
    joined, so a table row ("รายปี 36,500 109,500 ...") stays on one line instead of one line per cell.
    Each page is labelled "document title › section": the title is the largest text on page 1 and the section is the
    latest heading (text at least SECTION_RATIO of the title size), carried over to later pages until the next one.
    In a catalogue PDF with many products this tells every chunk which product it belongs to."""

    ROW_TOLERANCE = 3.0     # points: lines whose baselines differ by less than this belong to the same row
    SECTION_RATIO = 0.6     # headings are at least 60% of the title's font size (16 pt vs 22 pt in the catalogues)

    def __init__(self):
        self.titles: dict[str, str] = {}
        self.labels: dict[tuple[str, int], str] = {}

    @staticmethod
    def _lines(page: pymupdf.Page) -> list[tuple[float, float, float, str]]:
        """(baseline y, x, font size, text) for every non-empty text line."""
        return [(line["bbox"][3], line["bbox"][0], max(span["size"] for span in line["spans"]), text)
                for block in page.get_text("dict")["blocks"] for line in block.get("lines", [])
                if (text := "".join(span["text"] for span in line["spans"]).translate(THAI_PUA).strip())]

    @classmethod
    def title(cls, page: pymupdf.Page) -> str:
        lines = cls._lines(page)
        if not lines:
            return ""
        top = max(size for _, _, size, _ in lines)
        return next(text for _, _, size, text in lines if size >= top - 0.5)

    @classmethod
    def page_text(cls, page: pymupdf.Page) -> str:
        rows: list[list[tuple[float, str]]] = []
        row_y = None
        for y, x, _, text in sorted(cls._lines(page)):
            if row_y is None or abs(y - row_y) > cls.ROW_TOLERANCE:
                rows.append([])
                row_y = y
            rows[-1].append((x, text))
        return "\n".join(" ".join(text for _, text in sorted(row)) for row in rows)

    def load(self, folder: Path) -> list[tuple[str, int, str]]:
        pdfs = sorted(Path(folder).glob("*.pdf"))
        if not pdfs:
            raise FileNotFoundError(f"No PDF files found in {folder}")
        pages = []
        for pdf in pdfs:
            doc = pymupdf.open(pdf)
            title = self.titles[pdf.name] = self.title(doc[0]) if len(doc) else ""
            title_size = max((size for _, _, size, _ in self._lines(doc[0])), default=0) if len(doc) else 0
            section = ""
            for number, page in enumerate(doc, start=1):
                heads = [text for _, _, size, text in sorted(self._lines(page))
                         if text != title and size >= self.SECTION_RATIO * title_size]
                section = heads[0] if heads else section
                self.labels[(pdf.name, number)] = f"{title} › {section}" if section else title
                text = self.page_text(page).strip()
                if text:
                    pages.append((pdf.name, number, text))
            log.info("Loaded %s (title: %s)", pdf.name, title)
        return pages


class TextChunker:
    """Splits page text into overlapping chunks that keep paragraphs together where possible."""

    def __init__(self, size: int, overlap: int):
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap,
                                                       separators=["\n\n", "\n", ". ", " ", ""])

    def split(self, pages: list[tuple[str, int, str]], titles: dict | None = None) -> list[Chunk]:
        """With labels (keyed by (source, page) or by source), each chunk starts with its label, so a passage such as
        a premium table that never names its product is still matched to (and read as) the right product."""
        chunks = []
        titles = titles or {}
        for source, page, text in pages:
            title = titles.get((source, page)) or titles.get(source, "")
            for piece in self.splitter.split_text(text):
                if title and not piece.startswith(title):
                    piece = f"{title}\n{piece}"
                chunks.append(Chunk(piece, source, page, len(chunks)))
        return chunks


class FaissVectorStore:
    """Cosine-similarity index: L2-normalised embeddings in a FAISS inner-product index."""

    INDEX_FILE, META_FILE = "index.faiss", "chunks.json"

    def __init__(self, embeddings: OllamaEmbeddings):
        self.embeddings = embeddings
        self.index: faiss.Index | None = None
        self.chunks: list[Chunk] = []

    @staticmethod
    def _normalise(vectors: list[list[float]]) -> np.ndarray:
        arr = np.asarray(vectors, dtype="float32")
        faiss.normalize_L2(arr)
        return arr

    def build(self, chunks: list[Chunk]) -> None:
        vectors = self._normalise(self.embeddings.embed_documents([c.text for c in chunks]))
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        self.chunks = chunks

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(folder / self.INDEX_FILE))
        (folder / self.META_FILE).write_text(json.dumps([asdict(c) for c in self.chunks], ensure_ascii=False, indent=1),
                                             encoding="utf-8")

    def load(self, folder: Path) -> None:
        if not (folder / self.INDEX_FILE).exists():
            raise FileNotFoundError(f"No index in {folder}. Run: python main.py ingest")
        self.index = faiss.read_index(str(folder / self.INDEX_FILE))
        self.chunks = [Chunk(**c) for c in json.loads((folder / self.META_FILE).read_text(encoding="utf-8"))]

    def search(self, query: str, k: int) -> list[RetrievedChunk]:
        vector = self._normalise([self.embeddings.embed_query(query)])
        scores, ids = self.index.search(vector, k)
        return [RetrievedChunk(self.chunks[i], float(s)) for s, i in zip(scores[0], ids[0]) if i >= 0]


class KnowledgeBase:
    """Facade used by the agent: ingest PDFs once, then retrieve relevant chunks."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = FaissVectorStore(OllamaEmbeddings(model=settings.embed_model, base_url=settings.ollama_base_url))

    def ingest(self) -> int:
        loader = PdfLoader()
        pages = loader.load(self.settings.knowledge_dir)
        chunks = TextChunker(self.settings.chunk_size, self.settings.chunk_overlap).split(pages, loader.labels)
        log.info("Embedding %d chunks from %d pages with %s", len(chunks), len(pages), self.settings.embed_model)
        self.store.build(chunks)
        self.store.save(self.settings.index_dir)
        return len(chunks)

    def load(self) -> "KnowledgeBase":
        self.store.load(self.settings.index_dir)
        return self

    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        hits = self.store.search(query, k or self.settings.top_k)
        return [h for h in hits if h.score >= self.settings.min_relevance]

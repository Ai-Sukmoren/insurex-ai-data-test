"""Knowledge base: PDF loading, chunking, embedding and a FAISS vector index persisted to disk."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import faiss
import numpy as np
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

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


class PdfLoader:
    """Extracts text page by page from every PDF in a folder."""

    def load(self, folder: Path) -> list[tuple[str, int, str]]:
        pdfs = sorted(Path(folder).glob("*.pdf"))
        if not pdfs:
            raise FileNotFoundError(f"No PDF files found in {folder}")
        pages = []
        for pdf in pdfs:
            for number, page in enumerate(PdfReader(pdf).pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append((pdf.name, number, text))
            log.info("Loaded %s", pdf.name)
        return pages


class TextChunker:
    """Splits page text into overlapping chunks that keep paragraphs together where possible."""

    def __init__(self, size: int, overlap: int):
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap,
                                                       separators=["\n\n", "\n", ". ", " ", ""])

    def split(self, pages: list[tuple[str, int, str]]) -> list[Chunk]:
        chunks = []
        for source, page, text in pages:
            for piece in self.splitter.split_text(text):
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
        pages = PdfLoader().load(self.settings.knowledge_dir)
        chunks = TextChunker(self.settings.chunk_size, self.settings.chunk_overlap).split(pages)
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

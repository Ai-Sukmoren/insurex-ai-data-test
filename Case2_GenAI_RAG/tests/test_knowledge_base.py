from dataclasses import replace

from conftest import FakeEmbeddings
from sales_agent.config import Settings
from sales_agent.knowledge_base import Chunk, FaissVectorStore, KnowledgeBase, PdfLoader, TextChunker


def test_loader_reads_all_pdfs_with_clean_thai():
    folder = Settings().knowledge_dir
    pages = PdfLoader().load(folder)
    assert {source for source, _, _ in pages} == {p.name for p in folder.glob("*.pdf")}
    assert all(text for _, _, text in pages)
    text = "\n".join(t for source, _, t in pages if source == "Khum_Mangmee_18-9.pdf")
    assert "เบี้ยประกัน" in text                                       # tone mark kept (pypdf gave "เบี ย")
    assert "รายปี 36,500 109,500 182,000 362,000" in text               # table row kept on one line
    leaflet = "\n".join(t for source, _, t in pages if source == "justone_leaflets.pdf")
    assert "ซ่อมอู่" in leaflet and not any(0xF700 <= ord(ch) <= 0xF71F for ch in leaflet)   # legacy PUA marks mapped


def test_loader_titles_are_product_names():
    loader = PdfLoader()
    loader.load(Settings().knowledge_dir)
    assert loader.titles["Khum_Aomsook.pdf"] == "คุ้มออมสุข"
    assert loader.titles["Khum_Mangmee_18-9.pdf"] == "คุ้มมั่งมี 18/9"


def test_chunker_prefixes_document_title():
    chunks = TextChunker(size=200, overlap=20).split([("a.pdf", 2, "รายเดือน 878 2,635 4,346 " * 20)], {"a.pdf": "คุ้มออมสุข"})
    assert len(chunks) > 1 and all(c.text.startswith("คุ้มออมสุข\n") for c in chunks)


def test_chunker_keeps_source_and_page():
    chunks = TextChunker(size=200, overlap=20).split([("doc.pdf", 3, "word " * 200)])
    assert len(chunks) > 1
    assert all(c.citation == "doc.pdf, p.3" for c in chunks)
    assert [c.chunk_id for c in chunks] == list(range(len(chunks)))


def test_faiss_store_build_save_load_search(tmp_path):
    chunks = [Chunk("PA Plus premium is 890 THB", "a.pdf", 1, 0),
              Chunk("Health waiting period is 30 days", "b.pdf", 1, 1),
              Chunk("Claim by phone", "c.pdf", 1, 2)]
    store = FaissVectorStore(FakeEmbeddings())
    store.build(chunks)
    store.save(tmp_path)
    loaded = FaissVectorStore(FakeEmbeddings())
    loaded.load(tmp_path)
    hits = loaded.search("waiting period", k=2)
    assert hits[0].chunk.source == "b.pdf"
    assert hits[0].score >= hits[1].score


def test_retrieve_applies_relevance_floor(tmp_path):
    kb = KnowledgeBase(replace(Settings(), min_relevance=0.99))
    kb.store = FaissVectorStore(FakeEmbeddings())
    kb.store.build([Chunk("PA Plus premium", "a.pdf", 1, 0), Chunk("tax rules", "b.pdf", 1, 1)])
    assert all(h.score >= 0.99 for h in kb.retrieve("tax"))

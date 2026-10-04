from dataclasses import replace

from conftest import ROOT, FakeEmbeddings
from sales_agent.config import Settings
from sales_agent.knowledge_base import Chunk, FaissVectorStore, KnowledgeBase, PdfLoader, TextChunker


def test_loader_reads_all_sample_pdfs():
    pages = PdfLoader().load(ROOT / "knowledge_base")
    assert len({source for source, _, _ in pages}) == 5
    assert all(text for _, _, text in pages)


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

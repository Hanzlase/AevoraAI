"""Unit tests for Phase 02 RAG pipeline modules and search services."""

import numpy as np
import pytest

from app.rag.chunking import (
    check_source_consistency,
    merge_and_deduplicate_chunks,
)
from app.rag.config import RAGSettings
from app.rag.hybrid_search import HybridSearchService
from app.rag.json_loader import JSONSourceLoader, compute_chunk_id
from app.rag.keyword_search import BM25KeywordSearch
from app.rag.normalization import (
    detect_language_script,
    expand_query_aliases,
    normalize_urdu,
    tokenize_for_bm25,
)
from app.rag.pdf_loader import PDFSourceLoader
from app.rag.schemas import ChunkMetadata, DatasetManifest
from app.rag.vector_store import FAISSVectorStore


def test_json_loader_validates_and_extracts_canonical_chunks(tmp_path) -> None:
    """Test JSON loader loads canonical structure and yields structured chunks with provenance."""
    sample_json = {
        "dataset_name": "Test Clinic",
        "dataset_version": "1.0",
        "clinic": {
            "name": "NovaCare Test",
            "tagline": "Test Tag",
            "address": "Islamabad",
            "landmark": "Opposite Park",
            "phone": "051-1234567",
            "email": "test@novacare.example",
            "website": "https://novacare.example",
            "hours": [{"day": "Monday", "open": "09:00", "close": "18:00"}],
            "holiday_policy": "Check reception",
            "parking": "Basement",
            "accessibility": "Step-free",
            "payment_methods": ["Cash", "Card"],
            "insurance": "Self-pay",
        },
        "doctors": [
            {
                "doctor_id": "DOC-001",
                "name": "Dr Ayesha Rahman",
                "specialty": "Family Medicine",
                "qualifications": "MBBS",
                "schedule": "Mon-Fri 10am-2pm",
                "consultation_fee_pkr": 2500,
                "follow_up_fee_pkr": 1800,
                "follow_up_window": "7 days",
                "booking_note": "Request only",
            }
        ],
        "services": [{"name": "Consultation", "details": "General", "availability": "Mon-Fri"}],
        "appointment_policy": {"cancellation": "4 hours prior", "walk_ins": "Allowed if capacity"},
        "faq": [{"q": "Where are you?", "a": "Islamabad"}],
        "assistant_boundaries": {"role": "Receptionist", "allowed": [], "not_allowed": []},
    }

    test_file = tmp_path / "test_truth.json"
    import json

    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(sample_json, f)

    loader = JSONSourceLoader(test_file)
    chunks = loader.extract_chunks()

    assert len(chunks) >= 5
    # Check clinic chunk
    clinic_chunk = next(c for c in chunks if c.category == "clinic_info")
    assert "NovaCare Test" in clinic_chunk.text
    assert clinic_chunk.json_pointer == "/clinic"
    assert len(clinic_chunk.chunk_id) == 16

    # Check doctor chunk retains entity relationships
    doc_chunk = next(c for c in chunks if c.category == "doctor")
    assert "Dr Ayesha Rahman" in doc_chunk.text
    assert "2500 PKR" in doc_chunk.text
    assert doc_chunk.entity_id == "DOC-001"


def test_deterministic_chunk_id() -> None:
    """Ensure chunk IDs are deterministic and reproducible across multiple executions."""
    id1 = compute_chunk_id("doc.json", "/doctors/0", "Doctor Ayesha Fee: 2500 PKR")
    id2 = compute_chunk_id("doc.json", "/doctors/0", "Doctor Ayesha Fee: 2500 PKR")
    id3 = compute_chunk_id("doc.json", "/doctors/0", "Doctor Ayesha Fee: 3000 PKR")

    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 16


def test_unicode_and_urdu_normalization() -> None:
    """Verify Urdu diacritic stripping and Arabic character conversion."""
    # Arabic kaf ك to Urdu ک, Arabic yeh ي to Urdu ی
    arabic_urdu = "ڈاكٹر ثنا شكريہ"  # contains Arabic kaf and yeh
    normalized = normalize_urdu(arabic_urdu)
    assert "ک" in normalized
    assert "ك" not in normalized

    # Tashkeel removal
    with_tashkeel = "شُکْرِیَہ"
    without_tashkeel = normalize_urdu(with_tashkeel)
    assert without_tashkeel == "شکریہ"


def test_language_and_script_detection() -> None:
    """Verify language detection across English, Urdu script, Roman Urdu, and Mixed."""
    assert detect_language_script("What are the clinic opening hours?") == "en"
    assert detect_language_script("کلینک کے اوقات کیا ہیں؟") == "ur"
    assert detect_language_script("clinic ke timings kya hain?") == "roman_ur"
    assert detect_language_script("Dr Ali ki consultation fee kitni hai?") == "mixed"
    assert detect_language_script("12345 !@#$%") == "unknown"


def test_roman_urdu_alias_expansion() -> None:
    """Verify that Roman Urdu search terms expand aliases conservatively and non-destructively."""
    original = "Dr Sana Malik ki fee kitni hai"
    expanded = expand_query_aliases(original)
    assert "charges" in expanded
    assert "pkr" in expanded
    # Original words must remain intact
    assert "Dr Sana Malik ki fee kitni hai" in expanded


def test_tokenize_for_bm25_multilingual() -> None:
    """Ensure BM25 tokenizer preserves Urdu, English, and numeric tokens."""
    text = "Dr Sana Malik فیس 3500 PKR"
    tokens = tokenize_for_bm25(text)
    assert "dr" in tokens
    assert "sana" in tokens
    assert "فیس" in tokens
    assert "3500" in tokens


def test_pdf_extraction_real_or_fixture(tmp_path) -> None:
    """Verify PDF loader extracts page numbers, headings, and flags low text pages."""
    import pymupdf as fitz

    # Create a small synthetic PDF with 2 pages
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    # Page 1: normal text
    page1 = doc.new_page()
    page1.insert_text((50, 72), "1. Clinic Hours\nNovaCare opens at 09:00 AM.")
    # Page 2: low text
    page2 = doc.new_page()
    page2.insert_text((50, 72), "Hi")
    doc.save(str(pdf_path))
    doc.close()

    loader = PDFSourceLoader(pdf_path, low_text_threshold=20)
    pages = loader.extract_pages()

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "NovaCare opens" in pages[0].normalized_text
    assert not pages[0].is_low_text
    assert pages[1].is_low_text


def test_chunk_merging_and_deduplication() -> None:
    """Verify merging of canonical JSON chunks and PDF chunks without duplicates."""
    json_chunks = [
        ChunkMetadata(
            chunk_id="chunk_01",
            text="Doctor Ayesha Rahman consultation fee is 2500 PKR.",
            source_type="json",
            source_file="source.json",
            json_pointer="/doctors/0",
            section="doctors",
            category="doctor",
            provenance=["JSON: /doctors/0"],
        )
    ]

    pdf_chunks = [
        ChunkMetadata(
            chunk_id="chunk_02",
            # Near identical text
            text="Doctor Ayesha Rahman consultation fee is 2500 PKR.",
            source_type="pdf",
            source_file="source.pdf",
            page_number=2,
            section="Doctor Directory",
            category="doctor",
            provenance=["PDF: Page 2 (Doctor Directory)"],
        ),
        ChunkMetadata(
            chunk_id="chunk_03",
            text="Parking is available in Crescent Plaza basement.",
            source_type="pdf",
            source_file="source.pdf",
            page_number=3,
            section="Parking & Access",
            category="general_info",
            provenance=["PDF: Page 3 (Parking & Access)"],
        ),
    ]

    merged, dupes = merge_and_deduplicate_chunks(json_chunks, pdf_chunks)
    assert len(merged) == 2
    assert dupes == 1
    # Check that canonical chunk absorbed PDF provenance
    canonical = next(c for c in merged if c.chunk_id == "chunk_01")
    assert any("PDF: Page 2" in prov for prov in canonical.provenance)


def test_faiss_vector_store_build_and_search(tmp_path) -> None:
    """Verify FAISS vector store FlatIP indexing, metadata persistence, and row ID mapping."""
    settings = RAGSettings(vector_store_dir=tmp_path)
    store = FAISSVectorStore(settings)

    # Create synthetic normalized vectors (N=3, dim=4)
    raw_vecs = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.7071, 0.7071, 0.0, 0.0],
        ],
        dtype=np.float32,
    )

    chunks = [
        ChunkMetadata(
            chunk_id=f"c_{i}",
            text=f"Sample text {i}",
            source_type="json",
            source_file="f.json",
            section="sec",
            category="cat",
            provenance=[f"ptr_{i}"],
        )
        for i in range(3)
    ]

    manifest = DatasetManifest(
        dataset_name="Test",
        dataset_version="1.0",
        source_file_hashes={},
        embedding_model="dummy",
        embedding_dim=4,
        chunk_count=3,
        chunk_size=500,
        chunk_overlap=100,
        built_at="2026-11-14T00:00:00Z",
    )

    store.build_and_save(raw_vecs, chunks, manifest)

    # Search with vector aligned with index 0
    query_vec = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    results = store.search(query_vec, top_k=2)

    assert len(results) == 2
    top_chunk, score, rank = results[0]
    assert top_chunk.chunk_id == "c_0"
    assert rank == 1
    assert pytest.approx(score, 0.01) == 1.0


def test_bm25_keyword_search_build_and_search(tmp_path) -> None:
    """Verify BM25 keyword matching for exact names and medical terms."""
    settings = RAGSettings(vector_store_dir=tmp_path)
    bm25_svc = BM25KeywordSearch(settings)

    chunks = [
        ChunkMetadata(
            chunk_id="c_doc1",
            text="Dr Sana Malik is a certified dermatologist with 3500 PKR fee.",
            source_type="json",
            source_file="f.json",
            section="doctors",
            category="doctor",
        ),
        ChunkMetadata(
            chunk_id="c_doc2",
            text="Dr Hamza Qureshi is a pediatrician specializing in children care.",
            source_type="json",
            source_file="f.json",
            section="doctors",
            category="doctor",
        ),
    ]

    bm25_svc.build_and_save(chunks)

    # Search for Dr Sana
    results = bm25_svc.search("Dr Sana dermatologist", top_k=2)
    assert len(results) >= 1
    assert results[0][0].chunk_id == "c_doc1"
    assert results[0][2] == 1  # Rank 1


def test_rrf_hybrid_fusion_and_thresholding(tmp_path) -> None:
    """Verify Reciprocal Rank Fusion combines vector and keyword results accurately."""
    settings = RAGSettings(
        vector_store_dir=tmp_path,
        rrf_k=60,
        vector_weight=0.5,
        keyword_weight=0.5,
        insufficient_evidence_threshold=0.015,
    )

    class MockVectorStore:
        def search(self, qv, top_k):
            return [
                (
                    ChunkMetadata(
                        chunk_id="c1",
                        text="Clinic timing 9am to 8pm",
                        source_type="json",
                        source_file="f.json",
                        section="hours",
                        category="clinic_info",
                    ),
                    0.95,
                    1,
                )
            ]

    class MockKeywordSearch:
        def search(self, q, top_k):
            return [
                (
                    ChunkMetadata(
                        chunk_id="c1",
                        text="Clinic timing 9am to 8pm",
                        source_type="json",
                        source_file="f.json",
                        section="hours",
                        category="clinic_info",
                    ),
                    4.5,
                    1,
                )
            ]

    hybrid_svc = HybridSearchService(
        vector_store=MockVectorStore(),
        keyword_search=MockKeywordSearch(),
        settings=settings,
    )

    query_vec = np.zeros(4, dtype=np.float32)
    res = hybrid_svc.search(query="clinic timings", query_vector=query_vec, top_k=3)

    assert not res.insufficient_evidence
    assert len(res.evidence) == 1
    top_item = res.evidence[0]
    assert top_item.chunk_id == "c1"
    # RRF score = 0.5 * (1/61) + 0.5 * (1/61) = 1/61 approx 0.01639
    expected_score = round(1.0 / 61.0, 6)
    assert pytest.approx(top_item.hybrid_score, 0.001) == expected_score


def test_source_consistency_check() -> None:
    """Verify detection of factual discrepancies between JSON and PDF."""
    json_data = {
        "clinic": {"name": "NovaCare Medical Centre"},
        "doctors": [{"name": "Dr Ayesha Rahman", "consultation_fee_pkr": 2500}],
    }
    # PDF missing doctor fee
    pdf_text = "NovaCare Medical Centre. Doctor Ayesha Rahman is our chief physician."
    issues = check_source_consistency(json_data, pdf_text)

    assert len(issues) == 1
    assert issues[0].field == "doctor.Dr Ayesha Rahman.fee"
    assert issues[0].severity == "warning"

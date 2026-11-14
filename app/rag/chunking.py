"""Chunking algorithms for PDF and structured JSON records with provenance tracking."""

import re
from typing import Any

from app.rag.json_loader import compute_chunk_id
from app.rag.pdf_loader import ExtractedPDFPage
from app.rag.schemas import ChunkMetadata, ConsistencyIssue


def split_text_into_chunks(
    text: str,
    target_size: int = 500,
    overlap: int = 100,
) -> list[str]:
    """Split text into semantic chunks based on paragraphs or sentences with overlap."""
    if len(text) <= target_size:
        return [text] if text.strip() else []

    # Attempt to split by paragraphs first
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue

        if current_length + len(para_clean) <= target_size:
            current_chunk.append(para_clean)
            current_length += len(para_clean) + 1
        else:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
            # If paragraph itself exceeds target size, split by sentences
            if len(para_clean) > target_size:
                sentences = re.split(r"(?<=[.!?؟\n])\s+", para_clean)
                sub_chunk: list[str] = []
                sub_len = 0
                for sent in sentences:
                    sent_clean = sent.strip()
                    if not sent_clean:
                        continue
                    if sub_len + len(sent_clean) <= target_size:
                        sub_chunk.append(sent_clean)
                        sub_len += len(sent_clean) + 1
                    else:
                        if sub_chunk:
                            chunks.append(" ".join(sub_chunk))
                        sub_chunk = [sent_clean]
                        sub_len = len(sent_clean)
                if sub_chunk:
                    chunks.append(" ".join(sub_chunk))
                current_chunk = []
                current_length = 0
            else:
                # Retain overlap from previous paragraph if possible
                overlap_text = (
                    current_chunk[-1]
                    if (current_chunk and len(current_chunk[-1]) <= overlap)
                    else ""
                )
                current_chunk = [overlap_text, para_clean] if overlap_text else [para_clean]
                current_length = sum(len(c) for c in current_chunk) + len(current_chunk) - 1

    if current_chunk:
        joined = "\n\n".join(c for c in current_chunk if c)
        if joined and (not chunks or chunks[-1] != joined):
            chunks.append(joined)

    return chunks


def build_pdf_chunks(
    pages: list[ExtractedPDFPage],
    source_filename: str,
    target_size: int = 500,
    overlap: int = 100,
) -> list[ChunkMetadata]:
    """Generate page-aware, heading-aware chunks from extracted PDF pages."""
    pdf_chunks: list[ChunkMetadata] = []

    for page in pages:
        if page.is_low_text:
            continue

        # Skip test set pages (evaluation prompts must not be indexed as clinic facts)
        page_lower = page.normalized_text.lower()
        if "multilingual retrieval test set" in page_lower or "test set" in [
            h.lower() for h in page.headings
        ]:
            continue

        section_heading = page.headings[0] if page.headings else f"Page {page.page_number}"
        page_chunks = split_text_into_chunks(
            page.normalized_text, target_size=target_size, overlap=overlap
        )

        for chunk_idx, chunk_text in enumerate(page_chunks):
            chunk_pointer = f"page_{page.page_number}_c{chunk_idx + 1}"
            chunk_id = compute_chunk_id(source_filename, chunk_pointer, chunk_text)

            # Determine category heuristic based on heading/content
            cat = "general_info"
            text_lower = chunk_text.lower()
            if "doctor" in text_lower or "mbbs" in text_lower or "specialist" in text_lower:
                cat = "doctor"
            elif "fee" in text_lower or "pkr" in text_lower or "charges" in text_lower:
                cat = "fee_schedule"
            elif "policy" in text_lower or "appointment" in text_lower:
                cat = "policy"
            elif "hour" in text_lower or "timing" in text_lower:
                cat = "timings"

            pdf_chunks.append(
                ChunkMetadata(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    source_type="pdf",
                    source_file=source_filename,
                    page_number=page.page_number,
                    section=section_heading,
                    category=cat,
                    language_hint="en",
                    provenance=[f"PDF: Page {page.page_number} ({section_heading})"],
                )
            )

    return pdf_chunks


def check_source_consistency(
    json_data: dict[str, Any],
    pdf_text_all: str,
) -> list[ConsistencyIssue]:
    """Verify factual agreement between structured JSON and extracted PDF text."""
    issues: list[ConsistencyIssue] = []
    pdf_lower = pdf_text_all.lower()

    # 1. Check Clinic Name
    clinic_name = json_data.get("clinic", {}).get("name", "")
    if clinic_name and clinic_name.lower() not in pdf_lower:
        issues.append(
            ConsistencyIssue(
                field="clinic.name",
                json_value=clinic_name,
                pdf_value="Not found in PDF text",
                description="Clinic name defined in JSON was not located in extracted PDF text.",
                severity="conflict",
            )
        )

    # 2. Check Doctor Names and Fees
    for doc in json_data.get("doctors", []):
        d_name = doc.get("name", "")
        core_name = re.sub(r"^(dr\.?|doctor)\s+", "", d_name, flags=re.IGNORECASE).strip()
        c_fee = str(doc.get("consultation_fee_pkr", ""))

        if core_name and core_name.lower() not in pdf_lower:
            issues.append(
                ConsistencyIssue(
                    field=f"doctor.{d_name}.name",
                    json_value=d_name,
                    pdf_value="Doctor name missing from PDF",
                    description=f"Doctor '{d_name}' is listed in JSON but missing in PDF.",
                    severity="warning",
                )
            )

        if c_fee and c_fee not in pdf_text_all:
            issues.append(
                ConsistencyIssue(
                    field=f"doctor.{d_name}.fee",
                    json_value=c_fee,
                    pdf_value="Fee amount missing from PDF text",
                    description=f"Consultation fee {c_fee} PKR for {d_name} not found in PDF.",
                    severity="warning",
                )
            )

    return issues


def merge_and_deduplicate_chunks(
    json_chunks: list[ChunkMetadata],
    pdf_chunks: list[ChunkMetadata],
) -> tuple[list[ChunkMetadata], int]:
    """Merge JSON canonical chunks with PDF chunks and cross-reference matching evidence.

    Returns:
        tuple of (combined_chunks, merged_duplicates_count)
    """
    merged: list[ChunkMetadata] = []
    seen_ids: set[str] = set()
    duplicates_merged = 0

    # Index JSON chunks first as canonical source of truth
    for j_chunk in json_chunks:
        merged.append(j_chunk)
        seen_ids.add(j_chunk.chunk_id)

    # For PDF chunks, check if identical text or exact duplicate exists
    for p_chunk in pdf_chunks:
        if p_chunk.chunk_id in seen_ids:
            duplicates_merged += 1
            continue

        # Check for near-exact match with existing JSON chunk (e.g. FAQ or Doctor text)
        matched_canonical = None
        p_clean = p_chunk.text.strip().lower()

        for canonical in merged:
            c_clean = canonical.text.strip().lower()
            if p_clean in c_clean or c_clean in p_clean:
                matched_canonical = canonical
                break

        if matched_canonical:
            # Attach PDF provenance to canonical chunk rather than creating a competing duplicate
            provenance_entry = f"PDF: Page {p_chunk.page_number} ({p_chunk.section})"
            if provenance_entry not in matched_canonical.provenance:
                matched_canonical.provenance.append(provenance_entry)
            duplicates_merged += 1
        else:
            merged.append(p_chunk)
            seen_ids.add(p_chunk.chunk_id)

    return merged, duplicates_merged

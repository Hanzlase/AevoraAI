"""Loader and structured evidence extractor for NovaCare_RAG_Source_of_Truth.json."""

import hashlib
import json
from pathlib import Path
from typing import Any

from app.rag.schemas import ChunkMetadata


def compute_chunk_id(source_file: str, pointer_or_page: str, text: str) -> str:
    """Generate a stable, deterministic 16-character hexadecimal chunk ID."""
    content_key = f"{source_file}::{pointer_or_page}::{text.strip()}"
    return hashlib.sha256(content_key.encode("utf-8")).hexdigest()[:16]


class JSONSourceLoader:
    """Loads, validates, and transforms the canonical clinic JSON source of truth."""

    def __init__(self, json_path: Path | str) -> None:
        self.json_path = Path(json_path)

    def load_raw(self) -> dict[str, Any]:
        """Load and return the raw parsed JSON dictionary."""
        if not self.json_path.exists():
            raise FileNotFoundError(f"Canonical JSON source not found at: {self.json_path}")
        with open(self.json_path, encoding="utf-8") as f:
            data = json.load(f)
        return data

    def validate_schema(self, data: dict[str, Any]) -> None:
        """Validate presence of required top-level domain sections."""
        required_keys = [
            "dataset_name",
            "dataset_version",
            "clinic",
            "doctors",
            "services",
            "appointment_policy",
            "faq",
            "assistant_boundaries",
        ]
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(f"Malformed clinic JSON: missing required top-level keys {missing}")

    def extract_chunks(self) -> list[ChunkMetadata]:
        """Transform JSON source into discrete, coherent, retrievable evidence chunks."""
        data = self.load_raw()
        self.validate_schema(data)
        source_file = self.json_path.name
        chunks: list[ChunkMetadata] = []

        # 1. Clinic Overview & General Info
        clinic = data.get("clinic", {})
        hours_str = "; ".join(
            f"{h.get('day')}: {h.get('open')}-{h.get('close')}" for h in clinic.get("hours", [])
        )
        payment_str = ", ".join(clinic.get("payment_methods", []))

        clinic_text = (
            f"Clinic: {clinic.get('name')}. Tagline: {clinic.get('tagline')}.\n"
            f"Address: {clinic.get('address')}.\n"
            f"Landmark: {clinic.get('landmark')}.\n"
            f"Contact Phone: {clinic.get('phone')}. Email: {clinic.get('email')}.\n"
            f"Website: {clinic.get('website')}.\n"
            f"Operating Hours: {hours_str}.\n"
            f"Holiday Policy: {clinic.get('holiday_policy')}\n"
            f"Parking: {clinic.get('parking')}\n"
            f"Accessibility: {clinic.get('accessibility')}\n"
            f"Accepted Payment Methods: {payment_str}.\n"
            f"Insurance Policy: {clinic.get('insurance')}"
        )
        c_id = compute_chunk_id(source_file, "/clinic", clinic_text)
        chunks.append(
            ChunkMetadata(
                chunk_id=c_id,
                text=clinic_text,
                source_type="json",
                source_file=source_file,
                json_pointer="/clinic",
                section="clinic_overview",
                category="clinic_info",
                language_hint="en",
                provenance=[
                    "JSON: /clinic (Clinic General Information, Hours, Address & Policies)"
                ],
            )
        )

        # 2. Individual Doctor Profiles
        for idx, doc in enumerate(data.get("doctors", [])):
            doc_id = doc.get("doctor_id", f"DOC-{idx + 1:03d}")
            name = doc.get("name")
            specialty = doc.get("specialty")
            quals = doc.get("qualifications")
            sched = doc.get("schedule")
            c_fee = doc.get("consultation_fee_pkr")
            f_fee = doc.get("follow_up_fee_pkr")
            f_win = doc.get("follow_up_window")
            note = doc.get("booking_note")

            doc_text = (
                f"Doctor Profile: {name} (ID: {doc_id}).\n"
                f"Specialty: {specialty}.\n"
                f"Qualifications: {quals}.\n"
                f"OPD Consultation Schedule: {sched}.\n"
                f"Initial Consultation Fee: {c_fee} PKR.\n"
                f"Follow-up Consultation Fee: {f_fee} PKR (Follow-up Window: {f_win}).\n"
                f"Booking Note: {note}"
            )
            pointer = f"/doctors/{idx}"
            chunks.append(
                ChunkMetadata(
                    chunk_id=compute_chunk_id(source_file, pointer, doc_text),
                    text=doc_text,
                    source_type="json",
                    source_file=source_file,
                    json_pointer=pointer,
                    section="doctors",
                    category="doctor",
                    entity_id=doc_id,
                    language_hint="en",
                    provenance=[f"JSON: {pointer} (Doctor Profile: {name}, {specialty})"],
                )
            )

        # 3. Medical & Diagnostic Services
        for idx, svc in enumerate(data.get("services", [])):
            s_name = svc.get("name")
            s_details = svc.get("details")
            s_avail = svc.get("availability")

            svc_text = f"Clinical Service: {s_name}.\nDetails: {s_details}\nAvailability: {s_avail}"
            pointer = f"/services/{idx}"
            chunks.append(
                ChunkMetadata(
                    chunk_id=compute_chunk_id(source_file, pointer, svc_text),
                    text=svc_text,
                    source_type="json",
                    source_file=source_file,
                    json_pointer=pointer,
                    section="services",
                    category="service",
                    language_hint="en",
                    provenance=[f"JSON: {pointer} (Service: {s_name})"],
                )
            )

        # 4. Appointment Policies
        policy = data.get("appointment_policy", {})
        policy_text = (
            f"Appointment Policy & Guidelines:\n"
            f"- Booking Status: {policy.get('request_vs_confirmation')}\n"
            f"- Recommended Arrival: {policy.get('recommended_arrival')}\n"
            f"- Walk-ins: {policy.get('walk_ins')}\n"
            f"- Cancellation & Rescheduling: {policy.get('cancellation')}\n"
            f"- Late Arrival Policy: {policy.get('late_arrival')}\n"
            f"- Required Intake Information: {policy.get('required_information')}\n"
            f"- Policy for Minors: {policy.get('minors')}"
        )
        chunks.append(
            ChunkMetadata(
                chunk_id=compute_chunk_id(source_file, "/appointment_policy", policy_text),
                text=policy_text,
                source_type="json",
                source_file=source_file,
                json_pointer="/appointment_policy",
                section="appointment_policy",
                category="policy",
                language_hint="en",
                provenance=["JSON: /appointment_policy (Appointment & Cancellation Guidelines)"],
            )
        )

        # 5. Clinic FAQs (English)
        for idx, item in enumerate(data.get("faq", [])):
            q = item.get("q")
            a = item.get("a")
            faq_text = f"Question: {q}\nAnswer: {a}"
            pointer = f"/faq/{idx}"
            chunks.append(
                ChunkMetadata(
                    chunk_id=compute_chunk_id(source_file, pointer, faq_text),
                    text=faq_text,
                    source_type="json",
                    source_file=source_file,
                    json_pointer=pointer,
                    section="faq",
                    category="faq",
                    language_hint="en",
                    provenance=[f"JSON: {pointer} (FAQ: {q[:40]}...)"],
                )
            )

        # 6. Assistant Boundaries & Safety Guardrails
        bounds = data.get("assistant_boundaries", {})
        allowed_str = "; ".join(bounds.get("allowed", []))
        not_allowed_str = "; ".join(bounds.get("not_allowed", []))
        bounds_text = (
            f"Assistant Operational Scope & Boundaries:\n"
            f"Role: {bounds.get('role')}\n"
            f"Allowed Tasks: {allowed_str}.\n"
            f"Strictly Prohibited: {not_allowed_str}.\n"
            f"Emergency Response Protocol: {bounds.get('emergency_response')}\n"
            f"Unknown Fact Protocol: {bounds.get('unknown_answer')}"
        )
        chunks.append(
            ChunkMetadata(
                chunk_id=compute_chunk_id(source_file, "/assistant_boundaries", bounds_text),
                text=bounds_text,
                source_type="json",
                source_file=source_file,
                json_pointer="/assistant_boundaries",
                section="assistant_boundaries",
                category="policy",
                language_hint="en",
                provenance=[
                    "JSON: /assistant_boundaries (Safety Boundaries & Emergency Protocols)"
                ],
            )
        )

        # 7. Localized Urdu Content
        ur_data = data.get("localized_content", {}).get("ur", {})
        if ur_data:
            # Urdu Overview & Policies
            ur_overview_text = (
                f"کلینک کے اوقات اور پتہ (NovaCare Medical Centre):\n"
                f"اوقاتِ کار: {ur_data.get('clinic_hours_summary')}\n"
                f"پتہ: {ur_data.get('clinic_address')}\n"
                f"تعطیلات کی پالیسی: {ur_data.get('holiday_policy')}\n"
                f"اپائنٹمنٹ بکنگ پالیسی: {ur_data.get('appointment_confirmation')}\n"
                f"واک اِن پالیسی: {ur_data.get('walk_in_policy')}\n"
                f"منسوخی کی پالیسی: {ur_data.get('cancellation_policy')}\n"
                f"طبی اور ایمرجنسی حدود: {ur_data.get('emergency_boundary')}\n"
                f"{ur_data.get('medical_advice_boundary')}\n"
                f"ادائیگی: {ur_data.get('payment_policy')}"
            )
            chunks.append(
                ChunkMetadata(
                    chunk_id=compute_chunk_id(
                        source_file, "/localized_content/ur/overview", ur_overview_text
                    ),
                    text=ur_overview_text,
                    source_type="json",
                    source_file=source_file,
                    json_pointer="/localized_content/ur/overview",
                    section="clinic_overview_ur",
                    category="clinic_info",
                    language_hint="ur",
                    provenance=["JSON: /localized_content/ur (Urdu Clinic Information & Policies)"],
                )
            )

            # Urdu Doctors
            for idx, doc in enumerate(ur_data.get("doctors", [])):
                name = doc.get("name")
                specialty = doc.get("specialty_ur")
                sched = doc.get("schedule_ur")
                c_fee = doc.get("consultation_fee_ur")
                f_fee = doc.get("follow_up_fee_ur")
                ur_doc_text = (
                    f"ڈاکٹر تفصیلات: {name}\n"
                    f"شعبہ: {specialty}\n"
                    f"اوقات: {sched}\n"
                    f"فیس: {c_fee} {f_fee}"
                )
                pointer = f"/localized_content/ur/doctors/{idx}"
                chunks.append(
                    ChunkMetadata(
                        chunk_id=compute_chunk_id(source_file, pointer, ur_doc_text),
                        text=ur_doc_text,
                        source_type="json",
                        source_file=source_file,
                        json_pointer=pointer,
                        section="doctors_ur",
                        category="doctor",
                        entity_id=doc.get("doctor_id"),
                        language_hint="ur",
                        provenance=[f"JSON: {pointer} (Urdu Doctor Profile: {name})"],
                    )
                )

            # Urdu FAQs
            for idx, item in enumerate(ur_data.get("faq", [])):
                q = item.get("q")
                a = item.get("a")
                ur_faq_text = f"سوال: {q}\nجواب: {a}"
                pointer = f"/localized_content/ur/faq/{idx}"
                chunks.append(
                    ChunkMetadata(
                        chunk_id=compute_chunk_id(source_file, pointer, ur_faq_text),
                        text=ur_faq_text,
                        source_type="json",
                        source_file=source_file,
                        json_pointer=pointer,
                        section="faq_ur",
                        category="faq",
                        language_hint="ur",
                        provenance=[f"JSON: {pointer} (Urdu FAQ: {q[:30]}...)"],
                    )
                )

        return chunks

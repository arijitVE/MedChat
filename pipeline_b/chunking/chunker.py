from dataclasses import dataclass

from pipeline_b.schemas.input import PatientRecord


@dataclass
class QdrantChunk:
    chunk_id: str
    chunk_text: str
    payload: dict


def _make_chunk_id(job_id: str, field_name: str) -> str:
    import hashlib

    raw = f"field_{job_id}_{field_name}"
    return str(int(hashlib.sha256(raw.encode()).hexdigest()[:15], 16))


def chunk_per_field(record: PatientRecord) -> list[QdrantChunk]:
    chunks = []
    for f in record.fields:
        status = (
            "abnormal"
            if f.is_abnormal
            else "normal"
            if f.is_abnormal is False
            else "unknown"
        )
        ref_part = f"{f.ref_low}-{f.ref_high}" if f.ref_low and f.ref_high else "unknown"
        chunk_text = (
            f"{f.name} {f.value} {f.unit or ''} "
            f"reference {ref_part} status {status}"
        ).strip()

        payload = {
            "source_type": f.source_type,
            "chunk_type": "field",
            "patient_id": f.patient_id,
            "job_id": f.job_id,
            "document_type": f.document_type,
            "collection_date": f.collection_date,
            "processed_at": f.processed_at.isoformat(),
            "field_name": f.name,
            "raw_name": f.raw_name,
            "value": f.value,
            "numeric_value": f.numeric_value,
            "unit": f.unit,
            "reference_range": f.reference_range,
            "ref_low": f.ref_low,
            "ref_high": f.ref_high,
            "is_abnormal": f.is_abnormal,
            "chunk_text": chunk_text,
        }
        chunks.append(
            QdrantChunk(
                chunk_id=_make_chunk_id(f.job_id, f.name),
                chunk_text=chunk_text,
                payload=payload,
            )
        )
    return chunks


def chunk_full_document(record: PatientRecord) -> QdrantChunk:
    import hashlib

    chunk_id = str(
        int(hashlib.sha256(f"doc_{record.job_id}".encode()).hexdigest()[:15], 16)
    )
    payload = {
        "source_type": "patient",
        "chunk_type": "document",
        "patient_id": record.patient_id,
        "job_id": record.job_id,
        "document_type": record.document_type,
        "processed_at": record.processed_at.isoformat(),
        "chunk_text": record.structured_text,
    }
    return QdrantChunk(
        chunk_id=chunk_id,
        chunk_text=record.structured_text,
        payload=payload,
    )


def chunk_record(record: PatientRecord) -> list[QdrantChunk]:
    return chunk_per_field(record) + [chunk_full_document(record)]

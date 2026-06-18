# pipeline_a/orchestrator/merger.py

from shared.schemas.report import ExtractedField, ScoredField
from pipeline_a.normalization.normalizer import normalize_name, normalize_value, normalize_unit

def merge_and_normalize(fields: list[ExtractedField]) -> list[ScoredField]:
    """
    1. Normalizes names, values, units.
    2. Groups by normalized name and collection date.
    3. Deduplicates identical values (due to chunk overlap).
    """
    grouped = {}
    
    for f in fields:
        n_name = normalize_name(f.name)
        n_val = normalize_value(f.value)
        n_unit = normalize_unit(f.unit)
        
        # Unique key for deduplication
        key = (n_name, f.collection_date or "", n_val, n_unit or "")
        
        if key not in grouped:
            grouped[key] = ScoredField(
                name=n_name,
                value=n_val,
                unit=n_unit,
                reference_range=f.reference_range,
                collection_date=f.collection_date
            )
            
    return list(grouped.values())

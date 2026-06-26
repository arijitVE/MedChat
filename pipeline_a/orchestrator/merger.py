# pipeline_a/orchestrator/merger.py

from typing import List, Dict, Any, Tuple
from shared.schemas.report import ExtractedField, ScoredField
from pipeline_a.normalization.normalizer import normalize_name, normalize_value, normalize_unit

def merge_and_normalize(fields: List[ExtractedField]) -> List[ScoredField]:
    """
    1. Normalizes names, values, units.
    2. Groups by normalized name and collection date.
    3. Deduplicates identical values (due to chunk overlap).
    4. Carries trend analytics fields and computes is_abnormal deterministically.
    """
    grouped: Dict[Tuple[str, str, str, str], ScoredField] = {}
    
    for f in fields:
        n_name = normalize_name(f.name)
        n_val = normalize_value(f.value)
        n_unit = normalize_unit(f.unit)
        
        key = (n_name, f.collection_date or "", n_val, n_unit or "")
        
        if key not in grouped:
            num_val = getattr(f, "numeric_value", None)
            r_low = getattr(f, "ref_low", None)
            r_high = getattr(f, "ref_high", None)
            
            is_abn = None
            if num_val is not None and r_low is not None and r_high is not None:
                is_abn = num_val < r_low or num_val > r_high
            elif num_val is not None and r_high is not None and r_low is None:
                is_abn = num_val > r_high
            elif num_val is not None and r_low is not None and r_high is None:
                is_abn = num_val < r_low

            grouped[key] = ScoredField(
                name=n_name,
                value=n_val,
                unit=n_unit,
                reference_range=f.reference_range,
                collection_date=f.collection_date,
                numeric_value=num_val,
                ref_low=r_low,
                ref_high=r_high,
                is_abnormal=is_abn
            )
            
    return list(grouped.values())


def merge_metadata_dicts(dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge metadata dicts across chunks. First non-null non-empty value wins per key."""
    merged: Dict[str, Any] = {}
    if not dicts:
        return merged
        
    all_keys = set().union(*(d.keys() for d in dicts if isinstance(d, dict)))
    for k in all_keys:
        val = None
        for d in dicts:
            if isinstance(d, dict):
                v = d.get(k)
                if v is not None and str(v).strip() not in ("", "null", "None"):
                    val = v
                    break
        merged[k] = val
        
    return merged

import re

def _extract_range_unit(range_str: str) -> tuple[str, str | None]:
    if not range_str:
        return range_str, None
        
    range_str = range_str.strip()
    
    # List of units ordered by length (descending) to match longest first
    units = [
        "x10^3/µL", "x10^6/µL", "×10³/µL", "×10⁶/µL", "cells/µL",
        "mmol/L", "µmol/L", "mEq/L", "mg/dL", "µg/dL", "ng/mL", "pg/mL",
        "IU/mL", "mIU/mL", "g/dL", "IU/L", "mg/L", "U/L", "g/L", 
        "mm/hr", "seconds", "ratio", "%"
    ]
    
    for unit in units:
        if range_str.endswith(unit):
            idx = range_str.rfind(unit)
            cleaned = range_str[:idx].strip()
            return cleaned, unit
            
    return range_str, None


def _convert_value(value: float, from_unit: str | None, to_unit: str | None) -> float | None:
    if from_unit == to_unit:
        return value
    if from_unit is None or to_unit is None:
        return value
        
    conversion_key = (from_unit, to_unit)
    conversions = {
        ("g/L",    "g/dL"):      0.1,
        ("g/dL",   "g/L"):       10.0,
        ("mmol/L", "mg/dL"):     18.0,
        ("mg/dL",  "mmol/L"):    0.0555,
        ("µmol/L", "mg/dL"):     0.0113,
        ("mg/dL",  "µmol/L"):    88.4,
        ("×10⁶/µL","×10³/µL"):   1000.0,
        ("×10³/µL","×10⁶/µL"):   0.001,
    }
    
    if conversion_key in conversions:
        return value * conversions[conversion_key]
        
    return None


def check_abnormal(numeric_value: float | None, reference_range: str | None, field_unit: str | None = None) -> bool | None:
    # 1. Guard clauses
    if numeric_value is None:
        return None
    if reference_range is None or not reference_range.strip():
        return None
        
    # 2. Extract embedded unit from range string
    cleaned_range, range_unit = _extract_range_unit(reference_range)
    
    # 3. Unit reconciliation
    if field_unit and range_unit and field_unit != range_unit:
        converted_val = _convert_value(numeric_value, field_unit, range_unit)
        if converted_val is None:
            return None
        val_to_compare = converted_val
    else:
        val_to_compare = numeric_value
        
    # 4. Qualitative check
    qualitative_terms = {
        "negative", "positive", "reactive", "non-reactive", "non reactive",
        "absent", "present", "normal", "abnormal", "detected", "not detected", "trace"
    }
    if cleaned_range.lower() in qualitative_terms:
        return None
        
    # 5. Parse and compare
    if "+" in cleaned_range or "/" in cleaned_range:
        return None

    # Standard range "12.0-16.0" or "12.0 - 16.0" or "-5-5"
    std_range_match = re.match(r"^(-?[\d.]+)\s*[-–]\s*(-?[\d.]+)$", cleaned_range)
    if std_range_match:
        try:
            low = float(std_range_match.group(1))
            high = float(std_range_match.group(2))
            return not (low <= val_to_compare <= high)
        except ValueError:
            return None

    # Upper bound only "<15" "< 15" "<=15" "≤15" "≤ 15"
    upper_match = re.match(r"^[<≤](=?)\s*([\d.]+)$", cleaned_range)
    if upper_match:
        has_eq = upper_match.group(1) == "=" or cleaned_range.startswith("≤")
        try:
            bound = float(upper_match.group(2))
            if has_eq:
                return val_to_compare > bound
            else:
                return val_to_compare >= bound
        except ValueError:
            return None
            
    # Lower bound only ">0.5" ">= 2.5" "≥2.5"
    lower_match = re.match(r"^[>≥](=?)\s*([\d.]+)$", cleaned_range)
    if lower_match:
        has_eq = lower_match.group(1) == "=" or cleaned_range.startswith("≥")
        try:
            bound = float(lower_match.group(2))
            if has_eq:
                return val_to_compare < bound
            else:
                return val_to_compare <= bound
        except ValueError:
            return None

    # Fallback
    return None

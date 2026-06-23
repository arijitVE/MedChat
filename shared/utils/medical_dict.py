# shared/utils/medical_dict.py — Synonym maps (PCM → Paracetamol, BID → 2x/day)
# Single source of truth for all medical synonym and unit synonym maps.
#
# This file is a CONFIGURATION ARTIFACT — not business logic.
# The normalizer (pipeline_a/normalization/normalizer.py) imports from here.
# No other module should define synonym maps inline.
#
# Maintainers: Add new entries as new document types are onboarded.
# Indian labs frequently use abbreviations not found in international standards.

# ---------------------------------------------------------------------------
# MEDICAL_SYNONYMS: maps common abbreviations / alternate names → canonical
# All keys MUST be lowercase, pre-stripped. Lookup code does:
#   MEDICAL_SYNONYMS.get(name.strip().lower(), name.strip().lower())
# ---------------------------------------------------------------------------

MEDICAL_SYNONYMS: dict[str, str] = {
    # ----- Hematology -----
    "hb": "hemoglobin",
    "hgb": "hemoglobin",
    "haemoglobin": "hemoglobin",
    "tlc": "total leucocyte count",
    "wbc": "total leucocyte count",
    "wbc count": "total leucocyte count",
    "dlc": "differential leucocyte count",
    "rbc": "red blood cell count",
    "rbc count": "red blood cell count",
    "plt": "platelet count",
    "platelet": "platelet count",
    "platelets": "platelet count",
    "pcv": "packed cell volume",
    "hct": "hematocrit",
    "haematocrit": "hematocrit",
    "mcv": "mean corpuscular volume",
    "mch": "mean corpuscular hemoglobin",
    "mchc": "mean corpuscular hemoglobin concentration",
    "esr": "erythrocyte sedimentation rate",
    "rdw": "red cell distribution width",
    "mpv": "mean platelet volume",

    # ----- Liver Function -----
    "sgpt": "alanine aminotransferase",
    "alt": "alanine aminotransferase",
    "sgot": "aspartate aminotransferase",
    "ast": "aspartate aminotransferase",
    "alp": "alkaline phosphatase",
    "ggt": "gamma glutamyl transferase",
    "ggtp": "gamma glutamyl transferase",

    # ----- Kidney Function -----
    "bun": "blood urea nitrogen",
    "s. creatinine": "serum creatinine",
    "sr. creatinine": "serum creatinine",
    "s.creatinine": "serum creatinine",
    "egfr": "estimated glomerular filtration rate",
    "gfr": "estimated glomerular filtration rate",

    # ----- Lipid Profile -----
    "tc": "total cholesterol",
    "tg": "triglycerides",
    "hdl": "hdl cholesterol",
    "ldl": "ldl cholesterol",
    "vldl": "vldl cholesterol",

    # ----- Diabetes -----
    "fbs": "fasting blood sugar",
    "ppbs": "postprandial blood sugar",
    "rbs": "random blood sugar",
    "hba1c": "glycated hemoglobin",
    "a1c": "glycated hemoglobin",

    # ----- Thyroid -----
    "tsh": "thyroid stimulating hormone",
    "t3": "triiodothyronine",
    "t4": "thyroxine",
    "ft3": "free triiodothyronine",
    "ft4": "free thyroxine",

    # ----- Urine -----
    "ua": "uric acid",
    "s. uric acid": "uric acid",

    # ----- Electrolytes -----
    "na": "sodium",
    "na+": "sodium",
    "k": "potassium",
    "k+": "potassium",
    "cl": "chloride",
    "ca": "calcium",
    "ca++": "calcium",

    # ----- Drug Names (common Indian prescription abbreviations) -----
    "pcm": "paracetamol",
    "para": "paracetamol",
    "amox": "amoxicillin",
    "amoxyclav": "amoxicillin-clavulanate",
    "augmentin": "amoxicillin-clavulanate",
    "metro": "metronidazole",
    "azithro": "azithromycin",
    "azee": "azithromycin",
    "cef": "cefixime",
    "pan": "pantoprazole",
    "panto": "pantoprazole",
    "rantac": "ranitidine",
    "dolo": "paracetamol",
    "combiflam": "ibuprofen-paracetamol",

    # ----- Frequency Abbreviations -----
    "bid": "twice daily",
    "tid": "three times daily",
    "qid": "four times daily",
    "od": "once daily",
    "qd": "once daily",
    "hs": "at bedtime",
    "prn": "as needed",
    "sos": "as needed",
    "ac": "before meals",
    "pc": "after meals",
    "stat": "immediately",

    # ----- Coagulation -----
    "pt": "prothrombin time",
    "inr": "international normalized ratio",
    "aptt": "activated partial thromboplastin time",

    # ----- Miscellaneous -----
    "crp": "c-reactive protein",
    "hs-crp": "high-sensitivity c-reactive protein",
    "ana": "antinuclear antibody",
    "hiv": "human immunodeficiency virus",
    "hbsag": "hepatitis b surface antigen",
    "hcv": "hepatitis c virus",
    "lft": "liver function test",
    "kft": "kidney function test",
    "rft": "renal function test",
    "cbc": "complete blood count",
    "bp": "blood pressure",
}


# ---------------------------------------------------------------------------
# UNIT_SYNONYMS: maps case-insensitive / malformed unit strings → canonical
# All keys MUST be lowercase, pre-stripped. Lookup code does:
#   UNIT_SYNONYMS.get(unit.strip().lower(), unit)
# ---------------------------------------------------------------------------

UNIT_SYNONYMS: dict[str, str] = {
    # ----- Concentration -----
    "g/dl": "g/dL",
    "gm/dl": "g/dL",
    "g/l": "g/L",
    "mg/dl": "mg/dL",
    "mg/l": "mg/L",
    "ug/dl": "µg/dL",
    "ug/ml": "µg/mL",
    "ng/ml": "ng/mL",
    "ng/dl": "ng/dL",
    "pg/ml": "pg/mL",
    "iu/l": "IU/L",
    "iu/ml": "IU/mL",
    "u/l": "U/L",
    "u/ml": "U/mL",
    "miu/ml": "mIU/mL",
    "miu/l": "mIU/L",

    # ----- Cell Counts -----
    "cells/cumm": "cells/µL",
    "cells/cu mm": "cells/µL",
    "cells/ul": "cells/µL",
    "/cumm": "/µL",
    "/cu mm": "/µL",
    "/ul": "/µL",
    "x10^3/ul": "×10³/µL",
    "x10^6/ul": "×10⁶/µL",
    "10^3/ul": "×10³/µL",
    "10^6/ul": "×10⁶/µL",
    "thou/ul": "×10³/µL",
    "mill/ul": "×10⁶/µL",
    "lakh/cumm": "×10⁵/µL",
    "lakhs/cumm": "×10⁵/µL",

    # ----- Percentages & Ratios -----
    "%": "%",
    "percent": "%",
    "ratio": "ratio",

    # ----- Volume -----
    "fl": "fL",
    "pg": "pg",

    # ----- Time -----
    "mm/hr": "mm/hr",
    "mm/1st hr": "mm/hr",
    "mm /hr": "mm/hr",
    "sec": "seconds",
    "seconds": "seconds",

    # ----- Miscellaneous -----
    "mmol/l": "mmol/L",
    "meq/l": "mEq/L",
    "meq/dl": "mEq/dL",
    "umol/l": "µmol/L",
    "mg": "mg",
    "ml": "mL",
    "mcg": "µg",
    "gm": "g",
}

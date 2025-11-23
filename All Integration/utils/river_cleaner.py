import re
from fuzzywuzzy import fuzz

# Known river normalization dictionary
RIVER_MAP = {
    "GODAVARI": "Godavari",
    "KRISHNA": "Krishna",
    "CAUVERY": "Cauvery",
    "KAVERI": "Cauvery",
    "NARMADA": "Narmada",
    "TUNGABHADRA": "Tungabhadra",
    "PENNAR": "Pennar",
    "YAMUNA": "Yamuna",
    "GANGA": "Ganga",
    "GANGES": "Ganga",
    "BRAHMAPUTRA": "Brahmaputra",
    # Add more as needed
}

COMMON_SUFFIXES = [
    "U/S", "D/S", "B/C", "RIVER", " -", "-", "/", ","
]

def clean_river_name(name):
    if not isinstance(name, str):
        return None

    original = name.strip().upper()

    # 1 — Remove common suffixes/prefixes
    for sfx in COMMON_SUFFIXES:
        original = original.replace(sfx, "")
    
    original = re.sub(r"\s+", " ", original).strip()

    # 2 — Exact dictionary match
    if original in RIVER_MAP:
        return RIVER_MAP[original]

    # 3 — Fuzzy match with dictionary keys
    best_match = None
    best_score = 0

    for raw, clean in RIVER_MAP.items():
        score = fuzz.token_sort_ratio(original, raw)
        if score > best_score and score > 80:
            best_match = clean
            best_score = score

    if best_match:
        return best_match

    # 4 — If still unknown, return title-cased cleaned name
    return original.title()

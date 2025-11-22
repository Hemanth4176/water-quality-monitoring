# scripts/extract_by_section.py
import re
from pathlib import Path

import camelot
import pandas as pd
from pdfminer.high_level import extract_text

RAW_DIR = Path("../data/CPCB_Rivers_Main_Data")
OUT_DIR = Path("../data/extracted_csv_by_section")
OUT_DIR.mkdir(parents=True, exist_ok=True)
YEARS = list(range(2016, 2024))

# Updated regex patterns for main rivers and tributary sections
TITLE_PATTERNS = [
    r"\bWATER\s+QUALITY\s+(?:DATA\s+)?OF\s+RIVER\s+([A-Z \-/&]+?)(?:\s*[-–:]\s*20\d{2})?(?:\s|$)",
    r"\bTABLE\s*[-\s]*\d+(?:\.\d+)?\s*[:\-–]\s*WATER\s+QUALITY.*?\bRIVER\s+([A-Z \-/&]+)\b",
    r"\bWATER\s+QUALITY\s+OF\s+TRIBUTARY\s+STREAMS\s*[-:]\s*([A-Z ,\-/&]+)",
]

def detect_titles(pdf_path: Path):
    """Extract section titles from PDF page text."""
    text = extract_text(str(pdf_path))
    pages = text.split("\x0c")
    titles = {}
    current = None
    
    for i, pg in enumerate(pages, start=1):
        flat = " ".join(pg.split())
        found = None
        
        for pat in TITLE_PATTERNS:
            m = re.search(pat, flat, flags=re.IGNORECASE)
            if m:
                groups = [g for g in m.groups() if g]
                if groups:
                    found = groups[-1]
                    break
        
        if found:
            norm = re.sub(r"\(.*?\)", "", found).strip()
            norm = re.sub(r"\s+", " ", norm)
            if "TRIBUTARY" in flat.upper():
                current = f"Tributary Streams - {norm.title()}"
            else:
                current = norm.title()
        
        titles[i] = current
    return titles


def extract_waterbody_from_station(station: str) -> str:
    """Extract waterbody name from station string."""
    if not isinstance(station, str) or not station.strip():
        return ""
    s = station.upper().strip()
    
    # Match "RIVER <NAME> AT/U/S/D/S ..."
    m = re.search(r"\bRIVER\s+([A-Z/ \-]+?)\s+(AT|U/S|D/S|NEAR|NR)\b", s)
    if m:
        return m.group(1).strip()
    
    # Match "<NAME> AT/U/S/D/S ..." (fallback)
    m2 = re.search(r"\b([A-Z]{3,})\s+(AT|U/S|D/S|NEAR|NR|TO)\b", s)
    if m2:
        return m2.group(1).strip()
    
    return ""


def looks_like_code(x):
    """Check if string looks like a station code (3-6 digits)."""
    return bool(re.match(r"^\d{3,6}$", str(x).strip()))


def extract_year(name: str):
    """Extract year from filename."""
    m = re.search(r"(\d{4})", name)
    return int(m.group(1)) if m else None


def main():
    for pdf in sorted(RAW_DIR.glob("*.pdf")):
        year = extract_year(pdf.name)
        if year not in YEARS:
            continue
        
        print(f"[INFO] processing {pdf.name} (year={year})")
        
        try:
            page_titles = detect_titles(pdf)
        except Exception as e:
            print(f"[WARN] title parse failed: {e}")
            page_titles = {}
        
        # Extract tables
        tables = camelot.read_pdf(
            str(pdf),
            pages="all",
            flavor="lattice",
            strip_text="\n",
            line_scale=45
        )
        
        if tables.n == 0:
            print("[WARN] lattice found 0 tables, trying stream")
            tables = camelot.read_pdf(
                str(pdf),
                pages="all",
                flavor="stream",
                strip_text="\n"
            )
        
        frames = []
        for t in tables:
            # Get page number and section title
            page_no = int(t.parsing_report.get("page", 1)) if isinstance(t.parsing_report.get("page", 1), (int, str)) else 1
            section_title = page_titles.get(page_no, "") or ""
            
            df = t.df.copy()
            if df.empty:
                continue
            
            # Keep only rows where first column looks like station code
            df = df[df[0].astype(str).str.strip().apply(looks_like_code)].copy()
            if df.empty:
                continue
            
            # Pad to at least 18 columns (9 parameter pairs: min/max)
            # Actual structure: code, station, state, temp_min, temp_max, do_min, do_max, ph_min, ph_max,
            #                   cond_min, cond_max, bod_min, bod_max, nitrate_min, nitrate_max,
            #                   fecal_min, fecal_max, total_coli_min, total_coli_max
            max_cols = max(df.shape[1], 19)
            df = df.reindex(columns=list(range(max_cols)), fill_value="")
            
            # Map 19 columns to semantic names (8 parameter pairs, no fecal_strep)
            column_map = {
                0: "code",
                1: "station",
                2: "state",
                3: "temp_min",
                4: "temp_max",
                5: "do_min",
                6: "do_max",
                7: "ph_min",
                8: "ph_max",
                9: "cond_min",
                10: "cond_max",
                11: "bod_min",
                12: "bod_max",
                13: "nitrate_min",
                14: "nitrate_max",
                15: "fecal_min",
                16: "fecal_max",
                17: "total_coli_min",
                18: "total_coli_max"
            }
            df = df.rename(columns=column_map)
            
            # Normalize text columns
            for col in ["station", "state"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
            
            # Extract waterbody name from station
            df["waterbody"] = df["station"].apply(extract_waterbody_from_station)
            
            # Add metadata
            df["year"] = year
            df["section_title"] = section_title.strip()
            
            frames.append(df)
        
        if not frames:
            print(f"[WARN] no valid tables for {pdf.name}")
            continue
        
        # Concatenate all frames for this year
        out = pd.concat(frames, ignore_index=True)
        
        # Select only the columns we want
        cols_to_keep = [
            "year", "code", "station", "state", "section_title", "waterbody",
            "temp_min", "temp_max",
            "do_min", "do_max",
            "ph_min", "ph_max",
            "cond_min", "cond_max",
            "bod_min", "bod_max",
            "nitrate_min", "nitrate_max",
            "fecal_min", "fecal_max",
            "total_coli_min", "total_coli_max"
        ]
        out = out[[c for c in cols_to_keep if c in out.columns]]
        
        # Write CSV
        out_path = OUT_DIR / f"water_quality_by_section_{year}.csv"
        out.to_csv(out_path, index=False, encoding="utf-8")
        print(f"[OK] {year}: {len(out)} rows -> {out_path}")


if __name__ == "__main__":
    main()

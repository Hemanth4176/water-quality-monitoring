# scripts/extract_by_section.py
import re
from pathlib import Path

import camelot
import pandas as pd
from pdfminer.high_level import extract_text

RAW_DIR = Path("../data/raw_pdfs")
OUT_DIR = Path("../data/extracted_csv_by_section")
OUT_DIR.mkdir(parents=True, exist_ok=True)
YEARS = list(range(2016, 2024))

TITLE_PATTERNS = [
    r"\bWATER\s+QUALITY\s+OF\s+RIVER\s+([A-Z \-/&]+)\b",
    r"\bWATER\s+QUALITY\s+DATA\s+OF\s+RIVER\s+([A-Z \-/&]+)\b",
    r"\bTABLE\s*[-\s]*\d+(?:\.\d+)?\s*[:\-–]\s*WATER\s+QUALITY.*?\bRIVER\s+([A-Z \-/&]+)\b",
    r"\bWATER\s+QUALITY\s+OF\s+TRIBUTARY\s+STREAMS\s*[-:]\s*([A-Z ,\-/&]+)\b",
]

def detect_titles(pdf_path: Path):
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

def looks_like_code(x):
    return bool(re.match(r"^\d{3,6}$", str(x).strip()))

def extract_year(name: str):
    m = re.search(r"(\d{4})", name)
    return int(m.group(1)) if m else None

def main():
    for pdf in sorted(RAW_DIR.glob("*.pdf")):
        year = extract_year(pdf.name)
        if year not in YEARS:
            continue
        print(f"[INFO] {pdf.name}")
        try:
            page_titles = detect_titles(pdf)
        except Exception as e:
            print(f"[WARN] title parse failed: {e}")
            page_titles = {}

        tables = camelot.read_pdf(str(pdf), pages="all", flavor="lattice", strip_text="\n", line_scale=45)
        if tables.n == 0:
            print("[WARN] lattice found 0 tables, trying stream")
            tables = camelot.read_pdf(str(pdf), pages="all", flavor="stream", strip_text="\n")

        frames = []
        for t in tables:
            page_no = int(t.parsing_report.get("page", 1)) if isinstance(t.parsing_report.get("page", 1), (int, str)) else 1
            section_title = page_titles.get(page_no, "") or ""
            df = t.df.copy()
            if df.empty:
                continue
            # pad columns and keep station rows
            max_cols = max(df.shape[1], 21)
            df = df.reindex(columns=list(range(max_cols)), fill_value="")
            df = df[df[0].astype(str).str.strip().apply(looks_like_code)]
            if df.empty:
                continue
            df = df.rename(columns={
                0:"code", 1:"station", 2:"state",
                3:"temp_min", 4:"temp_max",
                5:"do_min", 6:"do_max",
                7:"ph_min", 8:"ph_max",
                9:"cond_min", 10:"cond_max",
                11:"bod_min", 12:"bod_max",
                13:"nitrate_min", 14:"nitrate_max",
                15:"fecal_min", 16:"fecal_max",
                17:"total_coli_min", 18:"total_coli_max",
                19:"fecal_strep_min", 20:"fecal_strep_max"
            })
            for col in ["station","state"]:
                df[col] = df[col].astype(str).str.replace(r"\s+"," ", regex=True).str.strip()
            df["year"] = year
            df["section_title"] = section_title.strip()
            frames.append(df)
        if not frames:
            print(f"[WARN] no tables for {pdf.name}")
            continue
        out = pd.concat(frames, ignore_index=True)
        out_path = OUT_DIR / f"water_quality_by_section_{year}.csv"
        out.to_csv(out_path, index=False, encoding="utf-8")
        print(f"[OK] {year}: {len(out)} rows -> {out_path}")

if __name__ == "__main__":
    main()

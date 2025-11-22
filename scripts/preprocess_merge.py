# scripts/preprocess_merge.py
import re
from pathlib import Path
import numpy as np
import pandas as pd

IN_DIR = Path("../data/extracted_csv_by_section")
OUT_DIR = Path("../data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def fnum(x):
    s = str(x).strip().replace(",", "")
    if s.lower() in ("", "na", "nan", "nil", "-"):
        return np.nan
    try:
        return float(s)
    except:
        return np.nan

def waterbody_from_station(station: str):
    if not isinstance(station, str):
        return ""
    s = station.upper()
    m = re.search(r"\bRIVER\s+([A-Z/ \-]+?)\s+(AT|U/S|D/S|NEAR|NR)\b", s)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"\b([A-Z]{3,})\s+(AT|U/S|D/S|NEAR|NR)\b", s)
    return m2.group(1).strip() if m2 else ""

def process_year(path: Path) -> pd.DataFrame:
    m = re.search(r"(\d{4})", path.name)
    if not m:
        raise ValueError(f"Could not infer year from filename: {path.name}")
    year = int(m.group(1))
    print(f"[INFO] processing {path.name} (year={year})")

    df = pd.read_csv(path, dtype=str, encoding="utf-8")

    # Normalize whitespace
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(r"\s+"," ", regex=True).str.strip()

    # Convert numeric min/max columns
    num_cols = [
        "ph_min","ph_max",
        "cond_min","cond_max",
        "bod_min","bod_max",
        "do_min","do_max",
        "nitrate_min","nitrate_max"
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = df[c].map(fnum)

    # ---- Drop rows where all numeric fields are missing ----
    existing_num = [c for c in num_cols if c in df.columns]
    if existing_num:
        mask_all_nan = df[existing_num].isna().all(axis=1)
        before = len(df)
        df = df[~mask_all_nan].copy()
        dropped = before - len(df)
        if dropped:
            print(f"[INFO] dropped {dropped} rows with no numeric data for {year}")
    # -------------------------------------------------------

    out = pd.DataFrame()
    out["year"] = year
    out["code"] = df.get("code")
    out["station"] = df.get("station")
    out["state"] = df.get("state")
    out["section_title"] = df.get("section_title")

    # Representative means
    out["pH"] = (df.get("ph_min") + df.get("ph_max")) / 2.0 if "ph_min" in df and "ph_max" in df else np.nan
    out["conductivity_uScm"] = (df.get("cond_min") + df.get("cond_max")) / 2.0 if "cond_min" in df and "cond_max" in df else np.nan
    out["BOD_mg_L"] = (df.get("bod_min") + df.get("bod_max")) / 2.0 if "bod_min" in df and "bod_max" in df else np.nan
    out["DO_mg_L"] = (df.get("do_min") + df.get("do_max")) / 2.0 if "do_min" in df and "do_max" in df else np.nan
    out["nitrate_mg_L"] = (df.get("nitrate_min") + df.get("nitrate_max")) / 2.0 if "nitrate_min" in df and "nitrate_max" in df else np.nan

    # Waterbody + section cleanup
    out["waterbody"] = out["station"].apply(waterbody_from_station)
    out["section_title"] = out["section_title"].str.replace(r"\s*[-–]\s*$","", regex=True)
    out.loc[out["waterbody"].eq(""), "waterbody"] = out["section_title"].str.replace(r"^Tributary Streams -\s*","", regex=True)

    # Sanity and date
    out.loc[(out["pH"] < 0) | (out["pH"] > 14), "pH"] = np.nan
    out["date"] = pd.Timestamp(year=year, month=6, day=30)

    # Coerce and reorder
    out["year"] = int(year)
    cols = ["year","code","station","state","section_title","pH","conductivity_uScm","BOD_mg_L","DO_mg_L","nitrate_mg_L","waterbody","date"]
    out = out[cols]

    ypath = OUT_DIR / f"water_quality_standardized_{year}.csv"
    out.to_csv(ypath, index=False, encoding="utf-8")
    print(f"[OK] standardized {year}: {len(out)} rows -> {ypath}")
    return out

def main():
    files = sorted(IN_DIR.glob("water_quality_by_section_*.csv"))
    if not files:
        print("[ERR] no files found in data/extracted_csv_by_section")
        return
    parts = []
    for f in files:
        try:
            parts.append(process_year(f))
        except Exception as e:
            print(f"[ERR] {f.name}: {e}")

    if parts:
        all_df = pd.concat(parts, ignore_index=True)
        all_df["year"] = all_df["year"].fillna(method="ffill").fillna(method="bfill").astype(int)
        cols = ["year","code","station","state","section_title","pH","conductivity_uScm","BOD_mg_L","DO_mg_L","nitrate_mg_L","waterbody","date"]
        all_df = all_df[cols]
        master = OUT_DIR / "water_quality_2016_2023.csv"
        all_df.to_csv(master, index=False, encoding="utf-8")
        print(f"[DONE] Master -> {master} ({len(all_df)} rows)")

if __name__ == "__main__":
    main()

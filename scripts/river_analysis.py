# analysis/river_analysis.py
import argparse
import glob
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# ---------- Standards (BIS for gating, WHO for reference) ----------
BIS = {
    "pH": {"acceptable_min": 6.5, "acceptable_max": 8.5},  # no relaxation
    "TDS_mg_L": {"acceptable_max": 500.0, "permissible_max": 2000.0},
    "turbidity_NTU": {"acceptable_max": 1.0, "permissible_max": 5.0},
}

WHO_REF = {
    # WHO uses narrative guidance; these reflect common practice for dashboard messaging
    "pH": {"guideline_min": 6.5, "guideline_max": 8.5},
    # TDS is acceptability-based; many references cite ~600 mg/L as a taste guideline
    "TDS_mg_L": {"guideline_max": 600.0},
    # Turbidity targets ≤1 NTU; 5 NTU is often treated as an upper bound in operations
    "turbidity_NTU": {"guideline_max": 1.0, "upper_bound": 5.0},
}

# ---------- Helpers ----------
def _norm(s: str) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())

def parse_numeric(x):
    if x is None:
        return np.nan
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if s in ("", "-", "na", "nan", "nil"):
        return np.nan
    # remove commas and stray symbols
    s = s.replace(",", "")
    # ranges like "7.1\n8.5" or "7.1-8.5": take mean
    if "-" in s:
        parts = [p for p in re.split(r"[-–]", s) if p.strip() != ""]
        try:
            nums = [float(p) for p in parts]
            return float(np.mean(nums))
        except:
            pass
    try:
        return float(s)
    except:
        return np.nan

def parse_date_any(x):
    # PDFs often lack date; if YEAR is embedded via filename, we’ll add later
    try:
        return pd.to_datetime(x, errors="coerce")
    except:
        return pd.NaT

def guess_river_from_station(station_name: str) -> str:
    s = _norm(station_name)
    # Heuristics to pull first token that looks like a river name preceding 'at', 'u/s', etc.
    # Example: "BEAS D/S MANDI" -> "beas"
    m = re.match(r"([a-z]+)", s)
    if m:
        return m.group(1).upper()
    return np.nan

# Map many header variants to canonical schema
HEADER_ALIASES = {
    "station": ["station", "station_name", "station name", "site", "location"],
    "state": ["state", "state name", "state/ut"],
    "river": ["river", "river name", "water body", "waterbody", "source name"],
    "ph": ["ph", "pH", "p h", "p_h"],
    "tds": ["tds", "total dissolved solids", "t.d.s.", "(mg/l) for tds", "tds (mg/l)"],
    "turbidity": ["turbidity", "ntu", "turbidity (ntu)"],
    "date": ["date", "sampling date", "sample date", "month", "year"],
    "district": ["district", "city", "town"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng"],
    "code": ["code", "station code"],
    "do": ["dissolved oxygen", "do", "d.o.", "d.o"],
    "bod": ["b.o.d.", "bod", "b o d", "biochemical oxygen demand"],
    "conductivity": ["conductivity", "µmhos/cm", "umhos/cm", "ec", "electrical conductivity"],
    "nitrate": ["nitrate-n + nitrite-n", "nitrate", "nitrite", "nitrate (mg/l)", "nitrate-n"],
    "fecal_coliform": ["faecal coli form", "faecal coliform", "fecal coliform", "fecal coli form", "fecal colifrom"],
    "total_coliform": ["total coli form", "total coliform", "total coli-form"],
    "temp": ["temperature", "temperature ⁰c", "temperature (c)", "temperature °c"],
}

def find_col(cols: List[str], candidates: List[str]):
    low = {c.lower().strip(): c for c in cols}
    for c in candidates:
        if c in low:
            return low[c]
    # search contains
    for c in cols:
        cn = c.lower().strip()
        if any(cand in cn for cand in candidates):
            return c
    return None

def standardize_df(df: pd.DataFrame, year_hint: int = None) -> pd.DataFrame:
    cols = list(df.columns)
    # pick columns
    station_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["station"]]) or "station"
    state_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["state"]])
    river_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["river"]])
    ph_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["ph"]])
    tds_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["tds"]])
    turb_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["turbidity"]])
    date_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["date"]])
    district_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["district"]])
    lat_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["latitude"]])
    lon_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["longitude"]])
    code_col = find_col(cols, [x.lower() for x in HEADER_ALIASES["code"]])

    out = pd.DataFrame()
    out["station"] = df[station_col] if station_col in df else np.nan
    out["state"] = df[state_col] if state_col in df else np.nan
    # river may be missing; derive heuristic from station if needed
    if river_col and river_col in df:
        out["river"] = df[river_col]
    else:
        out["river"] = out["station"].astype(str).apply(guess_river_from_station)

    # parse numerics (note some tables have min/max columns per parameter; take row means if so)
    def pick_param(prefixes):
        # look for 'min'/'max' siblings e.g., 'ph_min', 'ph_max'
        cands = [c for c in df.columns if any(pref in c.lower() for pref in prefixes)]
        if any("min" in c.lower() for c in cands) and any("max" in c.lower() for c in cands):
            mn = [c for c in cands if "min" in c.lower()]
            mx = [c for c in cands if "max" in c.lower()]
            mn = mn[0] if mn else None
            mx = mx[0] if mx else None
            if mn and mx:
                vals = (df[mn].apply(parse_numeric) + df[mx].apply(parse_numeric)) / 2.0
                return vals
        # fallback single column
        col = find_col(df.columns, prefixes)
        if col and col in df:
            return df[col].apply(parse_numeric)
        return pd.Series(np.nan, index=df.index)

    out["pH"] = pick_param(["ph", "p h"])
    out["TDS_mg_L"] = pick_param(["tds", "total dissolved"])
    out["turbidity_NTU"] = pick_param(["turbidity", "ntu"])

    # date
    if date_col and date_col in df:
        out["date"] = df[date_col].apply(parse_date_any)
    else:
        # synthesize mid-year date from hint
        out["date"] = pd.to_datetime(f"{year_hint}-06-30") if year_hint else pd.NaT

    out["district"] = df[district_col] if district_col in df else np.nan
    out["latitude"] = df[lat_col].apply(parse_numeric) if lat_col in df else np.nan
    out["longitude"] = df[lon_col].apply(parse_numeric) if lon_col in df else np.nan
    out["code"] = df[code_col] if code_col in df else np.nan

    # Clean impossible values
    out.loc[(out["pH"] < 0) | (out["pH"] > 14), "pH"] = np.nan
    out.loc[(out["TDS_mg_L"] < 0) | (out["TDS_mg_L"] > 100000), "TDS_mg_L"] = np.nan
    out.loc[(out["turbidity_NTU"] < 0) | (out["turbidity_NTU"] > 10000), "turbidity_NTU"] = np.nan

    # Drop rows with no key measures
    out = out.dropna(subset=["pH", "TDS_mg_L", "turbidity_NTU"], how="all")
    return out

def bis_flag_row(row, use_permissible=True) -> Tuple[str, List[str]]:
    status = "SAFE"
    reasons = []
    # pH
    if not pd.isna(row["pH"]):
        if row["pH"] < BIS["pH"]["acceptable_min"] or row["pH"] > BIS["pH"]["acceptable_max"]:
            status = "UNSAFE"
            reasons.append("pH outside 6.5–8.5")
    # TDS
    if not pd.isna(row["TDS_mg_L"]):
        if row["TDS_mg_L"] > BIS["TDS_mg_L"]["acceptable_max"]:
            if use_permissible and row["TDS_mg_L"] <= BIS["TDS_mg_L"]["permissible_max"] and status != "UNSAFE":
                status = "MARGINAL"
                reasons.append("TDS above 500, within 2000")
            else:
                status = "UNSAFE"
                reasons.append("TDS above 500")
    # Turbidity
    if not pd.isna(row["turbidity_NTU"]):
        if row["turbidity_NTU"] > BIS["turbidity_NTU"]["acceptable_max"]:
            if use_permissible and row["turbidity_NTU"] <= BIS["turbidity_NTU"]["permissible_max"] and status != "UNSAFE":
                status = "MARGINAL"
                reasons.append("Turbidity above 1, within 5")
            else:
                status = "UNSAFE"
                reasons.append("Turbidity above 1")
    return status, reasons

def who_compare_row(row) -> List[str]:
    notes = []
    if not pd.isna(row["pH"]):
        if row["pH"] < WHO_REF["pH"]["guideline_min"] or row["pH"] > WHO_REF["pH"]["guideline_max"]:
            notes.append("WHO: pH outside 6.5–8.5")
    if not pd.isna(row["TDS_mg_L"]):
        if row["TDS_mg_L"] > WHO_REF["TDS_mg_L"]["guideline_max"]:
            notes.append("WHO: TDS above ~600 (taste guideline)")
    if not pd.isna(row["turbidity_NTU"]):
        if row["turbidity_NTU"] > WHO_REF["turbidity_NTU"]["guideline_max"]:
            if row["turbidity_NTU"] <= WHO_REF["turbidity_NTU"]["upper_bound"]:
                notes.append("WHO: Turbidity >1 (target), ≤5 (upper bound)")
            else:
                notes.append("WHO: Turbidity >5")
    return notes

def load_all_years(data_dir: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(data_dir, "water_quality_*.csv")))
    frames = []
    for f in files:
        # infer year
        m = re.search(r"(\d{4})", os.path.basename(f))
        year_hint = int(m.group(1)) if m else None
        df = pd.read_csv(f, dtype=str, encoding="utf-8")
        frames.append(standardize_df(df, year_hint=year_hint))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def describe_series(s: pd.Series) -> Dict[str, float]:
    s = s.dropna()
    if s.empty:
        return {"count": 0}
    return {
        "count": int(s.count()),
        "mean": float(np.round(s.mean(), 3)),
        "median": float(np.round(s.median(), 3)),
        "min": float(np.round(s.min(), 3)),
        "max": float(np.round(s.max(), 3)),
        "std": float(np.round(s.std(ddof=1), 3)) if s.count() > 1 else 0.0,
    }

def river_report(df: pd.DataFrame, river_name: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    # match river name in either river or station text
    rnorm = _norm(river_name)
    mask = df["river"].astype(str).str.lower().str.contains(rnorm, na=False) | df["station"].astype(str).str.lower().str.contains(rnorm, na=False)
    sub = df[mask].copy()
    if sub.empty:
        result = {"river": river_name, "found": False, "message": "No records found"}
        with open(os.path.join(out_dir, f"{river_name}_report.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(json.dumps(result, indent=2))
        return

    # BIS flags
    statuses = []
    reasons_list = []
    who_notes = []
    for _, row in sub.iterrows():
        st, rs = bis_flag_row(row, use_permissible=True)
        statuses.append(st)
        reasons_list.append("; ".join(rs) if rs else "Within acceptable limits")
        who_notes.append("; ".join(who_compare_row(row)) or "Within WHO guidance")

    sub["bis_status"] = statuses
    sub["bis_reasons"] = reasons_list
    sub["who_notes"] = who_notes
    sub["unsafe_bool"] = (sub["bis_status"] == "UNSAFE").astype(int)
    sub["marginal_bool"] = (sub["bis_status"] == "MARGINAL").astype(int)

    # Descriptive stats
    stats = {
        "pH": describe_series(sub["pH"]),
        "TDS_mg_L": describe_series(sub["TDS_mg_L"]),
        "turbidity_NTU": describe_series(sub["turbidity_NTU"]),
    }

    # Latest snapshot per station
    sub["date"] = pd.to_datetime(sub["date"], errors="coerce")
    latest_idx = sub.groupby("station")["date"].idxmax().dropna().astype(int)
    latest = sub.loc[latest_idx, ["station","state","river","date","pH","TDS_mg_L","turbidity_NTU","bis_status","bis_reasons","who_notes","latitude","longitude"]].sort_values(["state","station"])

    # River-level verdict using latest observations
    latest_overall = latest.copy()
    verdict_counts = latest_overall["bis_status"].value_counts().to_dict()
    if "UNSAFE" in verdict_counts and verdict_counts["UNSAFE"] > 0:
        verdict = "UNSAFE"
    elif "MARGINAL" in verdict_counts and verdict_counts["MARGINAL"] > 0:
        verdict = "MARGINAL"
    else:
        verdict = "SAFE"

    output = {
        "river": river_name,
        "records": int(len(sub)),
        "stations": int(sub["station"].nunique()),
        "states": sorted([s for s in sub["state"].dropna().unique()]),
        "bis_verdict": verdict,
        "bis_summary_counts": verdict_counts,
        "descriptive_stats": stats,
        "notes": "BIS IS 10500:2012 used for pass/fail; WHO guidelines reported for context",
    }

    # Write outputs
    base = re.sub(r"[^A-Za-z0-9_]+", "_", river_name.strip())
    sub.to_csv(os.path.join(out_dir, f"{base}_records.csv"), index=False, encoding="utf-8")
    latest.to_csv(os.path.join(out_dir, f"{base}_latest.csv"), index=False, encoding="utf-8")
    with open(os.path.join(out_dir, f"{base}_report.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(json.dumps(output, indent=2))

def main():
    parser = argparse.ArgumentParser(description="River-wise water quality analysis and WHO/BIS comparison")
    parser.add_argument("--river", required=True, help="River name to filter, e.g., 'Beas', 'Satluj'")
    parser.add_argument("--data-dir", default="../data/processed", help="Directory with water_quality_YYYY.csv files")
    parser.add_argument("--out-dir", default="../outputs/river_reports", help="Directory to write outputs")
    args = parser.parse_args()

    df = load_all_years(args.data_dir)
    if df.empty:
        print(json.dumps({"error": "No data found in data-dir"}, indent=2))
        return
    river_report(df, args.river, args.out_dir)

if __name__ == "__main__":
    main()

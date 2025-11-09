# scripts/standardize_extracted_nwmp.py
import os, re, glob, json
import numpy as np
import pandas as pd

# Canonical parameter names aligned to BIS/WHO checks
CANON = {
    "pH": "pH",
    "TDS_mg_L": "TDS_mg_L",
    "turbidity_NTU": "turbidity_NTU",
}

# Header alias dictionary (lowercased matching)
ALIASES = {
    "station": ["station", "station name", "station_name", "location", "site"],
    "state": ["state", "state name", "state/ut"],
    "river": ["river", "river name", "water body", "waterbody", "source name"],
    "code": ["code", "station code"],
    "district": ["district", "city", "town"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng"],
    # parameters and their min/max patterns
    "ph": ["ph", "p h"],
    "tds": ["tds", "total dissolved solids", "t.d.s."],
    "turbidity": ["turbidity", "ntu"],
    "conductivity": ["conductivity", "µmhos/cm", "umhos/cm", "ec", "electrical conductivity"],
    "do": ["dissolved oxygen", "do", "d.o."],
    "bod": ["b.o.d.", "bod", "biochemical oxygen demand"],
    "nitrate": ["nitrate-n + nitrite-n", "nitrate", "nitrite"],
    "fecal_coliform": ["faecal coli form", "faecal coliform", "fecal coliform", "fecal coli form"],
    "total_coliform": ["total coli form", "total coliform", "total coli-form"],
    "temp": ["temperature ⁰c", "temperature °c", "temperature (c)", "temperature"],
}

def norm(s):
    return re.sub(r"\s+", " ", str(s).strip().lower()) if s is not None else ""

def find_col(cols, names):
    low = {c.lower().strip(): c for c in cols}
    for n in names:
        if n in low:
            return low[n]
    # fuzzy contains
    for c in cols:
        lc = c.lower().strip()
        if any(n in lc for n in names):
            return c
    return None

def parse_num(x):
    if x is None: return np.nan
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip().replace(",", "")
    if s in ("", "-", "na", "nan", "nil"): return np.nan
    # ranges like "7.3-8.1"
    if re.search(r"\d\s*[-–]\s*\d", s):
        parts = [p for p in re.split(r"[-–]", s) if p.strip() != ""]
        try:
            vals = [float(p) for p in parts]
            return float(np.mean(vals))
        except: pass
    try:
        return float(s)
    except:
        return np.nan

def representative_from_minmax(df, key_words):
    # Look for columns with 'min'/'max' for a parameter
    candidates = [c for c in df.columns if any(k in c.lower() for k in key_words)]
    min_col = next((c for c in candidates if "min" in c.lower()), None)
    max_col = next((c for c in candidates if "max" in c.lower()), None)
    if min_col and max_col:
        vals = (df[min_col].map(parse_num) + df[max_col].map(parse_num)) / 2.0
        return vals
    # else, single column fallback
    col = find_col(df.columns, key_words)
    return df[col].map(parse_num) if col else pd.Series(np.nan, index=df.index)

def guess_river_from_station(station):
    s = norm(station)
    m = re.match(r"([a-z]+)", s)
    return m.group(1).upper() if m else np.nan

def standardize_one(df, year_hint=None):
    out = pd.DataFrame()
    # identities
    st_col = find_col(df.columns, [n for n in ALIASES["station"]])
    state_col = find_col(df.columns, [n for n in ALIASES["state"]])
    river_col = find_col(df.columns, [n for n in ALIASES["river"]])

    out["station"] = df[st_col] if st_col else np.nan
    out["state"] = df[state_col] if state_col else np.nan
    if river_col:
        out["river"] = df[river_col]
    else:
        out["river"] = out["station"].apply(guess_river_from_station)

    # representative values
    out["pH"] = representative_from_minmax(df, ["ph", "p h"])
    out["TDS_mg_L"] = representative_from_minmax(df, ["tds", "total dissolved solids"])
    out["turbidity_NTU"] = representative_from_minmax(df, ["turbidity", "ntu"])

    # optional fields
    out["district"] = df[find_col(df.columns, ALIASES["district"])] if find_col(df.columns, ALIASES["district"]) else np.nan
    out["latitude"] = df[find_col(df.columns, ALIASES["latitude"])].map(parse_num) if find_col(df.columns, ALIASES["latitude"]) else np.nan
    out["longitude"] = df[find_col(df.columns, ALIASES["longitude"])].map(parse_num) if find_col(df.columns, ALIASES["longitude"]) else np.nan
    out["code"] = df[find_col(df.columns, ALIASES["code"])] if find_col(df.columns, ALIASES["code"]) else np.nan

    # synthesize date from year
    if year_hint:
        out["date"] = pd.to_datetime(f"{year_hint}-06-30")
    else:
        out["date"] = pd.NaT

    # sanity limits
    out.loc[(out["pH"] < 0) | (out["pH"] > 14), "pH"] = np.nan
    out.loc[(out["TDS_mg_L"] < 0) | (out["TDS_mg_L"] > 100000), "TDS_mg_L"] = np.nan
    out.loc[(out["turbidity_NTU"] < 0) | (out["turbidity_NTU"] > 10000), "turbidity_NTU"] = np.nan

    # drop empty rows
    out = out.dropna(subset=["pH", "TDS_mg_L", "turbidity_NTU"], how="all")
    return out

def run(data_dir="../data/extracted_csv", out_dir="../data/processed"):
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(data_dir, "water_quality_*.csv")))
    frames = []
    for f in files:
        year = None
        m = re.search(r"(\d{4})", os.path.basename(f))
        if m: year = int(m.group(1))
        df_raw = pd.read_csv(f, dtype=str, encoding="utf-8")
        df_std = standardize_one(df_raw, year_hint=year)
        df_std.to_csv(os.path.join(out_dir, f"water_quality_standardized_{year}.csv"), index=False, encoding="utf-8")
        frames.append(df_std)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        all_df.to_csv(os.path.join(out_dir, "water_quality_standardized_all.csv"), index=False, encoding="utf-8")
        with open(os.path.join(out_dir, "schema.json"), "w", encoding="utf-8") as f:
            json.dump({"columns": list(all_df.columns)}, f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(all_df)} rows across {len(frames)} years to {out_dir}")

if __name__ == "__main__":
    run()

# analysis/river_analysis_and_plots.py
import argparse
import json
import os
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# BIS IS 10500:2012 acceptable pH range for drinking water
BIS = {"pH_min": 6.5, "pH_max": 8.5}

def normalize_text(s):
    return re.sub(r"\s+"," ", str(s)).strip()

def load_master(path):
    df = pd.read_csv(path, parse_dates=["date"])
    # Ensure expected columns exist
    required = ["year","code","station","state","section_title","pH","waterbody","date"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")
    # Normalize text columns
    for col in ["station","state","section_title","waterbody"]:
        df[col] = df[col].astype(str).map(normalize_text)
    # Enforce types
    df["year"] = df["year"].astype(int)
    return df

def match_waterbody(df, river_name):
    rn = river_name.strip().upper()
    # Prefer exact match on parsed waterbody
    m1 = df["waterbody"].str.upper().str.fullmatch(rn, na=False)
    if m1.any():
        return df[m1].copy()
    # Fallback: station contains river name
    m2 = df["station"].str.upper().str.contains(rf"\b{re.escape(rn)}\b", na=False)
    return df[m2].copy()

def bis_status_row(pH):
    if pd.isna(pH):
        return "UNKNOWN", "pH missing"
    if pH < BIS["pH_min"] or pH > BIS["pH_max"]:
        return "UNSAFE", "pH outside 6.5–8.5 (BIS IS 10500)"
    return "SAFE", "Within acceptable limits"

def pH_deviation(pH):
    if pd.isna(pH):
        return np.nan
    if pH < BIS["pH_min"]:
        return BIS["pH_min"] - pH
    if pH > BIS["pH_max"]:
        return pH - BIS["pH_max"]
    return 0.0

def descriptive_stats(series):
    s = series.dropna()
    return {
        "count": int(s.count()),
        "mean": round(float(s.mean()), 3) if not s.empty else None,
        "median": round(float(s.median()), 3) if not s.empty else None,
        "min": round(float(s.min()), 3) if not s.empty else None,
        "max": round(float(s.max()), 3) if not s.empty else None,
        "std": round(float(s.std(ddof=1)), 3) if s.count() > 1 else 0.0
    }

def analyze_river(df, river_name, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    sub = match_waterbody(df, river_name)
    if sub.empty:
        result = {"river": river_name, "found": False, "message": "No rows matched"}
        with open(os.path.join(out_dir, f"{river_name}_report.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Compute BIS status and pH deviation
    sub["bis_status"], sub["bis_reasons"] = zip(*sub["pH"].map(bis_status_row))
    sub["pH_dev"] = sub["pH"].map(pH_deviation)

    # Latest per station (annual data -> latest year)
    latest_idx = sub.sort_values(["date"]).groupby("station").tail(1).index
    latest = sub.loc[latest_idx].sort_values(["state","station"])

    verdict_counts = latest["bis_status"].value_counts().to_dict()
    if verdict_counts.get("UNSAFE", 0) > 0:
        verdict = "UNSAFE"
    elif verdict_counts.get("SAFE", 0) > 0:
        verdict = "SAFE"
    else:
        verdict = "UNKNOWN"

    # Descriptive stats
    summary = {
        "pH": descriptive_stats(sub["pH"]),
        "conductivity_uScm": descriptive_stats(sub["conductivity_uScm"]) if "conductivity_uScm" in sub.columns else {"count": 0},
        "BOD_mg_L": descriptive_stats(sub["BOD_mg_L"]) if "BOD_mg_L" in sub.columns else {"count": 0},
        "DO_mg_L": descriptive_stats(sub["DO_mg_L"]) if "DO_mg_L" in sub.columns else {"count": 0},
        "nitrate_mg_L": descriptive_stats(sub["nitrate_mg_L"]) if "nitrate_mg_L" in sub.columns else {"count": 0},
    }

    # Write outputs
    base = re.sub(r"[^A-Za-z0-9_]+", "_", river_name.strip())
    sub.to_csv(os.path.join(out_dir, f"{base}_records.csv"), index=False, encoding="utf-8")
    latest.to_csv(os.path.join(out_dir, f"{base}_latest.csv"), index=False, encoding="utf-8")

    report = {
        "river": river_name,
        "records": int(len(sub)),
        "stations": int(sub["station"].nunique()),
        "states": sorted([s for s in sub["state"].dropna().unique()]),
        "bis_verdict": verdict,
        "bis_summary_counts": verdict_counts,
        "descriptive_stats": summary,
        "notes": "Safe/Unsafe uses BIS IS 10500 pH 6.5–8.5; include turbidity/TDS if available in future datasets."
    }
    with open(os.path.join(out_dir, f"{base}_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    # Plots
    plt.style.use("seaborn-v0_8-darkgrid")

    # 1) Yearly trend of pH by state
    gp = sub.groupby(["year","state"])["pH"].mean().reset_index()
    if not gp.empty:
        plt.figure(figsize=(9,4))
        for st in gp["state"].dropna().unique():
            s = gp[gp["state"]==st]
            plt.plot(s["year"], s["pH"], marker="o", label=st)
        plt.axhspan(BIS["pH_min"], BIS["pH_max"], color="green", alpha=0.12, label="BIS acceptable")
        plt.title(f"{river_name}: yearly mean pH by state")
        plt.xlabel("Year"); plt.ylabel("pH"); plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"{base}_pH_trend.png"), dpi=150)
        plt.close()

    # 2) Station x Year heatmap of pH
    piv = sub.pivot_table(index="station", columns="year", values="pH", aggfunc="mean")
    if piv.shape[0] > 0:
        plt.figure(figsize=(10, max(4, piv.shape[0]*0.25)))
        sns.heatmap(piv, cmap="RdYlGn", vmin=6.0, vmax=9.0, cbar_kws={"label":"pH"})
        plt.title(f"{river_name}: station-year pH heatmap")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"{base}_pH_heatmap.png"), dpi=150)
        plt.close()
        piv.to_csv(os.path.join(out_dir, f"{base}_pH_pivot.csv"))

    # 3) Top 5 stations by pH deviation in latest year
    worst = latest.sort_values("pH_dev", ascending=False).dropna(subset=["pH_dev"]).head(5)
    if not worst.empty:
        plt.figure(figsize=(9,4))
        plt.barh(worst["station"], worst["pH_dev"])
        plt.gca().invert_yaxis()
        plt.xlabel("pH deviation from 6.5–8.5")
        plt.title(f"{river_name}: top 5 stations by pH deviation (latest)")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"{base}_pH_top5.png"), dpi=150)
        plt.close()

def main():
    ap = argparse.ArgumentParser(description="River-wise analysis and plots (BIS pH gating)")
    ap.add_argument("--data", required=True, help="../data/processed/water_quality_2016_2023.csv")
    ap.add_argument("--river", required=True, help='River/waterbody name, e.g., "Beas", "Sutlej"')
    ap.add_argument("--out-dir", default="../outputs/river_reports")
    args = ap.parse_args()

    df = load_master(args.data)
    analyze_river(df, args.river, args.out_dir)

if __name__ == "__main__":
    main()

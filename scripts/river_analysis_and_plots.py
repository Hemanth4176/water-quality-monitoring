# analysis/river_analysis_and_plots.py
import argparse
import json
import os
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BIS = {"pH_min": 6.5, "pH_max": 8.5}

RAW = {
    "DO_min": 5.0,
    "BOD_max": 3.0,
    "fecal_coliform_max": 2500.0,
    "total_coliform_max": 500.0
}

def normalize_text(s):
    return re.sub(r"\s+"," ", str(s)).strip()

def load_master(path):
    df = pd.read_csv(path, parse_dates=["date"])
    required = ["year","code","station","state","section_title","pH","waterbody","date"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")
    for col in ["station","state","section_title","waterbody"]:
        df[col] = df[col].astype(str).map(normalize_text)
    df["year"] = df["year"].astype(int)
    opt_nums = ["DO_mg_L","BOD_mg_L","conductivity_uScm","nitrate_mg_L",
                "fecal_coliform_min","fecal_coliform_max","total_coliform_min","total_coliform_max"]
    for c in opt_nums:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def match_waterbody(df, river_name):
    rn = river_name.strip().upper()
    m1 = df["waterbody"].str.upper().str.fullmatch(rn, na=False)
    if m1.any():
        return df[m1].copy()
    m2 = df["station"].str.upper().str.contains(rf"\b{re.escape(rn)}\b", na=False)
    return df[m2].copy()

def bis_status_row(pH):
    if pd.isna(pH):
        return "UNKNOWN", "pH missing"
    if pH < BIS["pH_min"] or pH > BIS["pH_max"]:
        return "UNSAFE", "pH outside 6.5–8.5 (BIS IS 10500)"
    return "SAFE", "Within BIS acceptable pH"

def composite_status_row(row):
    reasons = []
    unknown = False

    pH = row.get("pH", np.nan)
    if pd.isna(pH):
        unknown = True
    else:
        if pH < BIS["pH_min"] or pH > BIS["pH_max"]:
            reasons.append("pH out of 6.5–8.5")

    DO = row.get("DO_mg_L", np.nan)
    if pd.isna(DO):
        unknown = True
    else:
        if DO < RAW["DO_min"]:
            reasons.append("DO < 5 mg/L")

    BOD = row.get("BOD_mg_L", np.nan)
    if pd.isna(BOD):
        unknown = True
    else:
        if BOD > RAW["BOD_max"]:
            reasons.append("BOD > 3 mg/L")

    fecal = None
    if "fecal_coliform_max" in row and not pd.isna(row["fecal_coliform_max"]):
        fecal = row["fecal_coliform_max"]
    elif "fecal_coliform_min" in row and not pd.isna(row["fecal_coliform_min"]):
        fecal = row["fecal_coliform_min"]
    if fecal is None:
        unknown = True
    else:
        if fecal > RAW["fecal_coliform_max"]:
            reasons.append("Fecal coliform > 2500 MPN/100ml")

    tcol = None
    if "total_coliform_max" in row and not pd.isna(row["total_coliform_max"]):
        tcol = row["total_coliform_max"]
    elif "total_coliform_min" in row and not pd.isna(row["total_coliform_min"]):
        tcol = row["total_coliform_min"]
    if tcol is None:
        unknown = True
    else:
        if tcol > RAW["total_coliform_max"]:
            reasons.append("Total coliform > 500 MPN/100ml")

    if unknown and not reasons:
        return "UNKNOWN", "Insufficient data for composite check"
    if reasons:
        return "UNSAFE", "; ".join(reasons)
    return "SAFE", "Within composite raw-water thresholds"

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

    sub["bis_status"], sub["bis_reasons"] = zip(*sub["pH"].map(bis_status_row))
    sub["pH_dev"] = sub["pH"].map(pH_deviation)

    comp_status = []
    comp_reasons = []
    for _, r in sub.iterrows():
        st, rs = composite_status_row(r)
        comp_status.append(st); comp_reasons.append(rs)
    sub["raw_status"] = comp_status
    sub["raw_reasons"] = comp_reasons

    latest_idx = sub.sort_values(["date"]).groupby("station").tail(1).index
    latest = sub.loc[latest_idx].sort_values(["state","station"])

    bis_counts = latest["bis_status"].value_counts().to_dict()
    bis_verdict = "UNSAFE" if bis_counts.get("UNSAFE", 0) > 0 else ("SAFE" if bis_counts.get("SAFE", 0) > 0 else "UNKNOWN")
    raw_counts = latest["raw_status"].value_counts().to_dict()
    raw_verdict = "UNSAFE" if raw_counts.get("UNSAFE", 0) > 0 else ("SAFE" if raw_counts.get("SAFE", 0) > 0 else "UNKNOWN")

    summary = {
        "pH": descriptive_stats(sub["pH"]),
        "conductivity_uScm": descriptive_stats(sub["conductivity_uScm"]) if "conductivity_uScm" in sub.columns else {"count": 0},
        "BOD_mg_L": descriptive_stats(sub["BOD_mg_L"]) if "BOD_mg_L" in sub.columns else {"count": 0},
        "DO_mg_L": descriptive_stats(sub["DO_mg_L"]) if "DO_mg_L" in sub.columns else {"count": 0},
        "nitrate_mg_L": descriptive_stats(sub["nitrate_mg_L"]) if "nitrate_mg_L" in sub.columns else {"count": 0},
    }

    base = re.sub(r"[^A-Za-z0-9_]+", "_", river_name.strip())
    sub.to_csv(os.path.join(out_dir, f"{base}_records.csv"), index=False, encoding="utf-8")
    latest.to_csv(os.path.join(out_dir, f"{base}_latest.csv"), index=False, encoding="utf-8")

    report = {
        "river": river_name,
        "records": int(len(sub)),
        "stations": int(sub["station"].nunique()),
        "states": sorted([s for s in sub["state"].dropna().unique()]),
        "bis_verdict": bis_verdict,
        "bis_summary_counts": bis_counts,
        "raw_verdict": raw_verdict,
        "raw_summary_counts": raw_counts,
        "descriptive_stats": summary,
        "notes": "BIS pH 6.5–8.5 used for drinking pH gate; composite raw-water gate applies DO>5 mg/L, BOD<3 mg/L, fecal<2500, total<500, and pH in-band; treated water must meet BIS IS 10500 at tap."
    }
    with open(os.path.join(out_dir, f"{base}_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    plt.style.use("seaborn-v0_8-darkgrid")

    # 1) pH trend by state
    gp = sub.groupby(["year","state"])["pH"].mean().reset_index()
    if not gp.empty:
        plt.figure(figsize=(10,4))
        for st in gp["state"].dropna().unique():
            s = gp[gp["state"] == st]
            plt.plot(s["year"], s["pH"], marker="o", label=st)
        plt.axhspan(BIS["pH_min"], BIS["pH_max"],
                    color="green", alpha=0.12, label="BIS acceptable")
        plt.title(f"{river_name}: yearly mean pH by state")
        plt.xlabel("Year")
        plt.ylabel("pH")
        plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15),
                   ncol=3, fontsize=8)
        plt.subplots_adjust(bottom=0.25)
        plt.savefig(os.path.join(out_dir, f"{base}_pH_trend.png"), dpi=150,
                    bbox_inches="tight")
        plt.close()

    # 2) Station x Year pH heatmap
    piv = sub.pivot_table(index="station", columns="year", values="pH", aggfunc="mean")
    if piv.shape[0] > 0:
        plt.figure(figsize=(12, max(4, piv.shape[0]*0.25)))
        sns.heatmap(piv, cmap="RdYlGn", vmin=6.0, vmax=9.0, cbar_kws={"label":"pH"})
        plt.title(f"{river_name}: station-year pH heatmap")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"{base}_pH_heatmap.png"), dpi=150)
        plt.close()
        piv.to_csv(os.path.join(out_dir, f"{base}_pH_pivot.csv"))

    # 3) Top 5 worst pH deviation (latest)
    worst = latest.sort_values("pH_dev", ascending=False).dropna(subset=["pH_dev"]).head(5)
    if not worst.empty:
        plt.figure(figsize=(10,4))
        plt.barh(worst["station"], worst["pH_dev"])
        plt.gca().invert_yaxis()
        plt.xlabel("pH deviation from 6.5–8.5")
        plt.title(f"{river_name}: top 5 stations by pH deviation (latest)")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"{base}_pH_top5.png"), dpi=150)
        plt.close()

    # 4) BIS pH compliance over time (SAFE/UNSAFE/UNKNOWN)
    yearly_bis = (
        sub.assign(year=sub["year"].astype(int))
           .groupby(["year","bis_status"])["station"].nunique()
           .unstack(fill_value=0)
           .reset_index()
    )
    for k in ["SAFE","UNSAFE","UNKNOWN"]:
        if k not in yearly_bis.columns:
            yearly_bis[k] = 0
    yearly_bis["TOTAL"]     = yearly_bis["SAFE"] + yearly_bis["UNSAFE"] + yearly_bis["UNKNOWN"]
    yearly_bis["SAFE_%"]    = 100.0 * yearly_bis["SAFE"]    / yearly_bis["TOTAL"].replace(0, np.nan)
    yearly_bis["UNSAFE_%"]  = 100.0 * yearly_bis["UNSAFE"]  / yearly_bis["TOTAL"].replace(0, np.nan)
    yearly_bis["UNKNOWN_%"] = 100.0 * yearly_bis["UNKNOWN"] / yearly_bis["TOTAL"].replace(0, np.nan)

    plt.figure(figsize=(10,4))
    plt.plot(yearly_bis["year"], yearly_bis["SAFE_%"],   marker="o", label="Safe % (pH)")
    plt.plot(yearly_bis["year"], yearly_bis["UNSAFE_%"], marker="o", label="Unsafe % (pH)")
    plt.plot(yearly_bis["year"], yearly_bis["UNKNOWN_%"],marker="o", label="Unknown % (pH)")
    plt.ylim(0, 100)
    plt.ylabel("Percent of stations"); plt.xlabel("Year")
    plt.title(f"{river_name}: BIS pH compliance over time")
    plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{base}_bis_compliance_over_time.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
    yearly_bis.to_csv(os.path.join(out_dir, f"{base}_bis_compliance_over_time.csv"),
                      index=False)

    # 5) Composite raw-water compliance over time (SAFE/UNSAFE/UNKNOWN)
    yearly_raw = (
        sub.assign(year=sub["year"].astype(int))
           .groupby(["year","raw_status"])["station"].nunique()
           .unstack(fill_value=0)
           .reset_index()
    )
    for k in ["SAFE","UNSAFE","UNKNOWN"]:
        if k not in yearly_raw.columns:
            yearly_raw[k] = 0
    yearly_raw["TOTAL"]     = yearly_raw["SAFE"] + yearly_raw["UNSAFE"] + yearly_raw["UNKNOWN"]
    yearly_raw["SAFE_%"]    = 100.0 * yearly_raw["SAFE"]    / yearly_raw["TOTAL"].replace(0, np.nan)
    yearly_raw["UNSAFE_%"]  = 100.0 * yearly_raw["UNSAFE"]  / yearly_raw["TOTAL"].replace(0, np.nan)
    yearly_raw["UNKNOWN_%"] = 100.0 * yearly_raw["UNKNOWN"] / yearly_raw["TOTAL"].replace(0, np.nan)

    plt.figure(figsize=(10,4))
    plt.plot(yearly_raw["year"], yearly_raw["SAFE_%"],   marker="o", label="Safe % (composite)")
    plt.plot(yearly_raw["year"], yearly_raw["UNSAFE_%"], marker="o", label="Unsafe % (composite)")
    plt.plot(yearly_raw["year"], yearly_raw["UNKNOWN_%"],marker="o", label="Unknown % (composite)")
    plt.ylim(0, 100)
    plt.ylabel("Percent of stations"); plt.xlabel("Year")
    plt.title(f"{river_name}: raw-water composite compliance over time")
    plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{base}_raw_compliance_over_time.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
    yearly_raw.to_csv(os.path.join(out_dir, f"{base}_raw_compliance_over_time.csv"),
                      index=False)

    # 6) State-wise compliance (latest year) for both gates
    latest_year = int(latest["year"].max())

    def state_comp(df_latest, col, tag):
        st = (df_latest[["state", col, "station"]]
              .drop_duplicates()
              .groupby(["state", col])["station"].nunique()
              .unstack(fill_value=0)
              .reset_index()
              .sort_values("state"))
        for k in ["SAFE", "UNSAFE", "UNKNOWN"]:
            if k not in st.columns:
                st[k] = 0

        plt.figure(figsize=(12,4))
        x = np.arange(len(st["state"]))
        barw = 0.35
        plt.bar(x - barw/2, st["SAFE"], width=barw, label="Safe")
        plt.bar(x + barw/2, st["UNSAFE"], width=barw, label="Unsafe")

        labels = st["state"].astype(str).tolist()
        plt.xticks(x, labels, rotation=45, ha="right", fontsize=8)

        plt.ylabel("Stations")
        plt.title(f"{river_name}: {tag} compliance (latest {latest_year})")
        plt.legend()
        plt.subplots_adjust(bottom=0.3)
        plt.savefig(os.path.join(
            out_dir,
            f"{base}_{tag.lower().replace(' ','_')}_state_compliance_latest.png"
        ), dpi=150, bbox_inches="tight")
        plt.close()

        st.to_csv(os.path.join(
            out_dir,
            f"{base}_{tag.lower().replace(' ','_')}_state_compliance_latest.csv"
        ), index=False)

    state_comp(latest, "bis_status", "BIS pH")
    state_comp(latest, "raw_status", "Composite raw-water")

    # 7) Parameter correlation matrix (all years)
    corr_cols = [c for c in ["pH","DO_mg_L","BOD_mg_L","conductivity_uScm","nitrate_mg_L"] if c in sub.columns]
    if len(corr_cols) >= 2:
        corr = sub[corr_cols].astype(float).corr()
        plt.figure(figsize=(5,4))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
        plt.title(f"{river_name}: parameter correlation (all years)")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"{base}_param_correlation.png"), dpi=150)
        plt.close()
        corr.to_csv(os.path.join(out_dir, f"{base}_param_correlation.csv"))

def main():
    ap = argparse.ArgumentParser(description="River-wise analysis with BIS pH and composite raw-water gates")
    ap.add_argument("--data", required=True, help="data/processed/water_quality_2016_2023.csv")
    ap.add_argument("--river", required=True, help='River/waterbody name, e.g., "Beas", "Sutlej"')
    ap.add_argument("--out-dir", default="outputs/river_reports")
    args = ap.parse_args()

    df = load_master(args.data)
    analyze_river(df, args.river, args.out_dir)

if __name__ == "__main__":
    main()

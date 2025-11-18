# # analysis/river_analysis_and_plots.py
# import argparse
# import json
# import os
# import re

# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns

# # BIS IS 10500:2012 acceptable pH range for drinking water
# BIS = {"pH_min": 6.5, "pH_max": 8.5}

# def normalize_text(s):
#     return re.sub(r"\s+"," ", str(s)).strip()

# def load_master(path):
#     df = pd.read_csv(path, parse_dates=["date"])
#     # Ensure expected columns exist
#     required = ["year","code","station","state","section_title","pH","waterbody","date"]
#     for c in required:
#         if c not in df.columns:
#             raise ValueError(f"Missing required column: {c}")
#     # Normalize text columns
#     for col in ["station","state","section_title","waterbody"]:
#         df[col] = df[col].astype(str).map(normalize_text)
#     # Enforce types
#     df["year"] = df["year"].astype(int)
#     return df

# def match_waterbody(df, river_name):
#     rn = river_name.strip().upper()
#     # Prefer exact match on parsed waterbody
#     m1 = df["waterbody"].str.upper().str.fullmatch(rn, na=False)
#     if m1.any():
#         return df[m1].copy()
#     # Fallback: station contains river name
#     m2 = df["station"].str.upper().str.contains(rf"\b{re.escape(rn)}\b", na=False)
#     return df[m2].copy()

# def bis_status_row(pH):
#     if pd.isna(pH):
#         return "UNKNOWN", "pH missing"
#     if pH < BIS["pH_min"] or pH > BIS["pH_max"]:
#         return "UNSAFE", "pH outside 6.5–8.5 (BIS IS 10500)"
#     return "SAFE", "Within acceptable limits"

# def pH_deviation(pH):
#     if pd.isna(pH):
#         return np.nan
#     if pH < BIS["pH_min"]:
#         return BIS["pH_min"] - pH
#     if pH > BIS["pH_max"]:
#         return pH - BIS["pH_max"]
#     return 0.0

# def descriptive_stats(series):
#     s = series.dropna()
#     return {
#         "count": int(s.count()),
#         "mean": round(float(s.mean()), 3) if not s.empty else None,
#         "median": round(float(s.median()), 3) if not s.empty else None,
#         "min": round(float(s.min()), 3) if not s.empty else None,
#         "max": round(float(s.max()), 3) if not s.empty else None,
#         "std": round(float(s.std(ddof=1)), 3) if s.count() > 1 else 0.0
#     }

# def analyze_river(df, river_name, out_dir):
#     os.makedirs(out_dir, exist_ok=True)
#     sub = match_waterbody(df, river_name)
#     if sub.empty:
#         result = {"river": river_name, "found": False, "message": "No rows matched"}
#         with open(os.path.join(out_dir, f"{river_name}_report.json"), "w", encoding="utf-8") as f:
#             json.dump(result, f, indent=2, ensure_ascii=False)
#         print(json.dumps(result, indent=2, ensure_ascii=False))
#         return

#     # Compute BIS status and pH deviation
#     sub["bis_status"], sub["bis_reasons"] = zip(*sub["pH"].map(bis_status_row))
#     sub["pH_dev"] = sub["pH"].map(pH_deviation)

#     # Latest per station (annual data -> latest year)
#     latest_idx = sub.sort_values(["date"]).groupby("station").tail(1).index
#     latest = sub.loc[latest_idx].sort_values(["state","station"])

#     verdict_counts = latest["bis_status"].value_counts().to_dict()
#     if verdict_counts.get("UNSAFE", 0) > 0:
#         verdict = "UNSAFE"
#     elif verdict_counts.get("SAFE", 0) > 0:
#         verdict = "SAFE"
#     else:
#         verdict = "UNKNOWN"

#     # Descriptive stats
#     summary = {
#         "pH": descriptive_stats(sub["pH"]),
#         "conductivity_uScm": descriptive_stats(sub["conductivity_uScm"]) if "conductivity_uScm" in sub.columns else {"count": 0},
#         "BOD_mg_L": descriptive_stats(sub["BOD_mg_L"]) if "BOD_mg_L" in sub.columns else {"count": 0},
#         "DO_mg_L": descriptive_stats(sub["DO_mg_L"]) if "DO_mg_L" in sub.columns else {"count": 0},
#         "nitrate_mg_L": descriptive_stats(sub["nitrate_mg_L"]) if "nitrate_mg_L" in sub.columns else {"count": 0},
#     }

#     # Write outputs
#     base = re.sub(r"[^A-Za-z0-9_]+", "_", river_name.strip())
#     sub.to_csv(os.path.join(out_dir, f"{base}_records.csv"), index=False, encoding="utf-8")
#     latest.to_csv(os.path.join(out_dir, f"{base}_latest.csv"), index=False, encoding="utf-8")

#     report = {
#         "river": river_name,
#         "records": int(len(sub)),
#         "stations": int(sub["station"].nunique()),
#         "states": sorted([s for s in sub["state"].dropna().unique()]),
#         "bis_verdict": verdict,
#         "bis_summary_counts": verdict_counts,
#         "descriptive_stats": summary,
#         "notes": "Safe/Unsafe uses BIS IS 10500 pH 6.5–8.5; include turbidity/TDS if available in future datasets."
#     }
#     with open(os.path.join(out_dir, f"{base}_report.json"), "w", encoding="utf-8") as f:
#         json.dump(report, f, indent=2, ensure_ascii=False)
#     print(json.dumps(report, indent=2, ensure_ascii=False))

#     # Plots
#     plt.style.use("seaborn-v0_8-darkgrid")

#     # 1) Yearly trend of pH by state
#     gp = sub.groupby(["year","state"])["pH"].mean().reset_index()
#     if not gp.empty:
#         plt.figure(figsize=(9,4))
#         for st in gp["state"].dropna().unique():
#             s = gp[gp["state"]==st]
#             plt.plot(s["year"], s["pH"], marker="o", label=st)
#         plt.axhspan(BIS["pH_min"], BIS["pH_max"], color="green", alpha=0.12, label="BIS acceptable")
#         plt.title(f"{river_name}: yearly mean pH by state")
#         plt.xlabel("Year"); plt.ylabel("pH"); plt.legend()
#         plt.tight_layout()
#         plt.savefig(os.path.join(out_dir, f"{base}_pH_trend.png"), dpi=150)
#         plt.close()

#     # 2) Station x Year heatmap of pH
#     piv = sub.pivot_table(index="station", columns="year", values="pH", aggfunc="mean")
#     if piv.shape[0] > 0:
#         plt.figure(figsize=(10, max(4, piv.shape[0]*0.25)))
#         sns.heatmap(piv, cmap="RdYlGn", vmin=6.0, vmax=9.0, cbar_kws={"label":"pH"})
#         plt.title(f"{river_name}: station-year pH heatmap")
#         plt.tight_layout()
#         plt.savefig(os.path.join(out_dir, f"{base}_pH_heatmap.png"), dpi=150)
#         plt.close()
#         piv.to_csv(os.path.join(out_dir, f"{base}_pH_pivot.csv"))

#     # 3) Top 5 stations by pH deviation in latest year
#     worst = latest.sort_values("pH_dev", ascending=False).dropna(subset=["pH_dev"]).head(5)
#     if not worst.empty:
#         plt.figure(figsize=(9,4))
#         plt.barh(worst["station"], worst["pH_dev"])
#         plt.gca().invert_yaxis()
#         plt.xlabel("pH deviation from 6.5–8.5")
#         plt.title(f"{river_name}: top 5 stations by pH deviation (latest)")
#         plt.tight_layout()
#         plt.savefig(os.path.join(out_dir, f"{base}_pH_top5.png"), dpi=150)
#         plt.close()

#     # 4) Compliance share over time
#     yearly_status = (
#         sub.assign(year=sub["year"].astype(int))
#            .groupby(["year","bis_status"])["station"].nunique()
#            .unstack(fill_value=0)
#            .reset_index()
#     )
#     yearly_status["TOTAL"] = yearly_status.drop(columns=["year"]).sum(axis=1)
#     for k in ["SAFE","UNSAFE","UNKNOWN"]:
#         if k not in yearly_status.columns: yearly_status[k] = 0
#     yearly_status["SAFE_%"] = 100.0 * yearly_status["SAFE"] / yearly_status["TOTAL"].replace(0, np.nan)
#     yearly_status["UNSAFE_%"] = 100.0 * yearly_status["UNSAFE"] / yearly_status["TOTAL"].replace(0, np.nan)
#     plt.figure(figsize=(9,4))
#     plt.plot(yearly_status["year"], yearly_status["SAFE_%"], marker="o", label="Safe %")
#     plt.plot(yearly_status["year"], yearly_status["UNSAFE_%"], marker="o", label="Unsafe %")
#     plt.ylim(0, 100); plt.ylabel("Percent of stations"); plt.xlabel("Year")
#     plt.title(f"{river_name}: compliance share over time")
#     plt.legend(); plt.tight_layout()
#     plt.savefig(os.path.join(out_dir, f"{base}_compliance_over_time.png"), dpi=150); plt.close()
#     yearly_status.to_csv(os.path.join(out_dir, f"{base}_compliance_over_time.csv"), index=False)

#     # 5) State-wise compliance (latest year)
#     latest_year = int(latest["year"].max())
#     st_comp = (latest[["state","bis_status","station"]]
#                .drop_duplicates()
#                .groupby(["state","bis_status"])["station"].nunique()
#                .unstack(fill_value=0)
#                .reset_index()
#                .sort_values("state"))
#     for k in ["SAFE","UNSAFE","UNKNOWN"]:
#         if k not in st_comp.columns: st_comp[k] = 0
#     st_comp.to_csv(os.path.join(out_dir, f"{base}_state_compliance_latest.csv"), index=False)

#     plt.figure(figsize=(10,4))
#     x = np.arange(len(st_comp["state"]))
#     barw = 0.35
#     plt.bar(x - barw/2, st_comp["SAFE"], width=barw, label="Safe")
#     plt.bar(x + barw/2, st_comp["UNSAFE"], width=barw, label="Unsafe")
#     plt.xticks(x, st_comp["state"], rotation=45, ha="right")
#     plt.ylabel("Stations"); plt.title(f"{river_name}: state-wise compliance (latest year {latest_year})")
#     plt.legend(); plt.tight_layout()
#     plt.savefig(os.path.join(out_dir, f"{base}_state_compliance_latest.png"), dpi=150); plt.close()

#     # 6) Metric distributions (latest year)
#     ly = latest.copy()
#     fig, axes = plt.subplots(1, 5, figsize=(15,3), sharex=False)
#     metrics = [
#         ("pH","pH", (5.5,9.0)),
#         ("DO_mg_L","DO (mg/L)", None),
#         ("BOD_mg_L","BOD (mg/L)", None),
#         ("conductivity_uScm","Conductivity (µS/cm)", None),
#         ("nitrate_mg_L","Nitrate (mg/L)", None),
#     ]
#     for ax, (col, label, xr) in zip(axes, metrics):
#         if col in ly.columns and ly[col].notna().any():
#             ax.hist(ly[col].dropna(), bins=15, color="#4C78A8", alpha=0.8)
#             ax.set_title(label, fontsize=10)
#             if xr: ax.set_xlim(*xr)
#         else:
#             ax.set_visible(False)
#     fig.suptitle(f"{river_name}: latest-year metric distributions (stations)", fontsize=12)
#     plt.tight_layout(rect=[0,0,1,0.95])
#     plt.savefig(os.path.join(out_dir, f"{base}_latest_metric_distributions.png"), dpi=150)
#     plt.close()

#     # 7) Station ranking by deviation (latest year)
#     rank = (latest[["station","state","pH","pH_dev","bis_status","bis_reasons"]]
#             .sort_values("pH_dev", ascending=False))
#     rank.to_csv(os.path.join(out_dir, f"{base}_station_ranking_latest.csv"), index=False)

#     # 8) Longitudinal pH for worst K stations
#     K = 6
#     worst_stations = rank["station"].head(K).tolist()
#     if worst_stations:
#         ts = sub[sub["station"].isin(worst_stations)].copy()
#         plt.figure(figsize=(10,5))
#         for stn in worst_stations:
#             s = ts[ts["station"]==stn].sort_values("year")
#             plt.plot(s["year"], s["pH"], marker="o", label=stn)
#         plt.axhspan(BIS["pH_min"], BIS["pH_max"], color="green", alpha=0.12)
#         plt.title(f"{river_name}: pH trends at top {K} worst stations")
#         plt.xlabel("Year"); plt.ylabel("pH"); plt.legend(fontsize=8)
#         plt.tight_layout()
#         plt.savefig(os.path.join(out_dir, f"{base}_worst_stations_trends.png"), dpi=150)
#         plt.close()

#     # 9) Parameter correlation matrix (all years)
#     corr_cols = [c for c in ["pH","DO_mg_L","BOD_mg_L","conductivity_uScm","nitrate_mg_L"] if c in sub.columns]
#     if len(corr_cols) >= 2:
#         corr = sub[corr_cols].astype(float).corr()
#         plt.figure(figsize=(5,4))
#         sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
#         plt.title(f"{river_name}: parameter correlation (all years)")
#         plt.tight_layout()
#         plt.savefig(os.path.join(out_dir, f"{base}_param_correlation.png"), dpi=150)
#         plt.close()
#         corr.to_csv(os.path.join(out_dir, f"{base}_param_correlation.csv"))

#     # 10) Outlier scatter (latest year)
#     if "conductivity_uScm" in latest.columns and latest["conductivity_uScm"].notna().any():
#         plt.figure(figsize=(8,5))
#         sizes = 20 + 30 * (latest["BOD_mg_L"].fillna(0) / (1 + latest["BOD_mg_L"].fillna(0)))
#         colors = latest["state"].astype('category').cat.codes
#         plt.scatter(latest["pH"], latest["conductivity_uScm"],
#                     c=colors, s=sizes,
#                     cmap="tab10", alpha=0.8, edgecolor="k", linewidths=0.2)
#         plt.axvspan(BIS["pH_min"], BIS["pH_max"], color="green", alpha=0.12)
#         plt.xlabel("pH"); plt.ylabel("Conductivity (µS/cm)")
#         plt.title(f"{river_name}: latest stations (pH vs Conductivity, size ~ BOD)")
#         plt.tight_layout()
#         plt.savefig(os.path.join(out_dir, f"{base}_scatter_ph_conductivity_latest.png"), dpi=150)
#         plt.close()

# def main():
#     ap = argparse.ArgumentParser(description="River-wise analysis and plots (BIS pH gating)")
#     ap.add_argument("--data", required=True, help="data/processed/water_quality_2016_2023.csv")
#     ap.add_argument("--river", required=True, help='River/waterbody name, e.g., "Beas", "Sutlej"')
#     ap.add_argument("--out-dir", default="outputs/river_reports")
#     args = ap.parse_args()

#     df = load_master(args.data)
#     analyze_river(df, args.river, args.out_dir)

# if __name__ == "__main__":
#     main()



# analysis/river_analysis_and_plots.py
import argparse
import json
import os
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# BIS acceptable pH (drinking)
BIS = {"pH_min": 6.5, "pH_max": 8.5}

# Raw surface water suitability thresholds (from Primary Water Quality Criteria / common practice)
RAW = {
    "DO_min": 5.0,                 # mg/L (primary criteria)
    "BOD_max": 3.0,                # mg/L (primary criteria)
    "fecal_coliform_max": 2500.0,  # MPN/100 ml (primary criteria)
    "total_coliform_max": 500.0    # MPN/100 ml (primary criteria)
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
    # Ensure optional numeric columns exist as float
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

# BIS pH-only gate
def bis_status_row(pH):
    if pd.isna(pH):
        return "UNKNOWN", "pH missing"
    if pH < BIS["pH_min"] or pH > BIS["pH_max"]:
        return "UNSAFE", "pH outside 6.5–8.5 (BIS IS 10500)"
    return "SAFE", "Within BIS acceptable pH"

# Composite raw-water gate using available columns
def composite_status_row(row):
    reasons = []
    unknown = False

    # pH check (required)
    pH = row.get("pH", np.nan)
    if pd.isna(pH):
        unknown = True
    else:
        if pH < BIS["pH_min"] or pH > BIS["pH_max"]:
            reasons.append("pH out of 6.5–8.5")

    # DO check
    DO = row.get("DO_mg_L", np.nan)
    if pd.isna(DO):
        unknown = True
    else:
        if DO < RAW["DO_min"]:
            reasons.append("DO < 5 mg/L")

    # BOD check
    BOD = row.get("BOD_mg_L", np.nan)
    if pd.isna(BOD):
        unknown = True
    else:
        if BOD > RAW["BOD_max"]:
            reasons.append("BOD > 3 mg/L")

    # Fecal coliform check (prefer max column if present, else any single value if merged)
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

    # Total coliform check
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

    # BIS (pH-only) gate
    sub["bis_status"], sub["bis_reasons"] = zip(*sub["pH"].map(bis_status_row))
    sub["pH_dev"] = sub["pH"].map(pH_deviation)

    # Composite raw-water gate
    comp_status = []
    comp_reasons = []
    for _, r in sub.iterrows():
        st, rs = composite_status_row(r)
        comp_status.append(st); comp_reasons.append(rs)
    sub["raw_status"] = comp_status
    sub["raw_reasons"] = comp_reasons

    # Latest per station
    latest_idx = sub.sort_values(["date"]).groupby("station").tail(1).index
    latest = sub.loc[latest_idx].sort_values(["state","station"])

    # Verdicts
    bis_counts = latest["bis_status"].value_counts().to_dict()
    bis_verdict = "UNSAFE" if bis_counts.get("UNSAFE", 0) > 0 else ("SAFE" if bis_counts.get("SAFE", 0) > 0 else "UNKNOWN")
    raw_counts = latest["raw_status"].value_counts().to_dict()
    raw_verdict = "UNSAFE" if raw_counts.get("UNSAFE", 0) > 0 else ("SAFE" if raw_counts.get("SAFE", 0) > 0 else "UNKNOWN")

    # Descriptive stats
    summary = {
        "pH": descriptive_stats(sub["pH"]),
        "conductivity_uScm": descriptive_stats(sub["conductivity_uScm"]) if "conductivity_uScm" in sub.columns else {"count": 0},
        "BOD_mg_L": descriptive_stats(sub["BOD_mg_L"]) if "BOD_mg_L" in sub.columns else {"count": 0},
        "DO_mg_L": descriptive_stats(sub["DO_mg_L"]) if "DO_mg_L" in sub.columns else {"count": 0},
        "nitrate_mg_L": descriptive_stats(sub["nitrate_mg_L"]) if "nitrate_mg_L" in sub.columns else {"count": 0},
    }

    # Outputs
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

    # Plots
    plt.style.use("seaborn-v0_8-darkgrid")

    # pH trend by state
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

    # Station x Year pH heatmap
    piv = sub.pivot_table(index="station", columns="year", values="pH", aggfunc="mean")
    if piv.shape[0] > 0:
        plt.figure(figsize=(10, max(4, piv.shape[0]*0.25)))
        sns.heatmap(piv, cmap="RdYlGn", vmin=6.0, vmax=9.0, cbar_kws={"label":"pH"})
        plt.title(f"{river_name}: station-year pH heatmap")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"{base}_pH_heatmap.png"), dpi=150)
        plt.close()
        piv.to_csv(os.path.join(out_dir, f"{base}_pH_pivot.csv"))

    # Top 5 worst pH deviation (latest)
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

    # Compliance share over time (BIS pH)
    yearly_bis = (
        sub.assign(year=sub["year"].astype(int))
           .groupby(["year","bis_status"])["station"].nunique()
           .unstack(fill_value=0)
           .reset_index()
    )
    yearly_bis["TOTAL"] = yearly_bis.drop(columns=["year"]).sum(axis=1)
    for k in ["SAFE","UNSAFE","UNKNOWN"]:
        if k not in yearly_bis.columns: yearly_bis[k] = 0
    yearly_bis["SAFE_%"] = 100.0 * yearly_bis["SAFE"] / yearly_bis["TOTAL"].replace(0, np.nan)
    yearly_bis["UNSAFE_%"] = 100.0 * yearly_bis["UNSAFE"] / yearly_bis["TOTAL"].replace(0, np.nan)
    plt.figure(figsize=(9,4))
    plt.plot(yearly_bis["year"], yearly_bis["SAFE_%"], marker="o", label="Safe % (pH)")
    plt.plot(yearly_bis["year"], yearly_bis["UNSAFE_%"], marker="o", label="Unsafe % (pH)")
    plt.ylim(0, 100); plt.ylabel("Percent of stations"); plt.xlabel("Year")
    plt.title(f"{river_name}: BIS pH compliance over time")
    plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{base}_bis_compliance_over_time.png"), dpi=150); plt.close()
    yearly_bis.to_csv(os.path.join(out_dir, f"{base}_bis_compliance_over_time.csv"), index=False)

    # Composite raw-water compliance over time
    yearly_raw = (
        sub.assign(year=sub["year"].astype(int))
           .groupby(["year","raw_status"])["station"].nunique()
           .unstack(fill_value=0)
           .reset_index()
    )
    yearly_raw["TOTAL"] = yearly_raw.drop(columns=["year"]).sum(axis=1)
    for k in ["SAFE","UNSAFE","UNKNOWN"]:
        if k not in yearly_raw.columns: yearly_raw[k] = 0
    yearly_raw["SAFE_%"] = 100.0 * yearly_raw["SAFE"] / yearly_raw["TOTAL"].replace(0, np.nan)
    yearly_raw["UNSAFE_%"] = 100.0 * yearly_raw["UNSAFE"] / yearly_raw["TOTAL"].replace(0, np.nan)
    plt.figure(figsize=(9,4))
    plt.plot(yearly_raw["year"], yearly_raw["SAFE_%"], marker="o", label="Safe % (composite)")
    plt.plot(yearly_raw["year"], yearly_raw["UNSAFE_%"], marker="o", label="Unsafe % (composite)")
    plt.ylim(0, 100); plt.ylabel("Percent of stations"); plt.xlabel("Year")
    plt.title(f"{river_name}: raw-water composite compliance over time")
    plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{base}_raw_compliance_over_time.png"), dpi=150); plt.close()
    yearly_raw.to_csv(os.path.join(out_dir, f"{base}_raw_compliance_over_time.csv"), index=False)

    # State-wise compliance (latest year) for both gates
    latest_year = int(latest["year"].max())
    def state_comp(df_latest, col, tag):
        st = (df_latest[["state",col,"station"]]
              .drop_duplicates()
              .groupby(["state",col])["station"].nunique()
              .unstack(fill_value=0)
              .reset_index()
              .sort_values("state"))
        for k in ["SAFE","UNSAFE","UNKNOWN"]:
            if k not in st.columns: st[k] = 0
        plt.figure(figsize=(10,4))
        x = np.arange(len(st["state"]))
        barw = 0.35
        plt.bar(x - barw/2, st["SAFE"], width=barw, label="Safe")
        plt.bar(x + barw/2, st["UNSAFE"], width=barw, label="Unsafe")
        plt.xticks(x, st["state"], rotation=45, ha="right")
        plt.ylabel("Stations"); plt.title(f"{river_name}: {tag} compliance (latest {latest_year})")
        plt.legend(); plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"{base}_{tag.lower().replace(' ','_')}_state_compliance_latest.png"), dpi=150); plt.close()
        st.to_csv(os.path.join(out_dir, f"{base}_{tag.lower().replace(' ','_')}_state_compliance_latest.csv"), index=False)

    state_comp(latest, "bis_status", "BIS pH")
    state_comp(latest, "raw_status", "Composite raw-water")

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

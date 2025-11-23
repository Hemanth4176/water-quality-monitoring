# app/analysis/station_analysis.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from utils.fig_to_base64 import fig_to_base64

BIS = {"pH_min": 6.5, "pH_max": 8.5}

def station_summary(df, station_name):
    df_st = df[df["station"].str.lower() == station_name.lower()].copy()
    if df_st.empty:
        return {"error": "Station not found"}

    results = {}
    # mean values
    results["means"] = df_st[["pH","DO_mg_L","BOD_mg_L","conductivity_uScm","nitrate_mg_L"]].mean().to_dict()

    # pH trend
    gp = df_st.groupby("year")["pH"].mean().reset_index()
    if not gp.empty:
        fig = plt.figure(figsize=(8,3))
        plt.plot(gp["year"], gp["pH"], marker='o')
        plt.axhspan(BIS["pH_min"], BIS["pH_max"], color="green", alpha=0.12)
        plt.title(f"{station_name} — pH Trend")
        plt.xlabel("Year"); plt.ylabel("pH")
        results["pH_trend"] = fig_to_base64(fig)
        plt.close()

    # DO trend
    gp_do = df_st.groupby("year")["DO_mg_L"].mean().reset_index()
    if not gp_do.empty:
        fig = plt.figure(figsize=(8,3))
        plt.plot(gp_do["year"], gp_do["DO_mg_L"], marker='o')
        plt.title(f"{station_name} — DO Trend")
        plt.xlabel("Year"); plt.ylabel("DO (mg/L)")
        results["DO_trend"] = fig_to_base64(fig)
        plt.close()

    # violation counts
    latest_year = df_st["year"].max()
    latest = df_st[df_st["year"] == latest_year]
    violations = {
        "pH_dev": int(((latest["pH"] - 7.5).abs()) > 0).sum() if not latest.empty else 0,
        "DO_below_6": int((latest["DO_mg_L"] < 6).sum()) if not latest.empty else 0,
        "BOD_above_3": int((latest["BOD_mg_L"] > 3).sum()) if not latest.empty else 0
    }
    results["violations_latest"] = violations

    return results

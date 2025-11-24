import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from utils.fig_to_base64 import fig_to_base64

BIS = {"pH_min": 6.5, "pH_max": 8.5}

def analyze_river(df, river_name, parameter="pH"):
    river_name_clean = str(river_name).strip().lower()
    df_river = df[df["waterbody"].str.lower() == river_name_clean].copy()

    if df_river.empty:
        return {"error": f"River '{river_name}' not found in data."}

    results = {}

    # -----------------------------
    # 1) TREND (YEARLY MEAN BY STATE)
    # -----------------------------
    gp = df_river.groupby(["year", "state"])[parameter].mean().reset_index()
    if not gp.empty:
        fig = plt.figure(figsize=(9, 4))
        for st in gp["state"].dropna().unique():
            s = gp[gp["state"] == st]
            plt.plot(s["year"], s[parameter], marker="o", label=st)

        plt.title(f"{river_name} – {parameter} Trend by State")
        plt.xlabel("Year")
        plt.ylabel(parameter)
        plt.legend()

        results["trend"] = fig_to_base64(fig)
        plt.close()

    # -----------------------------
    # 2) HEATMAP (STATION × YEAR)
    # -----------------------------
    piv = df_river.pivot_table(index="station", columns="year", values=parameter)
    if piv.size > 0:
        rows = piv.shape[0]
        height = max(4, min(12,0.35*rows))
        fig = plt.figure(figsize=(12, height))
        sns.heatmap(piv, cmap="coolwarm", annot=False)
        plt.title(f"{river_name} – Station-Year Heatmap ({parameter})")

        results["heatmap"] = fig_to_base64(fig)
        plt.close()

    # -----------------------------
    # 3) WORST 5 STATIONS (LATEST YEAR)
    # -----------------------------
    latest_year = df_river["year"].max()
    latest_df = df_river[df_river["year"] == latest_year].copy()

    if not latest_df.empty:
        latest_df["deviation"] = (latest_df[parameter] - latest_df[parameter].mean()).abs()
        worst5 = latest_df.sort_values("deviation", ascending=False).head(5)

        fig = plt.figure(figsize=(9, 4))
        plt.barh(worst5["station"], worst5["deviation"], color="red")
        plt.title(f"{river_name} – Worst 5 Stations ({parameter})")
        plt.gca().invert_yaxis()

        results["worst5"] = fig_to_base64(fig)
        plt.close()

    # -----------------------------
    # 4) CORRELATION MATRIX
    # -----------------------------
    corr_cols = ["pH", "DO_mg_L", "BOD_mg_L", "conductivity_uScm", "nitrate_mg_L"]
    sub = df_river[corr_cols].dropna()

    if len(sub) > 5:
        corr = sub.corr()

        fig = plt.figure(figsize=(6, 5))
        sns.heatmap(corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1)
        plt.title(f"{river_name} – Correlation Matrix")

        results["correlation"] = fig_to_base64(fig)
        plt.close()

    return results


# import pandas as pd
# import matplotlib
# matplotlib.use("Agg")
# import matplotlib.pyplot as plt
# import seaborn as sns
# from utils.fig_to_base64 import fig_to_base64

# # Set a professional, consistent theme for all plots
# sns.set_theme(
#     style="whitegrid", # Clean white background with grid lines
#     rc={
#         "figure.figsize": (10, 5),
#         "axes.edgecolor": "#A0A0A0", # Light grey axes
#         "axes.labelcolor": "#333333", # Dark text
#         "xtick.color": "#333333",
#         "ytick.color": "#333333",
#         "font.family": "sans-serif" # Use default system font
#     }
# )

# # Custom Color Palettes for better aesthetics
# LINE_PALETTE = sns.color_palette("viridis", 10) # Sequential colors for states/lines
# HEATMAP_CMAP = "YlGnBu" # Blue-green for water quality data heatmaps
# CORR_CMAP = "vlag" # Diverging for correlation (shows + and - strongly)
# BAR_COLOR = "#E74C3C" # Red for "Worst" metric deviation

# BIS = {"pH_min": 6.5, "pH_max": 8.5}

# def analyze_river(df, river_name, parameter="pH"):
#     river_name_clean = str(river_name).strip().lower()
#     df_river = df[df["waterbody"].str.lower() == river_name_clean].copy()

#     if df_river.empty:
#         return {"error": f"River '{river_name}' not found in data."}

#     results = {}

#     # -----------------------------
#     # 1) TREND (YEARLY MEAN BY STATE) - Stunning Line Plot
#     # -----------------------------
#     gp = df_river.groupby(["year", "state"])[parameter].mean().reset_index()
#     if not gp.empty:
#         plt.figure(figsize=(10, 5.5))
        
#         # Use Seaborn lineplot for stunning, smooth lines and confidence bands
#         sns.lineplot(
#             data=gp, 
#             x="year", 
#             y=parameter, 
#             hue="state", 
#             palette=LINE_PALETTE,
#             marker="o", 
#             linewidth=2,
#             alpha=0.8
#         )
        
#         plt.title(
#             f"{river_name} – Yearly Average {parameter} Trend by State", 
#             fontsize=15, 
#             weight='bold', 
#             pad=15
#         )
#         plt.xlabel("Year", fontsize=12)
#         plt.ylabel(f"Average {parameter}", fontsize=12)
#         plt.legend(title="State", bbox_to_anchor=(1.05, 1), loc='upper left', frameon=False)
#         plt.grid(axis='x', linestyle='--', alpha=0.5) # Keep vertical grid light

#         # Optional: Add BIS/quality standard lines if applicable (e.g., for pH)
#         if parameter == "pH":
#             plt.axhspan(BIS["pH_min"], BIS["pH_max"], color='green', alpha=0.1, label='BIS Range')
#             plt.axhline(BIS["pH_min"], color='green', linestyle='--', alpha=0.7)
#             plt.axhline(BIS["pH_max"], color='green', linestyle='--', alpha=0.7)
        
#         plt.tight_layout()
#         results["trend"] = fig_to_base64(plt.gcf())
#         plt.close()

#     # -----------------------------
#     # 2) HEATMAP (STATION × YEAR) - Stunning Heatmap
#     # -----------------------------
#     piv = df_river.pivot_table(index="station", columns="year", values=parameter)
#     if piv.size > 0:
#         rows = piv.shape[0]
#         height = max(5, min(14, 0.4 * rows)) # Dynamically adjust height
        
#         plt.figure(figsize=(12, height))
        
#         # Use an aesthetic sequential color map and add lines for clarity
#         sns.heatmap(
#             piv, 
#             cmap=HEATMAP_CMAP, 
#             annot=False, 
#             linewidths=.5, 
#             linecolor='white', 
#             cbar_kws={'label': f'Average {parameter} Value'}
#         )
        
#         plt.title(
#             f"{river_name} – Station-Year Heatmap ({parameter})", 
#             fontsize=15, 
#             weight='bold', 
#             pad=15
#         )
#         plt.xlabel("Year", fontsize=12)
#         plt.ylabel("Station", fontsize=12)
#         plt.yticks(rotation=0) # Make station names horizontal
        
#         plt.tight_layout()
#         results["heatmap"] = fig_to_base64(plt.gcf())
#         plt.close()

#     # -----------------------------
#     # 3) WORST 5 STATIONS (LATEST YEAR) - Stunning Bar Chart
#     # -----------------------------
#     latest_year = df_river["year"].max()
#     latest_df = df_river[df_river["year"] == latest_year].copy()

#     if not latest_df.empty:
#         # Calculate deviation and sort
#         latest_df["deviation"] = (latest_df[parameter] - latest_df[parameter].mean()).abs()
#         worst5 = latest_df.sort_values("deviation", ascending=False).head(5)
        
#         plt.figure(figsize=(10, 5))
        
#         # Use Seaborn barplot for aesthetic horizontal bars
#         sns.barplot(
#             x="deviation", 
#             y="station", 
#             data=worst5, 
#             color=BAR_COLOR, 
#             edgecolor=".2" # Darker edges for definition
#         )
        
#         plt.title(
#             f"{river_name} – Top 5 Stations with Highest Deviation from Mean {parameter} ({latest_year})", 
#             fontsize=15, 
#             weight='bold', 
#             pad=15
#         )
#         plt.xlabel(f"Absolute Deviation from Mean {parameter}", fontsize=12)
#         plt.ylabel("Station Name", fontsize=12)
        
#         plt.tight_layout()
#         results["worst5"] = fig_to_base64(plt.gcf())
#         plt.close()

#     # -----------------------------
#     # 4) CORRELATION MATRIX - Stunning Correlation Heatmap
#     # -----------------------------
#     corr_cols = ["pH", "DO_mg_L", "BOD_mg_L", "conductivity_uScm", "nitrate_mg_L"]
#     sub = df_river[corr_cols].dropna()

#     if len(sub) > 5:
#         corr = sub.corr()
        
#         plt.figure(figsize=(8, 7)) # Slightly larger figure for better detail
        
#         # Use diverging color map and mask the upper triangle for elegance
#         mask = np.triu(corr)
#         sns.heatmap(
#             corr, 
#             annot=True, 
#             fmt=".2f", # Format annotations to 2 decimal places
#             cmap=CORR_CMAP, 
#             vmin=-1, 
#             vmax=1, 
#             center=0, # Center the color scale on zero
#             linewidths=.5, 
#             linecolor='white',
#             mask=mask # Hide the redundant upper triangle
#         )
        
#         plt.title(
#             f"{river_name} – Parameter Correlation Matrix", 
#             fontsize=15, 
#             weight='bold', 
#             pad=15
#         )
#         plt.xticks(rotation=45, ha='right') # Rotate x-labels for clarity
#         plt.yticks(rotation=0)
        
#         plt.tight_layout()
#         results["correlation"] = fig_to_base64(plt.gcf())
#         plt.close()

#     return results
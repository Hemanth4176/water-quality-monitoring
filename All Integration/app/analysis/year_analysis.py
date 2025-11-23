# app/analysis/year_analysis.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from utils.fig_to_base64 import fig_to_base64

def year_boxplot(df, year, param="pH"):
    df_y = df[df["year"] == int(year)].copy()
    if df_y.empty:
        return {"error": "No data for year"}

    fig = plt.figure(figsize=(8,4))
    sns.boxplot(x="station", y=param, data=df_y)
    plt.xticks(rotation=90)
    plt.title(f"{param} distribution across stations in {year}")
    return fig_to_base64(fig)

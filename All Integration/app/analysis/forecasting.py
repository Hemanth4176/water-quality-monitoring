# app/analysis/forecasting.py
import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet
from utils.fig_to_base64 import fig_to_base64

def forecast_station_param(df, station_name, param="pH", years_ahead=5):
    df_st = df[df["station"].str.lower() == station_name.lower()].copy()
    if df_st.empty:
        return {"error": "Station not found"}

    # prepare time series (use year as timestamp)
    ts = df_st.groupby("year")[param].mean().reset_index().dropna()
    if ts.empty or len(ts) < 3:
        return {"error": "Not enough data for forecasting"}

    prophet_df = pd.DataFrame({
        "ds": pd.to_datetime(ts["year"].astype(int).astype(str) + "-01-01"),
        "y": ts[param].astype(float)
    })

    m = Prophet(yearly_seasonality=False)
    m.fit(prophet_df)

    future = m.make_future_dataframe(periods=years_ahead, freq="Y")
    forecast = m.predict(future)

    # plot
    fig, ax = plt.subplots(figsize=(9,4))
    ax.plot(prophet_df["ds"], prophet_df["y"], "o", label="Historical")
    ax.plot(forecast["ds"], forecast["yhat"], label="Forecast", linestyle="--")
    ax.fill_between(forecast["ds"], forecast["yhat_lower"], forecast["yhat_upper"], alpha=0.2)
    ax.set_title(f"Forecast for {param} at {station_name}")
    ax.set_xlabel("Year")
    ax.set_ylabel(param)
    ax.legend()

    img = fig_to_base64(fig)
    # return future numeric values as list of dicts
    future_rows = forecast[["ds","yhat","yhat_lower","yhat_upper"]].tail(years_ahead).copy()
    future_rows["ds"] = future_rows["ds"].dt.strftime("%Y")
    return {"image": img, "forecast": future_rows.to_dict(orient="records")}

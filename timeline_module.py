# timeline_module.py
from __future__ import annotations
import pandas as pd
import plotly.express as px

def _add_period(df: pd.DataFrame, granularity: str = "M") -> pd.DataFrame:
    dd = df.copy()
    dd["period"] = dd["date"].dt.to_period(granularity).dt.to_timestamp()
    return dd

def frequency(df: pd.DataFrame, granularity: str = "M") -> pd.DataFrame:
    dd = _add_period(df, granularity)
    return dd.groupby("period").size().reset_index(name="events")

def avg_sentiment(df: pd.DataFrame, granularity: str = "M") -> pd.DataFrame:
    dd = _add_period(df, granularity)
    return dd.groupby("period")["sentiment"].mean().reset_index()

def type_frequencies(df: pd.DataFrame, top_k: int = 10, granularity: str = "M") -> pd.DataFrame:
    dd = _add_period(df, granularity)
    ex = dd.explode("event_types").dropna(subset=["event_types"])
    top = ex["event_types"].value_counts().head(top_k).index.tolist()
    ex = ex[ex["event_types"].isin(top)]
    return ex.groupby(["period", "event_types"]).size().reset_index(name="count")

def add_rolling_mean(df: pd.DataFrame, y: str, window: int = 3) -> pd.DataFrame:
    dd = df.copy()
    dd[f"{y}_roll"] = dd[y].rolling(window=window, center=True, min_periods=1).mean()
    return dd

def mark_local_peaks(df: pd.DataFrame, y: str) -> pd.DataFrame:
    dd = df.reset_index(drop=True).copy()
    dd["is_peak"] = False
    for i in range(1, len(dd) - 1):
        if dd.loc[i, y] > dd.loc[i-1, y] and dd.loc[i, y] > dd.loc[i+1, y]:
            dd.loc[i, "is_peak"] = True
    return dd

def make_figs(df: pd.DataFrame, granularity: str = "M"):
    freq = frequency(df, granularity)
    sent = avg_sentiment(df, granularity)
    types = type_frequencies(df, top_k=10, granularity=granularity)

    freq_roll = add_rolling_mean(freq, y="events", window=3)
    sent_roll = add_rolling_mean(sent, y="sentiment", window=3)

    freq_peaks = mark_local_peaks(freq, y="events")
    sent_peaks = mark_local_peaks(sent, y="sentiment")

    title_suffix = "per Month" if granularity == "M" else "per Week"

    fig_freq = px.line(freq, x="period", y="events", title=f"Events {title_suffix}", markers=True)
    fig_freq.add_scatter(
        x=freq_roll["period"], y=freq_roll["events_roll"], mode="lines", name="Rolling mean"
    )
    peaks_df = freq_peaks[freq_peaks["is_peak"]]
    if not peaks_df.empty:
        fig_freq.add_scatter(
            x=peaks_df["period"], y=peaks_df["events"], mode="markers",
            name="Local peaks", marker=dict(size=10, symbol="star")
        )

    fig_sent = px.line(sent, x="period", y="sentiment", title=f"Average Sentiment {title_suffix}", markers=True)
    fig_sent.add_scatter(
        x=sent_roll["period"], y=sent_roll["sentiment_roll"], mode="lines", name="Rolling mean"
    )
    s_peaks = sent_peaks[sent_peaks["is_peak"]]
    if not s_peaks.empty:
        fig_sent.add_scatter(
            x=s_peaks["period"], y=s_peaks["sentiment"], mode="markers",
            name="Local peaks", marker=dict(size=10, symbol="triangle-up")
        )

    fig_types = px.line(
        types, x="period", y="count", color="event_types",
        title=f"Top Event Types Over Time ({'Monthly' if granularity=='M' else 'Weekly'})",
        markers=True
    )

    return fig_freq, fig_sent, fig_types

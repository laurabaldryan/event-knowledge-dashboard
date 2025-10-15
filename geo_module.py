from __future__ import annotations
from typing import Dict, Tuple, Optional, List, Literal

import pandas as pd
import folium
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim

ColorMode = Literal["sentiment", "taxonomy"]


def load_geocache(path: str) -> Dict[str, Tuple[float, float]]:
    try:
        df = pd.read_csv(path)
        return {row["location"]: (float(row["lat"]), float(row["lon"])) for _, row in df.iterrows()}
    except Exception:
        return {}

def save_geocache(path: str, cache: Dict[str, Tuple[float, float]]):
    if not cache:
        return
    df = pd.DataFrame([{"location": k, "lat": v[0], "lon": v[1]} for k, v in cache.items()])
    df.to_csv(path, index=False)

def geocode_location_cached(
    geo: Nominatim,
    loc: str,
    cache: Dict[str, Tuple[float, float]]
) -> Optional[Tuple[float, float]]:
    if not loc:
        return None
    if loc in cache:
        return cache[loc]
    try:
        r = geo.geocode(loc, timeout=10)
        if r:
            cache[loc] = (r.latitude, r.longitude)
            return cache[loc]
    except Exception:
        return None
    return None


def _aggregate_by_location(fdf: pd.DataFrame) -> pd.DataFrame:
    ex = fdf.explode("event_types")
    top_types = (
        ex.groupby(["event_location", "event_types"])
          .size()
          .reset_index(name="count")
          .sort_values(["event_location", "count"], ascending=[True, False])
          .groupby("event_location")
          .head(3)
          .groupby("event_location")["event_types"]
          .apply(lambda s: ", ".join(s.astype(str)))
    )

    base = (
        fdf.groupby("event_location")
           .agg(
               n_events=("event_title", "size"),
               avg_sentiment=("sentiment", "mean"),
               titles_preview=("event_title", lambda s: "<br>".join(s.astype(str).head(12)))
           )
    )

    out = base.join(top_types.rename("top_types"), how="left").reset_index()
    out["top_types"] = out["top_types"].fillna("")
    return out

def _color_by_sentiment(avg_sentiment: float, neg_thresh: float = -1.0, pos_thresh: float = 1.0) -> str:
    if avg_sentiment is None:
        return "gray"
    if avg_sentiment > pos_thresh:
        return "green"
    if avg_sentiment < neg_thresh:
        return "red"
    return "gray"

def _color_by_taxonomy(top_types: str) -> str:
    palette = {
        "Treaty": "#2ecc71",
        "Sanctions": "#e74c3c",
        "Protest": "#e67e22",
        "Attack": "#c0392b",
        "Negotiation": "#27ae60",
        "Aid": "#1abc9c",
        "Diplomacy": "#3498db",
        "Trade": "#9b59b6",
    }
    for label, color in palette.items():
        if label.lower() in top_types.lower():
            return color
    return "#95a5a6"

def build_folium_map(
    fdf: pd.DataFrame,
    coords: List[Tuple[str, float, float]],
    *,
    color_mode: ColorMode = "sentiment",
    sentiment_thresholds: Tuple[float, float] = (-1.0, 1.0),
    min_radius: int = 4,
    max_radius: int = 10,
    add_legend: bool = True
) -> folium.Map:

    if coords:
        mean_lat = sum(c[1] for c in coords) / len(coords)
        mean_lon = sum(c[2] for c in coords) / len(coords)
    else:
        mean_lat, mean_lon = 20.0, 0.0

    fmap = folium.Map(location=[mean_lat, mean_lon], zoom_start=2, tiles="CartoDB positron", control_scale=True)
    cluster = MarkerCluster().add_to(fmap)

    agg = _aggregate_by_location(fdf).set_index("event_location")

    if not agg.empty:
        n_min, n_max = int(agg["n_events"].min()), int(agg["n_events"].max())
    else:
        n_min, n_max = 1, 1

    def _scale_radius(n: int) -> int:
        if n_max == n_min:
            return (min_radius + max_radius) // 2
        return int(min_radius + (n - n_min) * (max_radius - min_radius) / (n_max - n_min))

    neg_t, pos_t = sentiment_thresholds
    for loc, lat, lon in coords:
        if loc not in agg.index:
            continue

        row = agg.loc[loc]
        n = int(row["n_events"])
        avg_s = float(row["avg_sentiment"]) if pd.notnull(row["avg_sentiment"]) else 0.0
        top_types = str(row.get("top_types", ""))
        titles = str(row.get("titles_preview", ""))

        if color_mode == "taxonomy":
            color = _color_by_taxonomy(top_types)
            fill_color = color
        else:
            color = _color_by_sentiment(avg_s, neg_thresh=neg_t, pos_thresh=pos_t)
            fill_color = color

        radius = _scale_radius(n)

        popup_html = (
            f"<b>{loc}</b><br>"
            f"Events: {n}<br>"
            f"Avg sentiment: {avg_s:.2f}<br>"
            f"Top types: {top_types or '—'}<br><br>"
            f"{titles}"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color=color,
            fill=True,
            fill_color=fill_color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=360),
        ).add_to(cluster)

    if add_legend:
        _add_legend_html(fmap, color_mode, sentiment_thresholds)

    return fmap


def _add_legend_html(m: folium.Map, color_mode: ColorMode, sentiment_thresholds: Tuple[float, float]):
    if color_mode == "sentiment":
        neg_t, pos_t = sentiment_thresholds
        html = f"""
        <div style="position: fixed; bottom: 25px; left: 25px; z-index: 9999; 
                    background: white; padding: 10px 12px; border-radius: 6px; 
                    box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-size: 12px;">
            <b>Legend (sentiment)</b><br>
            <span style="display:inline-block;width:12px;height:12px;background:red;margin-right:6px;"></span> &lt; {neg_t}<br>
            <span style="display:inline-block;width:12px;height:12px;background:gray;margin-right:6px;"></span> [{neg_t}, {pos_t}]<br>
            <span style="display:inline-block;width:12px;height:12px;background:green;margin-right:6px;"></span> &gt; {pos_t}<br>
        </div>
        """
    else:
        html = """
        <div style="position: fixed; bottom: 25px; left: 25px; z-index: 9999; 
                    background: white; padding: 10px 12px; border-radius: 6px; 
                    box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-size: 12px;">
            <b>Legend (taxonomy)</b><br>
            Colors map to top taxonomy labels (e.g., Treaties, Sanctions, Diplomacy).
        </div>
        """
    folium.Marker(location=[-90, -180], opacity=0)  # dummy to force overlay
    m.get_root().html.add_child(folium.Element(html))

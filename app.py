import time
from datetime import date
from itertools import chain
from typing import Tuple, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

from config import DEFAULT_EVENTS_PATH, DEFAULT_TAXONOMY_PATH, GEOCACHE_PATH
from utils_data import load_json, build_dataframe
from graph_module import build_cooccurrence_graph, top_centralities_table, pyvis_html
from geo_module import load_geocache, save_geocache, geocode_location_cached, build_folium_map
from timeline_module import make_figs

st.set_page_config(page_title="Event Knowledge Dashboard", layout="wide")
st.title("Event Knowledge Graph, Geospatial, and Temporal Visualization")
st.caption("Data visualization dashboard for event-based analysis")

@st.cache_data(show_spinner=False)
def _load_df(events_path: str, taxonomy_path: str) -> pd.DataFrame | None:
    events_json = load_json(events_path)
    taxonomy_json = load_json(taxonomy_path)
    if events_json is None or taxonomy_json is None:
        return None
    return build_dataframe(events_json, taxonomy_json)

df = _load_df(DEFAULT_EVENTS_PATH, DEFAULT_TAXONOMY_PATH)
if df is None:
    st.error("Could not load the default JSON files. Please check paths in config.py.")
    st.stop()

st.success(f"Loaded {len(df)} events from the default dataset.")

st.sidebar.header("Filters")

if df.empty:
    min_d = date(2000, 1, 1)
    max_d = date.today()
else:
    min_d = df["date"].min().date()
    max_d = df["date"].max().date()

date_range = st.sidebar.slider("Date range", min_value=min_d, max_value=max_d, value=(min_d, max_d))
sent_range = st.sidebar.slider("Sentiment range", -10.0, 10.0, (-10.0, 10.0), step=0.5)
all_types = sorted(set(chain.from_iterable(df["event_types"].tolist())))
type_filter = st.sidebar.multiselect("Event types (taxonomy)", options=all_types, default=[])
entity_query = st.sidebar.text_input("Entity contains (optional)")
min_edge_w = st.sidebar.slider("Minimum edge weight (co-occurrence)", 1, 10, 1)

def apply_filters(df_in: pd.DataFrame) -> pd.DataFrame:
    m = (df_in["date"].dt.date >= date_range[0]) & (df_in["date"].dt.date <= date_range[1])
    m &= (df_in["sentiment"] >= sent_range[0]) & (df_in["sentiment"] <= sent_range[1])
    if type_filter:
        m &= df_in["event_types"].apply(lambda lst: any(t in lst for t in type_filter))
    if entity_query.strip():
        q = entity_query.strip().lower()
        m &= df_in["entity_names"].apply(lambda lst: any(q in (x or "").lower() for x in lst))
    return df_in[m].copy()

fdf = apply_filters(df)
st.sidebar.info(f"{len(fdf)} events after filters")

tab1, tab2, tab3 = st.tabs(["Knowledge Graph", "Geospatial Map", "Timeline"])

with tab1:
    st.subheader("Entity Co-occurrence Graph")
    G = build_cooccurrence_graph(fdf)
    to_remove = [(u, v) for u, v, d in G.edges(data=True) if d.get("weight", 0) < min_edge_w]
    G.remove_edges_from(to_remove)
    G.remove_nodes_from([n for n in list(G.nodes()) if G.degree(n) == 0])
    if len(G) == 0:
        st.info("No edges remaining after filters or threshold.")
    else:
        top_rows = top_centralities_table(G, top_n=15)
        st.dataframe(pd.DataFrame(top_rows), use_container_width=True, height=350)
        try:
            html = pyvis_html(G)
            components.html(html, height=700, scrolling=True)
        except Exception as e:
            st.error(f"Graph render error: {e}")

with tab2:
    st.subheader("Event Locations on World Map")
    color_mode_choice = st.radio("Marker color mode", options=["Sentiment", "Taxonomy"], horizontal=True)
    color_mode_val = "sentiment" if color_mode_choice == "Sentiment" else "taxonomy"
    cache = load_geocache(GEOCACHE_PATH)
    geolocator = Nominatim(user_agent="event_dashboard")
    unique_locations = sorted({loc for loc in fdf["event_location"].fillna("").tolist() if loc})
    with st.expander("Geocoding options", expanded=False):
        max_new = st.slider("Max NEW locations to geocode this run", 0, 300, 80)
        run_geo = st.button("Run geocoding for new locations")
    coords: List[Tuple[str, float, float]] = []
    for loc in unique_locations:
        if loc in cache:
            lat, lon = cache[loc]
            coords.append((loc, lat, lon))
    if run_geo:
        new_locs = [loc for loc in unique_locations if loc not in cache][:max_new]
        if new_locs:
            prog = st.progress(0.0, text="Geocoding…")
            for i, loc in enumerate(new_locs, start=1):
                latlon = geocode_location_cached(geolocator, loc, cache)
                if latlon:
                    coords.append((loc, *latlon))
                time.sleep(1.0)
                prog.progress(i / len(new_locs), text=f"Geocoding {i}/{len(new_locs)}")
            save_geocache(GEOCACHE_PATH, cache)
            st.success(f"Geocoded {len(new_locs)} new locations and updated cache.")
        else:
            st.info("No new locations to geocode; everything is already cached.")
    if coords:
        try:
            fmap = build_folium_map(fdf, coords, color_mode=color_mode_val)
            st_folium(fmap, width=None, height=650)
        except Exception as e:
            st.error(f"Map render error: {e}")
    else:
        st.info("No geocoded locations found yet. Click **Run geocoding** to add coordinates.")

with tab3:
    st.subheader("Temporal Evolution of Events and Sentiment")
    if fdf.empty:
        st.info("No events available for selected filters.")
    else:
        granularity_choice = st.radio("Time granularity", options=["Monthly", "Weekly"], horizontal=True)
        gran = "M" if granularity_choice == "Monthly" else "W"
        try:
            fig_freq, fig_sent, fig_types = make_figs(fdf, granularity=gran)
            if getattr(fig_freq, "data", None):
                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(fig_freq, use_container_width=True)
                with c2:
                    st.plotly_chart(fig_sent, use_container_width=True)
            else:
                st.info("No temporal points to display for the current filters.")
            st.plotly_chart(fig_types, use_container_width=True)
        except Exception as e:
            st.error(f"Timeline render error: {e}")

st.caption("Developed using Streamlit, NetworkX, PyVis, Folium, Plotly, and Geopy.")

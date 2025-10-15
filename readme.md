# Event Knowledge Dashboard
## Overview

The Event Knowledge Dashboard is an interactive data visualization app built with Streamlit.
It enables exploration of structured event data through knowledge graphs, geospatial maps, and temporal timelines.

The dashboard integrates information from:

- event_information_sample.json — structured events extracted from news articles.

- event_taxonomy.json — a hierarchical taxonomy that assigns categories and sentiment values to event types.

## Project Structure

| File                 | Purpose                                                                   |
| -------------------- | ------------------------------------------------------------------------- |
| `app.py`             | Main Streamlit dashboard with tabs for Graph, Map, and Timeline.          |
| `utils_data.py`      | Loads and processes JSON data into a unified DataFrame.                   |
| `graph_module.py`    | Builds co-occurrence networks of entities using NetworkX and PyVis.       |
| `geo_module.py`      | Handles geocoding, caching, and Folium map visualization.                 |
| `timeline_module.py` | Creates time-series charts of event frequency and sentiment using Plotly. |
| `config.py`          | Defines paths for event data, taxonomy, and cache file.                   |
| `requirements.txt`   | Lists dependencies needed to run the dashboard.                           |

## Approach
1) Data Processing
- JSON files are parsed and converted into a unified DataFrame containing event titles, entities, locations, dates, and sentiment values.
- Sentiment is computed by averaging taxonomy-based polarity values.
2) Knowledge Graph Visualization
- Entities are connected when they co-occur in the same event.
- Edge weights represent co-occurrence frequency.
- Edges and nodes are colored based on average sentiment.
3) Geospatial Visualization
- Each event location is geocoded using Geopy (Nominatim).
- Coordinates are saved in a local CSV (geocache.csv) to avoid redundant requests.
- Folium displays a world map of events, colored by sentiment or taxonomy type.
4) Timeline Visualization
- Uses Plotly to plot the number of events and average sentiment over time (monthly or weekly).
- Also displays the frequency of top event types.

## Key Design Decisions

- Modular Design: Separate Python modules for graph, geospatial, and timeline logic.
- Caching: Geocoded coordinates are cached locally for faster subsequent runs.
- Filtering: Users can filter by date range, sentiment range, event type, and entity name.
- Interactivity: The app provides three complementary analytical views: graph-based, spatial, and temporal.


##  Installation and Usage
### 1. Clone the Repository
--------------------------------------------------------------------------------------------------------------------------------------------------------------------
git clone https://github.com/<your-username>/event-knowledge-dashboard.git
cd event-knowledge-dashboard
--------------------------------------------------------------------------------------------------------------------------------------------------------------------

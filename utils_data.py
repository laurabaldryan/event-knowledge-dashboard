from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

def load_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def flatten_events(events_json: list) -> List[dict]:
    flat = []
    for group in events_json:
        flat.extend(group)
    return flat

def parse_event_date(d: dict) -> Optional[datetime]:
    try:
        kind = d.get("kind")
        if kind == "single":
            return datetime.strptime(d["date"], "%d/%m/%Y")
        elif kind == "range":
            return datetime.strptime(d["end"], "%d/%m/%Y")
    except Exception:
        return None
    return None

def taxonomy_sentiment_lookup(taxonomy: dict, category: str, label: str) -> float:
    node = taxonomy.get(category, {})
    if isinstance(node, dict) and label in node:
        return float(node[label].get("sentiment", 0))
    if isinstance(node, dict) and "other" in node and isinstance(node["other"], dict):
        return float(node["other"].get("sentiment", 0))
    return 0.0

def event_sentiment(event: dict, taxonomy: dict) -> float:
    sentiments = []
    ec = event.get("event_classifications", {}) or {}
    for category, labels in ec.items():
        for lab in labels:
            sentiments.append(taxonomy_sentiment_lookup(taxonomy, category, lab))
    return sum(sentiments)/len(sentiments) if sentiments else 0.0

def extract_event_types(event: dict) -> List[str]:
    ec = event.get("event_classifications", {}) or {}
    out = []
    for _, labels in ec.items():
        out.extend(labels)
    return out

def build_dataframe(events_json: list, taxonomy: dict) -> pd.DataFrame:
    rows = []
    for ev in flatten_events(events_json):
        date_obj = parse_event_date(
            ev.get("event_date_occured") or ev.get("event_date_occurred") or {}
        )
        entities = ev.get("entities", []) or []
        rows.append({
            "event_title": ev.get("event_title", ""),
            "event_location": ev.get("event_location", ""),
            "date": date_obj,
            "entity_names": [e.get("name") for e in entities if e.get("name")],
            "entity_tags": [e.get("tag") for e in entities if e.get("tag")],
            "sentiment": event_sentiment(ev, taxonomy),
            "event_types": extract_event_types(ev),
            "_raw": ev,
        })
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    return df

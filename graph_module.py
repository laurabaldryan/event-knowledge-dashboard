from __future__ import annotations
from itertools import combinations
from typing import List, Dict

import pandas as pd
import networkx as nx
from pyvis.network import Network

def build_cooccurrence_graph(df: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    for _, row in df.iterrows():
        ents = row["entity_names"]
        if not ents or len(ents) < 2:
            continue

        for name in set(ents):
            if not G.has_node(name):
                G.add_node(name)

        for a, b in combinations(sorted(set(ents)), 2):
            if G.has_edge(a, b):
                G[a][b]["weight"] += 1
                G[a][b]["sentiments"].append(row["sentiment"])
                G[a][b]["event_types"].extend(row["event_types"])
                G[a][b]["event_titles"].append(row["event_title"])
            else:
                G.add_edge(
                    a, b,
                    weight=1,
                    sentiments=[row["sentiment"]],
                    event_types=list(row["event_types"]),
                    event_titles=[row["event_title"]],
                )

    for _, _, data in G.edges(data=True):
        s = data.get("sentiments", [])
        data["mean_sentiment"] = sum(s)/len(s) if s else 0.0
    return G

def top_centralities_table(G: nx.Graph, top_n: int = 15) -> List[Dict]:
    if len(G) == 0:
        return []
    deg = nx.degree_centrality(G)
    btw = nx.betweenness_centrality(G)
    try:
        evc = nx.eigenvector_centrality(G, max_iter=1000)
    except Exception:
        evc = {n: 0.0 for n in G.nodes()}
    rows = [
        {"entity": n, "degree": deg.get(n,0), "betweenness": btw.get(n,0),
         "eigenvector": evc.get(n,0), "degree_raw": G.degree(n)}
        for n in G.nodes()
    ]
    rows.sort(key=lambda r: r["degree"], reverse=True)
    return rows[:top_n]

def pyvis_html(G: nx.Graph, height="650px", width="100%") -> str:
    net = Network(height=height, width=width, directed=False, bgcolor="#0b0f19", font_color="white")
    net.barnes_hut(gravity=-20000, central_gravity=0.1, spring_length=150, spring_strength=0.02, damping=0.09)

    if len(G) == 0:
        return net.generate_html()

    degc = nx.degree_centrality(G)
    btw = nx.betweenness_centrality(G)
    try:
        evc = nx.eigenvector_centrality(G, max_iter=1000)
    except Exception:
        evc = {n: 0.0 for n in G.nodes()}

    for n in G.nodes():
        size = 12 + (degc.get(n, 0) * 70)
        title = (
            f"<b>{n}</b><br>"
            f"Degree: {degc.get(n,0):.3f}<br>"
            f"Betweenness: {btw.get(n,0):.3f}<br>"
            f"Eigenvector: {evc.get(n,0):.3f}"
        )
        net.add_node(n, label=n, title=title, value=size)

    for u, v, d in G.edges(data=True):
        w = d.get("weight", 1)
        mean_s = float(d.get("mean_sentiment", 0))
        color = "#95a5a6"
        if mean_s > 1:
            color = "#2ecc71"
        elif mean_s < -1:
            color = "#e74c3c"
        etypes = ", ".join(sorted(set(map(str, d.get("event_types", [])))))
        titles = "<br>".join(d.get("event_titles", [])[:12])
        tooltip = f"Weight: {w}<br>Mean sentiment: {mean_s:.2f}<br>Types: {etypes}<br><br><b>Sample events</b><br>{titles}"
        net.add_edge(u, v, value=w, color=color, title=tooltip, width=1 + min(w, 10))

    return net.generate_html()

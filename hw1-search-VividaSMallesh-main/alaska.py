"""
Alaska Airlines Flight Path Finder
Author: [Your Name]
Date: [Date]

This program loads Alaska Airlines flight data and airport locations,
builds a weighted graph, and finds routes between airports using
BFS, DFS, and A* search algorithms. Results are visualized on a map.
"""

import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import math
import os


# ---------------------------------------------------------------------------
# Data Loading & Graph Construction
# ---------------------------------------------------------------------------

def haversine(coord1, coord2):
    """
    Calculate the great-circle distance in miles between two points
    given as (longitude, latitude) tuples.
    """
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    R = 3958.8  # Earth radius in miles

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def build_graph():
    """
    Load airport and flight data, build and return a weighted NetworkX graph.
    Nodes are airport IATA codes; edge weights are haversine distances in miles.
    Also returns pos dict {code: (lon, lat)} for drawing.
    """
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    flights = pd.read_csv(os.path.join(base, 'as.csv'))
    airports = pd.read_csv(os.path.join(base, 'airport_codes.csv'))

    uniques = pd.concat([flights['ORIGIN'], flights['DEST']]).unique()
    airports_to_map = airports[airports['iata_code'].isin(uniques)]

    G = nx.Graph()
    pos = {}

    # Add nodes
    for _, airport in airports_to_map.iterrows():
        code = airport['iata_code']
        G.add_node(code)
        pos[code] = (airport['longitude_deg'], airport['latitude_deg'])

    # Add edges with haversine distance as weight
    seen = set()
    for _, flight in flights.iterrows():
        origin = flight['ORIGIN']
        dest = flight['DEST']
        pair = tuple(sorted([origin, dest]))
        if pair in seen:
            continue
        seen.add(pair)
        if origin in pos and dest in pos:
            dist = haversine(pos[origin], pos[dest])
            G.add_edge(origin, dest, weight=round(dist, 1))

    return G, pos


# ---------------------------------------------------------------------------
# Search Algorithms
# ---------------------------------------------------------------------------

def mybfs(G, source, target):
    """
    BFS from source to target using nx.bfs_edges.
    Stops as soon as target is reached.

    Returns
    -------
    explored_edges : list of (u, v) — every edge visited during the search
    path_edges     : list of (u, v) — edges on the final shortest path
    """
    parent = {source: None}
    explored_edges = []

    for u, v in nx.bfs_edges(G, source):
        explored_edges.append((u, v))
        if v not in parent:
            parent[v] = u
        if v == target:
            break

    if target not in parent:
        return [], []

    # Reconstruct final path
    path_nodes = []
    node = target
    while node is not None:
        path_nodes.append(node)
        node = parent[node]
    path_nodes.reverse()

    path_edges = [(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)]
    return explored_edges, path_edges


def mydfs(G, source, target):
    """
    DFS from source to target using nx.dfs_edges.
    Stops as soon as target is reached.

    Returns
    -------
    explored_edges : list of (u, v) — every edge visited during the search
    path_edges     : list of (u, v) — edges on the final path found
    """
    parent = {source: None}
    explored_edges = []

    for u, v in nx.dfs_edges(G, source):
        explored_edges.append((u, v))
        if v not in parent:
            parent[v] = u
        if v == target:
            break

    if target not in parent:
        return [], []

    # Reconstruct final path
    path_nodes = []
    node = target
    while node is not None:
        path_nodes.append(node)
        node = parent[node]
    path_nodes.reverse()

    path_edges = [(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)]
    return explored_edges, path_edges


def myastar_with_pos(G, source, target, pos):
    """
    A* search using haversine distance as the heuristic.
    nx.astar_path only returns the final path (no explored edges exposed),
    so we return only path_edges with an empty explored list.

    Returns
    -------
    explored_edges : [] — not available from nx.astar_path
    path_edges     : list of (u, v) on the optimal path
    """
    def heuristic(u, v):
        return haversine(pos[u], pos[v])

    try:
        path_nodes = nx.astar_path(G, source, target, heuristic=heuristic, weight='weight')
    except nx.NetworkXNoPath:
        return [], []

    path_edges = [(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)]
    return [], path_edges


def path_distance(G, path_edges):
    """Sum the edge weights (miles) along a list of (u, v) edge tuples."""
    total = 0.0
    for u, v in path_edges:
        total += G[u][v].get('weight', 0)
    return round(total, 1)


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def draw_search(G, pos, explored_edges, path_edges, title, filename, algorithm_label):
    """
    Draw the Alaska Airlines airport graph on a Cartopy map.

    Three-layer coloring:
      - Light blue  : unvisited edges (not explored by the algorithm)
      - Orange      : edges explored/visited during search (BFS/DFS only)
      - Red         : edges on the final path

    Parameters
    ----------
    G               : NetworkX graph
    pos             : dict {code: (lon, lat)}
    explored_edges  : list of (u,v) visited during search (empty for A*)
    path_edges      : list of (u,v) on the final path
    title           : plot title string
    filename        : output file path
    algorithm_label : 'BFS', 'DFS', or 'A*'
    """
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)

    fig = plt.figure(figsize=(18, 12))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor='#f5f5f0')
    ax.add_feature(cfeature.OCEAN, facecolor='#d0e8f5')
    ax.add_feature(cfeature.COASTLINE, linewidth=0.7)
    ax.add_feature(cfeature.BORDERS, linestyle='-', alpha=0.5, linewidth=0.5)
    ax.add_feature(cfeature.STATES, linestyle=':', alpha=0.4, linewidth=0.5)
    ax.set_extent([-180, -50, 15, 75], crs=ccrs.PlateCarree())

    # Build lookup sets (normalise edge direction for undirected matching)
    path_set     = {tuple(sorted(e)) for e in path_edges}
    explored_set = {tuple(sorted(e)) for e in explored_edges}

    # ---- Draw edges in three layers (back to front) ----

    # Layer 1: unvisited edges (light blue)
    for u, v in G.edges():
        key = tuple(sorted([u, v]))
        if key not in explored_set and key not in path_set:
            lon1, lat1 = pos[u]
            lon2, lat2 = pos[v]
            ax.plot([lon1, lon2], [lat1, lat2],
                    color='steelblue', linewidth=0.6, alpha=0.3, zorder=2,
                    transform=ccrs.PlateCarree())

    # Layer 2: explored edges (orange) — BFS/DFS only
    for u, v in explored_edges:
        key = tuple(sorted([u, v]))
        if key not in path_set:
            lon1, lat1 = pos[u]
            lon2, lat2 = pos[v]
            ax.plot([lon1, lon2], [lat1, lat2],
                    color='orange', linewidth=1.4, alpha=0.7, zorder=3,
                    transform=ccrs.PlateCarree())

    # Layer 3: final path edges (red, on top)
    for u, v in path_edges:
        lon1, lat1 = pos[u]
        lon2, lat2 = pos[v]
        ax.plot([lon1, lon2], [lat1, lat2],
                color='red', linewidth=2.8, zorder=5,
                transform=ccrs.PlateCarree())

    # ---- Draw nodes ----
    path_nodes = {n for e in path_edges for n in e}
    explored_nodes = {n for e in explored_edges for n in e}

    for code, (lon, lat) in pos.items():
        if code in path_nodes:
            color, size, z = 'red', 9, 7
        elif code in explored_nodes:
            color, size, z = 'orange', 6, 4
        else:
            color, size, z = '#3a7abf', 4, 2
        ax.plot(lon, lat, 'o', color=color, markersize=size, zorder=z,
                transform=ccrs.PlateCarree())
        ax.text(lon + 0.4, lat + 0.4, code, fontsize=6.5, zorder=8,
                transform=ccrs.PlateCarree(), color='#222222')

    # ---- Legend ----
    legend_handles = [
        mpatches.Patch(color='red',       label=f'{algorithm_label} final path'),
        mpatches.Patch(color='steelblue', alpha=0.4, label='Unvisited routes'),
    ]
    if explored_edges:
        legend_handles.insert(1, mpatches.Patch(color='orange', alpha=0.8,
                                                 label='Explored edges'))
    ax.legend(handles=legend_handles, loc='lower right', fontsize=9)

    # ---- Title ----
    plt.title(title, fontsize=13, fontweight='bold')

    # ---- Footnote with per-hop distances + total ----
    total_dist = path_distance(G, path_edges)

    if path_edges:
        hop_parts = []
        for u, v in path_edges:
            d = round(G[u][v].get('weight', 0))
            hop_parts.append(f"{u} --({d:,} mi)--> {v}")
        hop_str  = '   |   '.join(hop_parts)
        footnote = f"{hop_str}\nTotal distance: {total_dist:,.0f} miles"
    else:
        footnote = "No path found"

    fig.text(0.5, 0.01, footnote,
             ha='center', fontsize=9, fontweight='bold', color='#111111',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow', edgecolor='gray'))

    plt.tight_layout(rect=[0, 0.08, 1, 1])
    plt.savefig(filename, dpi=130, bbox_inches='tight')
    plt.close()
    print(f"Saved: {filename}  (distance: {total_dist:,.0f} mi, "
          f"explored edges: {len(explored_edges)})")


def run_and_visualize(G, pos, source, target, output_dir):
    """
    Run BFS, DFS, and A* between source and target.
    Saves bfs.png, dfs.png, astar.png into output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Route: {source}  →  {target}")
    print(f"{'='*60}")

    # BFS
    bfs_explored, bfs_path = mybfs(G, source, target)
    print(f"BFS  path: {[e[0] for e in bfs_path] + ([bfs_path[-1][1]] if bfs_path else [])}")
    draw_search(G, pos, bfs_explored, bfs_path,
                title=f"BFS: {source} → {target}",
                filename=os.path.join(output_dir, 'bfs.png'),
                algorithm_label='BFS')

    # DFS
    dfs_explored, dfs_path = mydfs(G, source, target)
    print(f"DFS  path: {[e[0] for e in dfs_path] + ([dfs_path[-1][1]] if dfs_path else [])}")
    draw_search(G, pos, dfs_explored, dfs_path,
                title=f"DFS: {source} → {target}",
                filename=os.path.join(output_dir, 'dfs.png'),
                algorithm_label='DFS')

    # A* (no explored edges from nx built-in)
    astar_explored, astar_path = myastar_with_pos(G, source, target, pos)
    print(f"A*   path: {[e[0] for e in astar_path] + ([astar_path[-1][1]] if astar_path else [])}")
    draw_search(G, pos, astar_explored, astar_path,
                title=f"A*: {source} → {target}",
                filename=os.path.join(output_dir, 'astar.png'),
                algorithm_label='A*')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Building graph from airport and flight data...")
    G, pos = build_graph()
    print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")

    # Verify Seattle → Boston connectivity
    print("\nVerifying Seattle (SEA) → Boston (BOS) connectivity...")
    _, test_path = mybfs(G, 'SEA', 'BOS')
    if test_path:
        print(f"  Connected! BFS path: {[e[0] for e in test_path] + [test_path[-1][1]]}")
    else:
        print("  No path found between SEA and BOS.")

    # Assignment routes
    run_and_visualize(G, pos, 'MIA', 'ADK', 'mia_to_adk')
    run_and_visualize(G, pos, 'BNA', 'CVG', 'bna_to_cvg')

    # Reflection Q4: reverse direction
    run_and_visualize(G, pos, 'ADK', 'MIA', 'adk_to_mia')

    # Interactive mode
    print("\n--- Interactive Route Finder ---")
    while True:
        src = input("Enter source airport code (or 'quit'): ").strip().upper()
        if src == 'QUIT':
            break
        dst = input("Enter destination airport code: ").strip().upper()
        if src not in G.nodes or dst not in G.nodes:
            print(f"  Airport not found. Available: {sorted(G.nodes)}")
            continue
        run_and_visualize(G, pos, src, dst, f"{src.lower()}_to_{dst.lower()}")
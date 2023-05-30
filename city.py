import os
import pickle
import networkx as nx
import osmnx as ox
from typing import TypeAlias, List, Tuple, Union
from haversine import haversine, Unit
from buses import BusesGraph, get_buses_graph
from staticmap import StaticMap, Line
from typing import NamedTuple
OsmnxGraph: TypeAlias = nx.MultiDiGraph
CityGraph: TypeAlias = nx.Graph
Coord: TypeAlias = Tuple[float, float]  # (latitude, longitude)
Path: TypeAlias = List[Coord]

class Edge(NamedTuple):
    length: float  # Length of the edge
    speed: float  # Speed at which to traverse this edge
    edge_type: str  # Either "Street" or "Bus"
    time: float  # Time to traverse this edge

class Node(NamedTuple):
    coord: Coord  # Coordinates of the node
    node_type: str  # Either "Intersection" or "Stop"
    
def get_osmnx_graph() -> OsmnxGraph:
    if os.path.exists('graph.pickle'):
        with open('graph.pickle', 'rb') as f:
            G = pickle.load(f)
    else:
        G = ox.graph_from_place('Barcelona, Spain', network_type='walk')
        with open('graph.pickle', 'wb') as f:
            pickle.dump(G, f)
    
    G.graph["crs"] = "EPSG:4326"

    return G

def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    with open(filename, 'wb') as f:
        pickle.dump(g, f)

def load_osmnx_graph(filename: str) -> OsmnxGraph:
    with open(filename, 'rb') as f:
        return pickle.load(f)
def build_city_graph(g1: OsmnxGraph, g2: BusesGraph) -> CityGraph:
    G = nx.MultiDiGraph()  # Use MultiDiGraph instead of Graph

    # Add nodes from the OsmnxGraph
    for node, data in g1.nodes(data=True):
        G.add_node(node, y=data['y'], x=data['x'], node_type='Intersection')

    # Add nodes from the BusesGraph
    for node, data in g2.nodes(data=True):
        G.add_node(node, y=data['y'], x=data['x'], node_type='Stop')

    # Add edges from the OsmnxGraph
    default_speed = 4.5  # set a default speed value

    for u, v, data in g1.edges(data=True):
        length = data.get('length', 0)  # Default length value if 'length' key is missing
        try:
            speed = data['speed']
        except KeyError:
            speed = default_speed
        time = length / speed  # Calculate travel time
        G.add_edge(u, v, Edge(length, speed, 'Street', time))

    # Add edges from the BusesGraph
    for u, v, data in g2.edges(data=True):
        length = data.get('length', 0)  # Default length value if 'length' key is missing
        try:
            speed = data['speed']
            
        except KeyError:
            speed = default_speed
        time = length / speed  # Calculate travel time
        G.add_edge(u, v, Edge(length, speed, 'Bus', time))

    # Add edges between Stops and the nearest Intersections
    for stop_node in G.nodes:
        if G.nodes[stop_node]['node_type'] == 'Stop':
            min_distance = float('inf')
            nearest_intersection = None

            for intersection_node in G.nodes:
                if G.nodes[intersection_node]['node_type'] == 'Intersection':
                    dist = haversine((G.nodes[stop_node]['x'], G.nodes[stop_node]['y']), (G.nodes[intersection_node]['x'], G.nodes[intersection_node]['y']), unit=Unit.METERS)
                    if dist < min_distance:
                        min_distance = dist
                        nearest_intersection = intersection_node

            if nearest_intersection is not None:
                STREET_SPEED = 4.5  # Average walking speed in km/h
                time = min_distance / STREET_SPEED  # Calculate travel time
                G.add_edge(stop_node, nearest_intersection, Edge(min_distance, STREET_SPEED, 'Street', time))

    G.graph["crs"] = "EPSG:4326"
    
    return G


def find_path(ox_g: OsmnxGraph, g: CityGraph, src: Coord, dst: Coord) -> Path:
    # Get the nearest nodes to the source and destination coordinates
    print("src and dst:")
    print(src, dst)
    src_node = ox.distance.nearest_nodes(ox_g, src[0], src[1])
    dst_node = ox.distance.nearest_nodes(ox_g, dst[0], dst[1])
    
    print(src_node, dst_node)
    #print the coordinates of the nodes
    print(g.nodes[src_node]['x'], g.nodes[src_node]['y'])
    print(g.nodes[dst_node]['x'], g.nodes[dst_node]['y'])

    # Find the shortest path from the source to the destination
    try:
        path = nx.shortest_path(g, src_node, dst_node, weight='time')
    except nx.NetworkXNoPath:
        print("Sorry, no path exists between these two locations.")
        return []

    # Convert nodes in path to coordinates
    path_coords = [(g.nodes[node]['y'], g.nodes[node]['x']) for node in path]

    return path_coords

def show(g: CityGraph) -> None:
    # Filter nodes without coordinates
    nodes_with_coordinates = {n: data for n, data in g.nodes(data=True) if 'coord' in data}
    # Create a set of nodes that are referred to by edges
    edge_nodes = set()
    for u, v in g.edges():
        edge_nodes.add(u)
        edge_nodes.add(v)
    # Create a subgraph with nodes containing coordinates and nodes referred to by edges
    subgraph = g.subgraph(nodes_with_coordinates.keys() | edge_nodes)
    # Plot the subgraph
    ox.plot_graph(subgraph)

def plot(g: CityGraph, filename: str) -> None:
    ox.save_graphml(g, filename)

def plot_path(g: CityGraph, p: Path, filename: str) -> None:
    m = StaticMap(800, 800)
    previous_node = p[0]

    for node in p[1:]:
        data = g[previous_node][node]
        m.add_line(Line(((data['lat'], data['lon']), (data['lat'], data['lon'])), 'blue', 3))
        previous_node = node

    image = m.render()
    image.save(filename)
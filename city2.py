import networkx as nx
from networkx.algorithms.shortest_paths.generic import shortest_path

from typing import TypeAlias, Tuple
import osmnx as ox
import pickle
import os
from geopy.distance import geodesic
from buses import BusesGraph, get_buses_graph
from haversine import haversine, Unit
import matplotlib.pyplot as plt
from staticmap import StaticMap, CircleMarker, Line

from typing import List

CityGraph: TypeAlias = nx.Graph
OsmnxGraph: TypeAlias = nx.MultiDiGraph
Coord: TypeAlias = Tuple[float, float]  # (latitude, longitude)

        
        
#TODO: Define Intersection, Stop, Street, Bus and Path as per your requirements

class Edge:
    # Define this class based on your requirements
    pass

def get_osmnx_graph() -> OsmnxGraph:
    filename = 'osmnx_graph.pickle'

    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)

    graph = ox.graph_from_place('Barcelona, Spain', network_type='walk')
    save_osmnx_graph(graph, filename)

    return graph



def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    with open(filename, 'wb') as f:
        pickle.dump(g, f)

def load_osmnx_graph(filename: str) -> OsmnxGraph:
    with open(filename, 'rb') as f:
        return pickle.load(f)

def build_city_graph(g1: OsmnxGraph, g2: BusesGraph) -> CityGraph:
    #print type of g1 and g2
    #g1 is MultiDiGraph
    #g2 is Graph
    #g1_undirected = g1.to_undirected()
    
    #g2_multigraph = nx.MultiGraph(g2)
    g2_undirected = g2.to_undirected()
    #create multigraph from g2_undirected
    g2_multigraph = nx.MultiGraph(g2_undirected)
    # Create a new graph that is the union of g1 and g2
    city_graph = nx.compose(g1, g2_multigraph)
    

    # Connect each stop to the nearest intersection
    i = 0
    #get number of nodes in g2
    num_nodes = g2.number_of_nodes()
    print('num_nodes: ', num_nodes)
    for stop, data in g2.nodes(data=True):
        #data: {'name': 'Pl de Catalunya', 'line': '100', 'x': 41.386255, 'y': 2.169782}
        i += 1
        if i % 500 == 0:
            #print(i)
            
        #yx yx yx
        #xy yx yx
        #yx xy yx
        #xy xy yx
        #yx 
        # x from graph in osmnx is longitude
            #print('datax: ', data['x'])
        # Estimate distance as bird's-eye distance
            nearest_intersection = ox.distance.nearest_nodes(g1, data['x'], data['y'])
            #print('g1 nodes nearest intersection x: ', g1.nodes[nearest_intersection]['x'])
            
            distance = haversine((data['y'], data['x']), (g1.nodes[nearest_intersection]['x'], g1.nodes[nearest_intersection]['y']))
            city_graph.add_edge(stop, nearest_intersection, info=[{data['name'], distance, data['line']}], length=distance)
            city_graph.add_edge(nearest_intersection, stop, info=[{data['name'], distance, data['line']}], length=distance)

    
    print('returned city_graph')
    
    # save city_graph as pickle
    save_osmnx_graph(city_graph, 'city_graph5.pickle')
    
    return city_graph

def get_city_graph() -> CityGraph:
    filename = 'city_graph5.pickle'

    if os.path.exists(filename):
        return load_osmnx_graph(filename)

    osmnx_graph = get_osmnx_graph()
    buses_graph = get_buses_graph()
    city_graph = build_city_graph(osmnx_graph, buses_graph)
    save_osmnx_graph(city_graph, filename)

    return city_graph



def find_path(ox_g: OsmnxGraph, g: CityGraph, dst: Coord, src: Coord) -> List[Coord]:
    # Find nearest nodes to the source and destination coordinates in the original osmnx graph
    dst_nearest = ox.distance.nearest_nodes(ox_g, src[1], src[0])
    src_nearest = ox.distance.nearest_nodes(ox_g, dst[1], dst[0])
    print('src_nearest: ', src_nearest)
    print('dst_nearest: ', dst_nearest)

    # Calculate the shortest path in the city graph
    try: 
        shortest_path_in_city_graph = shortest_path(ox_g, src_nearest, dst_nearest, weight='length')
    except nx.NetworkXNoPath:
        return []
    #list with nodes such as ['102477', '102474', '100770',...]
    
    # Convert the nodes of the shortest path into coordinates
    #path_as_coordinates = [(g.nodes[node]['y'], g.nodes[node]['x']) for node in shortest_path_in_city_graph]
    #@GitHub: alexanderbkl

    return shortest_path_in_city_graph

def show(g: CityGraph) -> None:
    print('showing graph')
    print('drawing graph')
    fig, ax = ox.plot_graph(g, node_size=0.5, edge_linewidth=0.5)

    #nx.draw(g, with_labels=False, node_color='skyblue', node_size=15, edge_color='gray')
    

def plot(g: CityGraph, filename: str) -> None:
    m = StaticMap(800, 800)
    i = 0
    for node in g.nodes:
        if i % 500 == 0:
            print('g nodes node x: ', g.nodes[node]['x'])
        m.add_marker(CircleMarker((g.nodes[node]['x'], g.nodes[node]['y']), 'red', 3))
        
    for edge in g.edges:
        m.add_line(Line([(g.nodes[edge[0]]['x'], g.nodes[edge[0]]['y']), (g.nodes[edge[1]]['x'], g.nodes[edge[1]]['y'])], 'blue', 2))
    
    image = m.render()
    image.save(filename)
    
    


#def plot_path(g: CityGraph, p: Path, filename: str) -> None:
#    #TODO: Implement this function to display the path on the city map
#    pass
if __name__ == '__main__':
    city_graph = get_city_graph()
    
    plot(city_graph, 'city_graph.png')
    
    #show(city_graph)
    
    
    

    #TODO: Use the functions as per your requirements
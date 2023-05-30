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

from typing import List, Union

CityGraph: TypeAlias = nx.Graph
OsmnxGraph: TypeAlias = nx.MultiDiGraph
Coord: TypeAlias = Tuple[float, float]  # (latitude, longitude)
EdgeType: TypeAlias = Union["Intersection", "Stop"]

class Edge:
    def __init__(self, name: str, distance: float, edge_type: EdgeType):
        self.name = name
        self.distance = distance
        self.type = edge_type


class Intersection(Edge):
    def __init__(self, name: str, distance: float):
        super().__init__(name, distance, 'intersection')

class Stop(Edge):
    def __init__(self, name: str, distance: float):
        super().__init__(name, distance, 'stop')



def get_osmnx_graph() -> OsmnxGraph:
    filename = 'osmnx_graph.pickle'

    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)

    graph = ox.graph_from_place("Barcelona", network_type='walk', simplify=True)
    # Iterate over edges to remove geometry and keep the first edge
    for u, nbrsdict in graph.adjacency():
        for v, edgesdict in nbrsdict.items():
            eattr = edgesdict[0]  # First edge attributes
            if 'geometry' in eattr:
                del(eattr['geometry'])

    save_osmnx_graph(graph, filename)
    return graph


def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    # Remove geometry from all edges before saving to a file
    for u, v, key, geom in g.edges(data="geometry", keys=True):
        if geom is not None:
            del(g[u][v][key]["geometry"])

    with open(filename, 'wb') as f:
        pickle.dump(g, f)

def load_osmnx_graph(filename: str) -> OsmnxGraph:
    with open(filename, 'rb') as f:
        return pickle.load(f)

def build_city_graph(g1: OsmnxGraph, g2: BusesGraph) -> CityGraph:
    print('Building city graph...')

    for node in g1.nodes:
        g1.nodes[node]['type'] = 'intersection'
        
    for node in g2.nodes:
        g2.nodes[node]['type'] = 'stop'

    g2_multigraph = g2.to_undirected()
    
    city_graph: CityGraph = nx.compose(g1, g2_multigraph)
    

    # Connect each stop to the nearest intersection
    i = 0
    #get number of nodes in g2
    num_nodes = g2.number_of_nodes()
    print('num_nodes: ', num_nodes)
    for stop, data in g2.nodes(data=True):
        #data: {'name': 'Pl de Catalunya', 'line': '100', 'x': 41.386255, 'y': 2.169782}
        i += 1
        if i % 500 == 0:
            print("test")
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
            city_graph.add_edge(stop, nearest_intersection, info=[Edge(data['name'], distance, data['line'])], length=distance)
            city_graph.add_edge(nearest_intersection, stop, info=[Edge(data['name'], distance, data['line'])], length=distance)

    
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



def find_path(g: CityGraph, ox_g: OsmnxGraph, dst: Coord, src: Coord) -> List[Coord]:
    # Find nearest nodes to the source and destination coordinates in the original osmnx graph
    #print the first node and edge in g
    
    first_node = list(g.nodes(data=True))[0]
    first_edge = list(g.edges(data=True))[0]
    print('first_node: ', first_node)
    print('first_edge: ', first_edge)
    
    dst_nearest = ox.distance.nearest_nodes(g, src[1], src[0])
    src_nearest = ox.distance.nearest_nodes(g, dst[1], dst[0])
    print('src_nearest: ', src_nearest)
    print('dst_nearest: ', dst_nearest)

    # Calculate the shortest path in the city graph
    try: 
        shortest_path_in_city_graph = shortest_path(g, src_nearest, dst_nearest, weight='length')
    except nx.NetworkXNoPath:
        return []
    #list with nodes such as ['102477', '102474', '100770',...]
    
    # Convert the nodes of the shortest path into coordinates
    #path_as_coordinates = [(g.nodes[node]['y'], g.nodes[node]['x']) for node in shortest_path_in_city_graph]
    #@GitHub: alexanderbkl

    return shortest_path_in_city_graph

def show(g: CityGraph) -> None:
    print('showing graph')

    colors = ['green' if data.get('type') == 'street' else 'red' for node, data in g.nodes(data=True)]

    ox.plot_graph(g, node_color=colors, node_size=0.5, edge_linewidth=0.5)

def plot(g: CityGraph, filename: str) -> None:
    print('plotting city graph', filename)
    m = StaticMap(800, 800)
    for node in g.nodes:
        if g.nodes[node]['type'] == 'street':
            m.add_marker(CircleMarker((g.nodes[node]['x'], g.nodes[node]['y']), 'green', 2))
        elif g.nodes[node]['type'] == 'buses':
            m.add_marker(CircleMarker((g.nodes[node]['x'], g.nodes[node]['y']), 'red', 3))
        
    for edge in g.edges:
        edge_type = g.nodes[edge[0]]['type']
        if edge_type == 'street':
            color = 'yellow'
        elif edge_type == 'buses':
            color = 'blue'
        else:
            color = 'black'  # Default color if type is not defined
        
        m.add_line(Line([(g.nodes[edge[0]]['x'], g.nodes[edge[0]]['y']), (g.nodes[edge[1]]['x'], g.nodes[edge[1]]['y'])], color, 1))
    
    image = m.render()
    image.save(filename)
    
    



def plot_path(g: CityGraph, p: List[Coord], filename: str) -> None:
    # Initialize the map
    m = StaticMap(800, 800)

    # Add markers for nodes and lines for edges in the path
    for i in range(len(p) - 1):
        # (longitude, latitude)
        m.add_marker(CircleMarker((p[i][1], p[i][0]), 'red', 3))
        m.add_line(
            Line([(p[i][1], p[i][0]), (p[i + 1][1], p[i + 1][0])], 'blue', 2))

    # Add a marker for the final destination
    # (longitude, latitude)
        


    # Render the image and save it
    try:
        m.add_marker(CircleMarker((p[-1][1], p[-1][0]), 'green', 4))
        image = m.render()
        image.save(filename)
    except IndexError:
        print('No path found')
        return
    except Exception as e:
        #print('Error while plotting path:', e)
        return

#graph = get_city_graph()

#show(graph)
#plot(graph, 'city_graph.png')
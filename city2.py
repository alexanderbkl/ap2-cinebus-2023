import networkx as nx
from networkx.algorithms.shortest_paths.generic import shortest_path

from typing import TypeAlias, Tuple
import osmnx as ox
from osmnx import distance
import pickle
import os
from geopy.distance import geodesic
from buses import BusesGraph, get_buses_graph
from haversine import haversine, Unit
import matplotlib.pyplot as plt
from staticmap import StaticMap, CircleMarker, Line, IconMarker
from PIL import Image, ImageDraw, ImageFont

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
    #g2_multigraph = nx.MultiGraph(g2)
    g2_undirected = g2.to_undirected()
    #create multigraph from g2_undirected
    g2_multigraph = nx.MultiGraph(g2_undirected)
    # Create a new graph that is the union of g1 and g2
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

def get_stop_subgraph(g: CityGraph) -> CityGraph:
    # Get all nodes of type 'stop'
    stop_nodes = [node for node, data in g.nodes(data=True) if data.get('type') == 'stop']
    
    # Create a subgraph from the original graph using only these nodes
    stop_subgraph = g.subgraph(stop_nodes)
    
    return stop_subgraph

def get_intersection_subgraph(g: CityGraph) -> CityGraph:
    # Get all nodes of type 'intersection'
    intersection_nodes = [node for node, data in g.nodes(data=True) if data.get('type') == 'intersection']
    
    # Create a subgraph from the original graph using only these nodes
    intersection_subgraph = g.subgraph(intersection_nodes)
    
    return intersection_subgraph

def find_path(g: CityGraph, dst: Coord, src: Coord) -> List[Coord]:
    # Find nearest nodes to the source and destination coordinates in the original osmnx graph
    #print the first node and edge in g
    buses_graph = get_buses_graph()
    
    dst_nearest = distance.nearest_nodes(buses_graph, src[1], src[0])
    src_nearest = distance.nearest_nodes(buses_graph, dst[1], dst[0])
    

    # Calculate the shortest path in the city graph
    try: 
        shortest_path_in_city_graph = shortest_path(buses_graph, src_nearest, dst_nearest, weight='length')
    except nx.NetworkXNoPath:
        return []
    #list with nodes such as ['102477', '102474', '100770',...]
    
    # Convert the nodes of the shortest path into coordinates
    #path_as_coordinates = [(g.nodes[node]['y'], g.nodes[node]['x']) for node in shortest_path_in_city_graph]
    #@GitHub: alexanderbkl

    return shortest_path_in_city_graph

def show(g: CityGraph) -> None:
    print('showing graph')

    colors = ['green' if data.get('type') == 'intersection' else 'red' for node, data in g.nodes(data=True)]

    ox.plot_graph(g, node_color=colors, node_size=0.5, edge_linewidth=0.5)

def plot(g: CityGraph, filename: str) -> None:
    print('plotting city graph', filename)
    m = StaticMap(800, 800)
    for node in g.nodes:
        if g.nodes[node]['type'] == 'intersection':
            m.add_marker(CircleMarker((g.nodes[node]['y'], g.nodes[node]['x']), 'green', 2))
        elif g.nodes[node]['type'] == 'stop':
            m.add_marker(CircleMarker((g.nodes[node]['y'], g.nodes[node]['x']), 'red', 3))
        
    for edge in g.edges:
        edge_type = g.nodes[edge[0]]['type']
        if edge_type == 'intersection':
            color = 'yellow'
        elif edge_type == 'stop':
            color = 'blue'
        else:
            color = 'black'  # Default color if type is not defined
        
        m.add_line(Line([(g.nodes[edge[0]]['y'], g.nodes[edge[0]]['x']), (g.nodes[edge[1]]['y'], g.nodes[edge[1]]['x'])], color, 1))
    
    image = m.render()
    image.save(filename)
    
    

def create_icon(text: str, font_path: str, font_size: int, filename: str):
    font = ImageFont.truetype(font_path, font_size)
    text_width, text_height = font.getsize(text)
    img = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    d.text((0, 0), text, font=font, fill=(0, 0, 0, 255))
    img.save(filename)

def plot_path(g: CityGraph, p: List[Coord], filename: str) -> None:
    osmnx_g = get_osmnx_graph()
    m = StaticMap(800, 800)
    
    # draw icons
    
    for i in range(len(p)):
        # name of the bus stop line
        line_name = g.nodes[p[i]]['line']
        icon_path = f"./icons/{line_name}.png"
        # create icon if it doesn't exist
        if not os.path.exists(icon_path):
            create_icon(line_name, "./fonts/Roboto-Black.ttf", 20, icon_path)
        # calculate offsets, assuming that the average size of an icon is 20x20
        offset_x = -10 # half the width
        offset_y = -10 # half the height

        m.add_marker(IconMarker((g.nodes[p[i]]['x'], g.nodes[p[i]]['y']), icon_path, offset_x, offset_y))


    #draw lines and markers between bus stops
    for i in range(len(p) - 1):
        #add bus red marker
        m.add_marker(CircleMarker((g.nodes[p[i]]['x'], g.nodes[p[i]]['y']), 'red', 10))

        src_nearest = distance.nearest_nodes(osmnx_g, g.nodes[p[i]]['x'], g.nodes[p[i]]['y'])
        dst_nearest = distance.nearest_nodes(osmnx_g, g.nodes[p[i+1]]['x'], g.nodes[p[i+1]]['y'])

        shortest_path_osmnx = shortest_path(osmnx_g, src_nearest, dst_nearest, weight='length')
        path_as_coordinates_osmnx = [(osmnx_g.nodes[node]['x'], osmnx_g.nodes[node]['y']) for node in shortest_path_osmnx]
        m.add_line(Line(path_as_coordinates_osmnx, 'black', 5))

    try:
        m.add_marker(CircleMarker((g.nodes[p[-1]]['x'], g.nodes[p[-1]]['y']), 'green', 10))
        image = m.render()
        image.save(filename)
    except IndexError:
        print('No path found')
        return
    except Exception as e:
        print('Error while plotting path:', e)
        return

#graph = get_city_graph()

#stop_subgraph = get_stop_subgraph(graph)
#osmng_g = get_osmnx_graph()
#show(osmng_g)
#plot(graph, 'city_graph.png')
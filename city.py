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

# Definitions of custom types for ease of understanding and readability
CityGraph: TypeAlias = nx.Graph
OsmnxGraph: TypeAlias = nx.MultiDiGraph
Coord: TypeAlias = Tuple[float, float]  # (latitude, longitude)
EdgeType: TypeAlias = Union["Intersection", "Stop"]

# Global variable representing travel time
travel_time = ''


class Edge:
    """Class representing an Edge in the graph with associated metadata."""

    def __init__(self, name: str, distance: float, edge_type: EdgeType):
        """Initializes an Edge object with its name, distance, and type."""
        self.name = name
        self.distance = distance
        self.type = edge_type


class Intersection(Edge):
    """Class representing an intersection in the city graph. Inherits from Edge."""

    def __init__(self, name: str, distance: float):
        """Initializes an Intersection object."""
        super().__init__(name, distance, 'intersection')


class Stop(Edge):
    """Class representing a bus stop in the city graph. Inherits from Edge."""

    def __init__(self, name: str, distance: float):
        """Initializes a Stop object."""
        super().__init__(name, distance, 'stop')


class Path:
    """Class representing a Path between edges in the graph."""

    def __init__(self, x, y, node, type):
        """Initializes a Path object."""
        if type == 'intersection':
            self.x = x
            self.y = y
            self.type = type
        else:
            self.node = node
            self.type = type


def get_osmnx_graph() -> OsmnxGraph:
    """Fetches or builds and returns an OSMNX graph for Barcelona."""

    # The filename where the graph is or will be stored
    filename = 'barcelona.grf'

    # If the graph has already been created and saved, load it from the file
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)

    # If the graph hasn't been created yet, build it
    graph = ox.graph_from_place(
        "Barcelona", network_type='walk', simplify=True)

    # Remove the 'geometry' attribute from all edges
    for u, nbrsdict in graph.adjacency():
        for v, edgesdict in nbrsdict.items():
            eattr = edgesdict[0]  # First edge attributes
            if 'geometry' in eattr:
                del (eattr['geometry'])

    # Save the graph to a file for future use
    save_osmnx_graph(graph, filename)
    return graph


def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    """Saves an OSMNX graph to a file after removing the 'geometry' attribute from all edges."""

    for u, v, key, geom in g.edges(data="geometry", keys=True):
        if geom is not None:
            del (g[u][v][key]["geometry"])

    with open(filename, 'wb') as f:
        pickle.dump(g, f)


def load_osmnx_graph(filename: str) -> OsmnxGraph:
    """Loads an OSMNX graph from a file."""

    with open(filename, 'rb') as f:
        return pickle.load(f)


def build_city_graph(g1: OsmnxGraph, g2: BusesGraph) -> CityGraph:
    """Builds and returns a city graph that combines an OSMNX graph and a buses graph."""

    print('Building city graph...')

    # Define the type of all nodes in the OSMNX graph as 'intersection'
    for node in g1.nodes:
        g1.nodes[node]['type'] = 'intersection'

    # Define the type of all nodes in the buses graph as 'stop'
    for node in g2.nodes:
        g2.nodes[node]['type'] = 'stop'

    # Convert the buses graph to undirected
    g2_undirected = g2.to_undirected()

    # Convert the undirected buses graph to multigraph
    g2_multigraph = nx.MultiGraph(g2_undirected)

    # Combine the OSMNX graph and the multigraph to create the city graph
    city_graph: CityGraph = nx.compose(g1, g2_multigraph)

    print('returned city_graph')

    # Save the city graph as a pickle
    save_osmnx_graph(city_graph, 'city_graph.grf')

    return city_graph


def get_city_graph() -> CityGraph:
    """Load a city graph from a file, or generate it if it doesn't exist.

    Returns:
        CityGraph: The city graph, loaded from a file or newly generated.
    """
    filename = 'city_graph.grf'

    if os.path.exists(filename):
        return load_osmnx_graph(filename)

    osmnx_graph = get_osmnx_graph()
    buses_graph = get_buses_graph()
    city_graph = build_city_graph(osmnx_graph, buses_graph)
    save_osmnx_graph(city_graph, filename)

    return city_graph


def get_stop_subgraph(g: CityGraph) -> CityGraph:
    """Extracts a subgraph from the city graph containing only bus stops.

    Args:
        g (CityGraph): The city graph.

    Returns:
        CityGraph: A subgraph containing only bus stops.
    """
    stop_nodes = [node for node, data in g.nodes(
        data=True) if data.get('type') == 'stop']
    stop_subgraph = g.subgraph(stop_nodes)

    return stop_subgraph


def get_intersection_subgraph(g: CityGraph) -> CityGraph:
    """Extracts a subgraph from the city graph containing only intersections.

    Args:
        g (CityGraph): The city graph.

    Returns:
        CityGraph: A subgraph containing only intersections.
    """
    intersection_nodes = [node for node, data in g.nodes(
        data=True) if data.get('type') == 'intersection']
    intersection_subgraph = g.subgraph(intersection_nodes)

    return intersection_subgraph


def find_path(g: CityGraph, src: Coord, dst: Coord) -> List[Path]:
    """Calculates the shortest path between two coordinates in the city graph.

    Args:
        g (CityGraph): The city graph.
        src (Coord): The source coordinates (latitude, longitude).
        dst (Coord): The destination coordinates (latitude, longitude).

    Returns:
        List[Path]: The shortest path as a list of paths.
    """
    buses_graph = get_buses_graph()
    dst_nearest = distance.nearest_nodes(buses_graph, dst[1], dst[0])
    src_nearest = distance.nearest_nodes(buses_graph, src[1], src[0])

    try:
        shortest_path_nodes: List = shortest_path(
            buses_graph, src_nearest, dst_nearest, weight='length')
        shortest_path_list: List[Path] = [Path(
            buses_graph.nodes[node]['x'], buses_graph.nodes[node]['y'], node, 'stop') for node in shortest_path_nodes]
        shortest_path_list.insert(0, Path(src[1], src[0], 0, 'intersection'))
        shortest_path_list.append(Path(dst[1], dst[0], 0, 'intersection'))

    except nx.NetworkXNoPath:
        return []

    return shortest_path_list


def show(g: CityGraph) -> None:
    """Displays the city graph using color-coded nodes for intersections and stops.

    Args:
        g (CityGraph): The city graph.
    """
    print('showing graph')
    colors = ['green' if data.get(
        'type') == 'intersection' else 'red' for node, data in g.nodes(data=True)]
    ox.plot_graph(g, node_color=colors, node_size=0.5, edge_linewidth=0.5)


def plot(g: CityGraph, filename: str) -> None:
    """Plots and saves the city graph as an image.

    Args:
        g (CityGraph): The city graph.
        filename (str): The path to the file where the image will be saved.
    """
    print('plotting city graph', filename)
    m = StaticMap(800, 800)
    for node in g.nodes:
        if g.nodes[node]['type'] == 'intersection':
            m.add_marker(CircleMarker(
                (g.nodes[node]['y'], g.nodes[node]['x']), 'green', 2))
        elif g.nodes[node]['type'] == 'stop':
            m.add_marker(CircleMarker(
                (g.nodes[node]['y'], g.nodes[node]['x']), 'red', 3))

    for edge in g.edges:
        edge_type = g.nodes[edge[0]]['type']
        if edge_type == 'intersection':
            color = 'yellow'
        elif edge_type == 'stop':
            color = 'blue'
        else:
            color = 'black'  # Default color if type is not defined

        m.add_line(Line([(g.nodes[edge[0]]['y'], g.nodes[edge[0]]['x']),
                   (g.nodes[edge[1]]['y'], g.nodes[edge[1]]['x'])], color, 1))

    image = m.render()
    image.save(filename)


def create_icon(text: str, font_path: str, font_size: int, filename: str):
    """Creates an image file with a specified text and saves it to the file.

    Args:
        text (str): The text to render into the image.
        font_path (str): The path to the .ttf font file.
        font_size (int): The size of the font to use.
        filename (str): The path to the file where the image will be saved.
    """

    font = ImageFont.truetype(font_path, font_size)
    text_width, text_height = font.getsize(text)
    img = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    d.text((0, 0), text, font=font, fill=(69, 69, 7, 255))
    img.save(filename)


# Method for calculating the travel time
def calculate_travel_time(distance_in_km, speed_in_km_h):
    """Calculates the travel time given a distance and a speed.

    Args:
        distance_in_km: The distance in kilometers.
        speed_in_km_h: The speed in kilometers per hour.

    Returns:
        float: The travel time in minutes.
    """
    time_in_hours = distance_in_km / speed_in_km_h
    time_in_minutes = time_in_hours * 60
    return time_in_minutes


def format_minutes(minutes: float) -> str:
    """Formats the time in minutes into hours and minutes.

    Args:
        minutes (float): The time in minutes.

    Returns:
        str: The formatted time string in the format 'hh:mm'.
    """
    hours, mins = divmod(int(minutes), 60)
    return f"{hours:02d}:{mins:02d}"


def plot_path(g: CityGraph, p: List[Path], filename: str) -> str:
    """Plots the path on the city graph and saves the image to a file.

    Args:
        g (CityGraph): The city graph.
        p (List[Path]): The list of paths.
        filename (str): The path to the file where the image will be saved.

    Returns:
        str: The total travel time in the format 'hh:mm'.
    """
    osmnx_g = get_osmnx_graph()
    m = StaticMap(800, 800)

    bus_speed = 20  # km/h
    walking_speed = 5  # km/h

    stop_paths = []
    intersection_paths = []

    # Separate the paths into their respective lists
    for path in p:
        if path.type == 'stop':
            stop_paths.append(path)
        elif path.type == 'intersection':
            intersection_paths.append(path)

    # Draw line from start point to first bus stop
    src_nearest = distance.nearest_nodes(
        osmnx_g, intersection_paths[0].x, intersection_paths[0].y)
    dst_nearest = distance.nearest_nodes(
        osmnx_g, g.nodes[stop_paths[0].node]['x'], g.nodes[stop_paths[0].node]['y'])
    shortest_path_osmnx_start = shortest_path(
        osmnx_g, src_nearest, dst_nearest, weight='length')
    path_as_coordinates_osmnx_start = [
        (osmnx_g.nodes[node]['x'], osmnx_g.nodes[node]['y']) for node in shortest_path_osmnx_start]
    m.add_line(Line(path_as_coordinates_osmnx_start, 'blue', 10))
    # add marker to the start point (paths_as_coordinates_osmnx_start[0])
    m.add_marker(CircleMarker(
        (path_as_coordinates_osmnx_start[0][0], path_as_coordinates_osmnx_start[0][1]), 'green', 15))

    # intersections:  [<city2.Path object at 0x000001D2AAC2E590>, <city2.Path object at 0x000001D2AAC2F160>]
    # Draw icons for each stop in the path
    for i in range(len(stop_paths)):
        # name of the bus stop line
        line_name = g.nodes[stop_paths[i].node]['line']
        icon_path = f"./icons/{line_name}.png"
        # create icon if it doesn't exist
        if not os.path.exists(icon_path):
            create_icon(line_name, "./fonts/Roboto-Black.ttf", 20, icon_path)
        # calculate offsets, assuming that the average size of an icon is 20x20
        offset_x = -10  # half the width
        offset_y = -10  # half the height

        m.add_marker(IconMarker(
            (g.nodes[stop_paths[i].node]['x'], g.nodes[stop_paths[i].node]['y']), icon_path, offset_x, offset_y))

    # g nodes {'name': 'Gran Via Corts Catalanes, 1132-1142', 'line': 'N2', 'y': 41.417631, 'x': 2.206185, 'type': 'stop'}
    # Draw lines and markers between bus stops

    current_line: str
    next_line: str
    last_bus_node: int = stop_paths[-1].node
    total_time = 0
    for i in range(len(stop_paths) - 1):
        # add bus red marker
        current_bus_node = stop_paths[i].node
        next_bus_node = stop_paths[i+1].node

        current_line = g.nodes[current_bus_node]['line']
        next_line = g.nodes[next_bus_node]['line']

        coord1 = (g.nodes[current_bus_node]['x'],
                  g.nodes[current_bus_node]['y'])
        coord2 = (g.nodes[next_bus_node]['x'], g.nodes[next_bus_node]['y'])
        distance_in_km = haversine(coord1, coord2)

        src_nearest = distance.nearest_nodes(
            osmnx_g, g.nodes[current_bus_node]['x'], g.nodes[current_bus_node]['y'])
        dst_nearest = distance.nearest_nodes(
            osmnx_g, g.nodes[next_bus_node]['x'], g.nodes[next_bus_node]['y'])

        shortest_path_osmnx: (list | dict) = shortest_path(
            osmnx_g, src_nearest, dst_nearest, weight='length')

        path_as_coordinates_osmnx = [
            (osmnx_g.nodes[node]['x'], osmnx_g.nodes[node]['y']) for node in shortest_path_osmnx]

        # if current line and next line is different, print walking. if not, print bus
        if current_line != next_line:
            # walking
            walking_time = calculate_travel_time(distance_in_km, walking_speed)
            # add walking blue line
            m.add_line(Line(path_as_coordinates_osmnx, 'blue', 10))
            # sum time by walking
            total_time += walking_time

        else:
            # bus
            bus_time = calculate_travel_time(distance_in_km, bus_speed)
            # add bus red line
            m.add_line(Line(path_as_coordinates_osmnx, 'red', 10))
            # sum time by bus
            total_time += bus_time
        m.add_marker(CircleMarker(
            (g.nodes[current_bus_node]['x'], g.nodes[current_bus_node]['y']), 'black', 15))

    # Draw line from last bus stop to end point

    src_nearest = distance.nearest_nodes(
        osmnx_g, g.nodes[stop_paths[-1].node]['x'], g.nodes[stop_paths[-1].node]['y'])
    dst_nearest = distance.nearest_nodes(
        osmnx_g, intersection_paths[-1].x, intersection_paths[-1].y)
    shortest_path_osmnx_end = shortest_path(
        osmnx_g, src_nearest, dst_nearest, weight='length')
    path_as_coordinates_osmnx_end = [
        (osmnx_g.nodes[node]['x'], osmnx_g.nodes[node]['y']) for node in shortest_path_osmnx_end]
    m.add_line(Line(path_as_coordinates_osmnx_end, 'blue', 10))
    # Calculate total time and draw the path from the last bus stop to the end point
    travel_time = format_minutes(total_time)

    # Save the final image and return the total travel time
    try:

        m.add_marker(CircleMarker(
            (g.nodes[last_bus_node]['x'], g.nodes[last_bus_node]['y']), 'green', 15))
        image = m.render()
        image.save(filename)
    except IndexError:
        print('No path found')
        return
    except Exception as e:
        print('Error while plotting path:', e)
        return
    return travel_time

# Following is for testing purposes, commented out
# graph = get_city_graph()
# stop_subgraph = get_stop_subgraph(graph)
# osmng_g = get_osmnx_graph()
# show(osmng_g)
# plot(graph, 'city_graph.png')

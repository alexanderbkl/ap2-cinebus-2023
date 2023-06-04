import networkx as nx
import matplotlib.pyplot as plt
from typing import TypeAlias
import requests
from staticmap import StaticMap, CircleMarker, Line
import geopandas as gpd

from shapely.geometry import Point, LineString
from geopy.distance import geodesic

# Typing alias for a NetworkX Graph
BusesGraph: TypeAlias = nx.Graph


class Bus:
    """Represent a Bus object with specific attributes."""

    def __init__(self, id, name, line):
        """Initialize a new Bus object.

        Args:
            id (int): The bus's unique identifier.
            name (str): The name of the bus.
            line (str): The line that the bus travels on.
        """
        self.id = id
        self.name = name
        self.line = line


def get_buses_graph() -> BusesGraph:
    """Create a graph of bus stops from a given data source.

    This function retrieves data from an online source, filters out relevant information, 
    and constructs a graph where nodes represent bus stops and edges represent paths 
    between consecutive stops.

    Returns:
        BusesGraph: A graph object representing the bus network.
    """

    print("Creating buses graph...")

    # The URL from where the bus data is to be fetched
    url = "https://www.ambmobilitat.cat/OpenData/ObtenirDadesAMB.json"
    response = requests.get(url)
    data = response.json()

    # Initialize an empty graph
    graph = BusesGraph()

    # Parse through each line data fetched
    for line in data['ObtenirDadesAMBResult']['Linies']['Linia']:
        # Filter bus transport
        if line['MitjaTransport'] == "Bus":
            stops = line['Parades']['Parada']
            # Filter Barcelona's bus stops
            stops = [stop for stop in stops if stop['Municipi'] == "Barcelona"]
            for stop in stops:
                # Add bus stop as a node to the graph
                bus = Bus(stop['CodAMB'], stop['Adreca'], line['Nom'])
                graph.add_node(bus.id, name=bus.name, line=bus.line,
                               y=stop['UTM_X'], x=stop['UTM_Y'])
            for i in range(len(stops) - 1):
                # Calculate geodesic distance between each consecutive bus stop
                coord1 = (stops[i]['UTM_X'], stops[i]['UTM_Y'])
                coord2 = (stops[i + 1]['UTM_X'], stops[i + 1]['UTM_Y'])
                distance = geodesic(coord1, coord2).meters

                # Add the edge with distance between the bus stops to the graph
                graph.add_edge(stops[i]['CodAMB'], stops[i + 1]
                               ['CodAMB'], distance=distance)

    graph.graph["crs"] = "EPSG:4326"
    print("Buses graph created!")

    return graph


def show(g: BusesGraph) -> None:
    """Show the constructed bus graph using matplotlib.

    This function converts the graph's nodes and edges to GeoPandas GeoDataFrames, 
    and then visualizes them using a matplotlib plot.

    Args:
        g (BusesGraph): The bus graph to be visualized.
    """
    print("showing...")

    # Convert nodes and edges to GeoPandas GeoDataFrames
    nodes_gdf = gpd.GeoDataFrame([attr for node, attr in g.nodes(data=True)],
                                 geometry=gpd.points_from_xy(
        [attr['x'] for node, attr in g.nodes(data=True)],
        [attr['y'] for node, attr in g.nodes(data=True)]))
    edges_gdf = gpd.GeoDataFrame([attr for node1, node2, attr in g.edges(data=True)],
                                 geometry=[LineString([Point(
                                     g.nodes[node1]['x'], g.nodes[node1]['y']),
                                     Point(g.nodes[node2]['x'], g.nodes[node2]['y'])])
        for node1, node2 in g.edges()])

    # Plot nodes and edges
    fig, ax = plt.subplots(figsize=(15, 15))
    edges_gdf.plot(ax=ax, linewidth=1, edgecolor='#BC8F8F')
    nodes_gdf.plot(ax=ax, markersize=20, color='blue')
    plt.show()


def plot(g: BusesGraph, file_name: str) -> None:
    """Visualize the constructed bus graph and save it as a static map image.

    Args:
        g (BusesGraph): The bus graph to be visualized.
        file_name (str): The name of the image file to save.
    """
    print("Plotting buses graph...")
    m = StaticMap(800, 800)

    # Iterate over each node in the graph
    for node in g.nodes(data=True):
        # Each node is a tuple where the first element is the node ID
        # and the second element is a dictionary of node attributes.
        # Example: (72, {'name': 'Pl de Catalunya', 'line': '100', 'x': 41.386255, 'y': 2.169782})
        try:
            # Create a marker for the node and add it to the map
            marker = CircleMarker((node[1]['x'], node[1]['y']), 'red', 5)
            m.add_marker(marker)
        except:
            print("Error plotting node: ", node)

    # Iterate over each edge in the graph
    for edge in g.edges():
        # Each edge is a tuple where the first and second elements are the node IDs of the connected nodes.
        # Example: (72, 72), (73, 73), (72, 72), (73, 73), (74, 74), (76, 76), (79, 79), ...
        # Create a line for the edge and add it to the map
        line = Line(((g.nodes[edge[0]]['x'], g.nodes[edge[0]]['y']),
                    (g.nodes[edge[1]]['x'], g.nodes[edge[1]]['y'])), 'blue', 1)
        m.add_line(line)

    # Render the map and save it as an image
    image = m.render()
    image.save(file_name)
    print("Buses graph plotted!", file_name)


# The following lines of code are commented out. They are used for testing purposes.
# Uncomment them to generate and visualize a bus graph.

# graph = get_buses_graph()  # Generate a graph of bus stops

# show(graph)  # Visualize the bus graph

# plot(graph, 'buses.png')  # Save the bus graph as a static map image

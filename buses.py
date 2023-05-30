import networkx as nx
import matplotlib.pyplot as plt
from typing import TypeAlias
import requests
from staticmap import StaticMap, CircleMarker, Line
import geopandas as gpd

from shapely.geometry import Point, LineString
from geopy.distance import geodesic

BusesGraph: TypeAlias = nx.Graph

class Bus:
    def __init__(self, id, name, line):
        self.id = id
        self.name = name
        self.line = line


def get_buses_graph() -> BusesGraph:
    print("Creating buses graph...")
    url = "https://www.ambmobilitat.cat/OpenData/ObtenirDadesAMB.json"
    response = requests.get(url)
    data = response.json()

    graph = BusesGraph()
    
    for line in data['ObtenirDadesAMBResult']['Linies']['Linia']:
        #check if MitjaTransport in line is "Bus"
        if line['MitjaTransport'] == "Bus":
            stops = line['Parades']['Parada']
            # filter the stops to only those in Barcelona
            stops = [stop for stop in stops if stop['Municipi'] == "Barcelona"]
            for stop in stops:
                #check if Municipi in stop is "Barcelona"
                if stop['Municipi'] == "Barcelona":
                
                    bus = Bus(stop['CodAMB'], stop['Adreca'], line['Nom'])
                    graph.add_node(bus.id, name=bus.name, line=bus.line, y=stop['UTM_X'], x=stop['UTM_Y'])
            for i in range(len(stops) - 1):
                # Get the coordinates of the two stops
                coord1 = (stops[i]['UTM_X'], stops[i]['UTM_Y'])
                coord2 = (stops[i + 1]['UTM_X'], stops[i + 1]['UTM_Y'])

                # Calculate the geodesic distance between the two stops
                distance = geodesic(coord1, coord2).meters  # distance in meters
    
                
                # Add an edge between the stops, with the distance as an attribute
                graph.add_edge(stops[i]['CodAMB'], stops[i + 1]['CodAMB'], distance=distance)
                    




    #gdf_edges = gpd.GeoDataFrame(edge_data, geometry=lines, crs='EPSG:4326')  # Set the CRS directly here

    # Convert GeoDataFrames back to an nx.Graph
    #G = nx.from_pandas_edgelist(gdf_edges, source='source', target='target', edge_attr=True, create_using=nx.Graph())
    #nx.set_node_attributes(G, node_data)
    graph.graph["crs"] = "EPSG:4326"
    print("Buses graph created!")

    return graph





def show(g: BusesGraph) -> None:
    print("showing...")
    # Convert nodes and edges to GeoPandas GeoDataFrames
    nodes_gdf = gpd.GeoDataFrame([attr for node, attr in g.nodes(data=True)], geometry=gpd.points_from_xy([attr['x'] for node, attr in g.nodes(data=True)], [attr['y'] for node, attr in g.nodes(data=True)]))
    edges_gdf = gpd.GeoDataFrame([attr for node1, node2, attr in g.edges(data=True)], geometry=[LineString([Point(g.nodes[node1]['x'], g.nodes[node1]['y']), Point(g.nodes[node2]['x'], g.nodes[node2]['y'])]) for node1, node2 in g.edges()])

    # Plot nodes and edges
    fig, ax = plt.subplots(figsize=(15,15))
    edges_gdf.plot(ax=ax, linewidth=1, edgecolor='#BC8F8F')
    nodes_gdf.plot(ax=ax, markersize=20, color='blue')
    plt.show()
def plot(g: BusesGraph, file_name: str) -> None:
    print("Plotting buses graph...")
    m = StaticMap(800, 800)

    for node in g.nodes(data=True):
        
        #node: (72, {'name': 'Pl de Catalunya', 'line': '100', 'x': 41.386255, 'y': 2.169782})
        try:
            marker = CircleMarker((node[1]['x'], node[1]['y']), 'red', 5)
            m.add_marker(marker)
        except:
            print("Error plotting node: ", node)
        #@GitHub: alexanderbkl



    for edge in g.edges():
        #edge:
        #(72, 72)
        #(73, 73)
        #(72, 72)
        #(73, 73)
        #(74, 74)
        #(76, 76)
        #(79, 79)
        #...
        line = Line(((g.nodes[edge[0]]['x'], g.nodes[edge[0]]['y']), (g.nodes[edge[1]]['x'], g.nodes[edge[1]]['y'])), 'blue', 1)
        m.add_line(line)

    image = m.render()
    image.save(file_name)
    print("Buses graph plotted!", file_name)
    

#graph = get_buses_graph()

#show(graph)

#plot(graph, 'buses.png')
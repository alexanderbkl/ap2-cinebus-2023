import networkx as nx
import matplotlib.pyplot as plt
from typing import TypeAlias
import requests
from staticmap import StaticMap, CircleMarker, Line
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

BusesGraph: TypeAlias = nx.Graph

class Bus:
    def __init__(self, id, name, line):
        self.id = id
        self.name = name
        self.line = line


def get_buses_graph() -> BusesGraph:
    url = "https://www.ambmobilitat.cat/OpenData/ObtenirDadesAMB.json"
    response = requests.get(url)
    data = response.json()

    graph = BusesGraph()
    
    for line in data['ObtenirDadesAMBResult']['Linies']['Linia']:
        for stop in line['Parades']['Parada']:
            bus = Bus(stop['CodAMB'], stop['Adreca'], line['Nom'])
            graph.add_node(bus.id, name=bus.name, line=bus.line, y=stop['UTM_X'], x=stop['UTM_Y'])

        stops = line['Parades']['Parada']
        for i in range(len(stops) - 1):
            graph.add_edge(stops[i]['CodAMB'], stops[i + 1]['CodAMB'])




    #gdf_edges = gpd.GeoDataFrame(edge_data, geometry=lines, crs='EPSG:4326')  # Set the CRS directly here

    # Convert GeoDataFrames back to an nx.Graph
    #G = nx.from_pandas_edgelist(gdf_edges, source='source', target='target', edge_attr=True, create_using=nx.Graph())
    #nx.set_node_attributes(G, node_data)
    graph.graph["crs"] = "EPSG:4326"

    return graph





def show(g: BusesGraph) -> None:
    plt.figure(figsize=(15,15))
    nx.draw(g, with_labels=True, node_color='skyblue', node_size=15, edge_color='gray')
    plt.show()

def plot(g: BusesGraph, file_name: str) -> None:
    m = StaticMap(800, 800)

    for node in g.nodes(data=True):
        #node: (72, {'name': 'Pl de Catalunya', 'line': '100', 'x': 41.386255, 'y': 2.169782})
        marker = CircleMarker((node[1]['y'], node[1]['x']), 'red', 5)
        m.add_marker(marker)
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
        line = Line(((g.nodes[edge[0]]['y'], g.nodes[edge[0]]['x']), (g.nodes[edge[1]]['y'], g.nodes[edge[1]]['x'])), 'blue', 1)
        m.add_line(line)

    image = m.render()
    image.save(file_name)
    

#graph = get_buses_graph()

#show(graph)

#plot(graph, 'buses.png')
import osmnx as ox
import networkx as nx
import folium

place_name = "Montigala, Badalona, Spain"
graph = ox.graph_from_place(place_name, network_type="drive")

ox.plot_graph_folium(graph, popup_attribute='name',
                     color='red', weight=2, opacity=0.7)


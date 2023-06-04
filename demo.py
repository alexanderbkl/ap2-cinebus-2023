from datetime import datetime
from staticmap import StaticMap, CircleMarker, Line
import billboard
import buses
import city
from haversine import haversine, Unit
from typing import List
import datetime
import osmnx as ox


def create_billboard():
    """Create a billboard with cinema and film data

    Returns:
        Billboard: A Billboard object with loaded cinema and film data.
    """
    return billboard.read()


def search_billboard(billboard, keyword):
    """Searches the billboard for films containing the provided keyword.

    Args:
        billboard (Billboard): The billboard to search.
        keyword (str): The keyword to search for.

    Returns:
        list: A list of matching Projection objects.
    """
    matching_projections = []
    for projection in billboard.projections:
        if keyword.lower() in projection.film.title.lower():
            matching_projections.append(projection)
            print('----------------------------------------')
            print('Matching projection:')
            print("Títol: "+projection.film.title)
            print("Cinema: " + projection.cinema.name)
            print("Hora: "+str(projection.time[0])+":"+str(projection.time[1]))
            print('----------------------------------------')

    return matching_projections


def create_city_graph():
    """Create a graph representation of the city.

    Returns:
        Graph: A Graph object representing the city.
    """
    return city.get_city_graph()


def find_path_to_cinema(city_graph, start_location, cinema_location):
    """Find the shortest path in the city graph from the start location to the cinema location.

    Args:
        city_graph (Graph): The city graph.
        start_location (tuple): The starting location.
        cinema_location (tuple): The cinema location.

    Returns:
        list: A list of nodes representing the shortest path.
    """
    return city.find_path(city_graph, start_location, cinema_location)


def plot_path(city_graph, path, filename):
    """Plot the path on the city graph and save it as an image.

    Args:
        city_graph (Graph): The city graph.
        path (list): The path to plot.
        filename (str): The name of the file to save the plot to.
    """
    return city.plot_path(city_graph, path, filename)


def Path(node, type):
    """Create a Path object.

    Args:
        node (Node): The node in the path.
        type (str): The type of path.

    Returns:
        Path: A Path object.
    """
    return city.Path(node, type)


def get_lat_long(address):
    """Get the latitude and longitude for a given address.

    Args:
        address (str): The address to geocode.

    Returns:
        tuple: The latitude and longitude of the address, or (None, None) if the address could not be geocoded.
    """
    try:
        result = ox.geocode(address)
        if isinstance(result, tuple):
            latitude = result[0]
            longitude = result[1]
        else:
            latitude = result.y
            longitude = result.x
        return latitude, longitude
    except ox.errors.GeocoderQueryError:
        print(
            f"Unable to geocode the address '{address}'. Please enter a different address.")
        return None, None
    except Exception as e:
        # Handle any other exceptions that may occur during geocoding
        print(f"Error geocoding address '{address}': {e}")
        return None, None


def main():
    """Main function of the script. Handles user input and calls other functions to search the billboard, create the city graph, find the shortest path to the cinema, and plot the path."""
    print("Author: David T.T.")
    billboard = create_billboard()

    print("Showing billboard...")
    billboard.print_billboard()

    keyword = input('Enter keyword to search in billboard: ')
    matching_projections = search_billboard(billboard, keyword)
    print('Matching projections:')
    for projection in matching_projections:
        # print formatted projection film title and cinema name
        print(projection.film.title + ' - ' + projection.cinema.name)

    # bus_graph = buses.get_buses_graph()
    # print("Showing bus graph...")
    # buses.show(bus_graph)
    # print("Saving bus image plot...")
    # buses.plot(bus_graph, "test.png")

    # show CityGraph:
    city_graph = create_city_graph()
    # print("Showing city graph...")
    # city2.show(city_graph)

    address = input(
        'Introduïr adreça (Ex: Av. Diagonal, 250, Barcelona): ')
    start_location = None

    while start_location is None:
        start_location = get_lat_long(address)
        if start_location is None:
            address = input(
                'No s\'ha trobat l\'adreça, intruduïr una altra: ')
    # start_location = (41.377490, 2.205378)

    # finding the cinema with the earliest projection
    matching_projections.sort(key=lambda p: p.time)
    try:
        cinema_location = (
            matching_projections[0].cinema.address.latitude, matching_projections[0].cinema.address.longitude)
    except IndexError:
        print('No matching projections found')
        return
    path: List[Path] = find_path_to_cinema(
        city_graph, start_location, cinema_location)

    projection_time = matching_projections[0].time

    # Variable to keep track of the current line
    current_line = ''

    # Iterate over the nodes in the path
    for i in path:
        if i.type != 'intersection':
            # Check first if name and line exist in the node (g.nodes[node]['name'] and g.nodes[node]['line']])
            if 'name' in city_graph.nodes[i.node] and 'line' in city_graph.nodes[i.node]:
                new_line = city_graph.nodes[i.node]['line']
                # If this line is different from the previous one, print it along with the street
                if new_line != current_line:
                    print(
                        f'Línia TMB: {new_line} Carrer: {city_graph.nodes[i.node]["name"]}')
                    current_line = new_line

    # Convert projection_time to 'hh:mm' format and print
    projection_time = matching_projections[0].time
    projection_time_formatted = ":".join(projection_time)

    print(f'Hora de la projecció : {projection_time_formatted}')

    # Get the current time
    current_time = datetime.datetime.now().time()

    # travel_time is a string in format hh:mm
    travel_time = plot_path(city_graph, path, "path.png")
    print(f'Temps de viatge: {travel_time} hores')

    hours_travel, minutes_travel = map(int, travel_time.split(":"))

    # Convert current_time to a datetime.datetime object
    current_datetime = datetime.datetime.combine(
        datetime.date.today(), current_time)

    # Calculate the arrival time by adding the travel time
    arrival_datetime = current_datetime + \
        datetime.timedelta(hours=hours_travel, minutes=minutes_travel)
    arrival_time = arrival_datetime.time()

    # Convert projection_time_formatted back to datetime.time
    projection_time = datetime.datetime.strptime(
        projection_time_formatted, "%H:%M").time()

    # Compare the arrival time with the projection time
    if arrival_time < projection_time:
        print("Arribaràs a temps a la projecció!")
    else:
        print("No podràs arribar a temps.")


if __name__ == '__main__':
    main()

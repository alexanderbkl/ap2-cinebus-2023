from datetime import datetime
from staticmap import StaticMap, CircleMarker, Line
import billboard
import buses
import city2
from haversine import haversine, Unit
from typing import List
#@GitHub: alexanderbkl


def create_billboard():
    return billboard.read()


def search_billboard(billboard, keyword):
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
    return city2.get_city_graph()


def find_path_to_cinema(city_graph, start_location, cinema_location):
    return city2.find_path(city_graph, start_location, cinema_location)

def plot_path(city_graph, path, filename):
    return city2.plot_path(city_graph, path, filename)


    
def calculate_time(city_graph, path):
    total_distance = 0.0
    for i in range(len(path) - 1):
        total_distance += haversine((city_graph.nodes[path[i]]['x'], city_graph.nodes[path[i]]['y']),
                                    (city_graph.nodes[path[i+1]]['x'], city_graph.nodes[path[i+1]]['y']), unit=Unit.KILOMETERS)
    
    
    speed = 20 / 60  # speed in km/minute
    travel_time = total_distance / speed  # time in minutes
    return travel_time

def main():
    print("Author: Alexander Baikálov")
    billboard = create_billboard()

    print("Showing billboard...")
    billboard.print_billboard()

    keyword = input('Enter keyword to search in billboard: ')
    matching_projections = search_billboard(billboard, keyword)
    print('Matching projections:')
    for projection in matching_projections:
        print(projection.film.title)

    bus_graph = buses.get_buses_graph()
    # print("Showing bus graph...")
    # buses.show(bus_graph)
    # print("Saving bus image plot...")
    # buses.plot(bus_graph, "test.png")

    # show CityGraph:
    city_graph = create_city_graph()
    #print("Showing city graph...")
    #city2.show(city_graph)

    # start_location = input('Enter your current location as latitude,longitude: ')
    # start_location = tuple(map(float, start_location.split(',')))
    # 41.43562334333733, 2.230975455414895
    start_location = (41.417490, 2.205378)

    # finding the cinema with the earliest projection
    matching_projections.sort(key=lambda p: p.time)
    try:
        cinema_location = (
            matching_projections[0].cinema.address.latitude, matching_projections[0].cinema.address.longitude)
    except IndexError:
        print('No matching projections found')
        return
    path = find_path_to_cinema(city_graph, start_location, cinema_location)
    
    
    #from the path (['102477', '102474', '100770',...]), we get the coordinates of the nodes
    # Convert the nodes of the shortest path into coordinates

    time_to_cinema = calculate_time(city_graph, path)
    #time_to_cinema is for example 16.63426
    #if current time plus time to get to the cinema is less than the projection time, we can make it
        
    #round time to cinema to 2 decimals
    time_to_cinema = round(time_to_cinema, 0)
    projection_time = matching_projections[0].time[0] * 60 + matching_projections[0].time[1]
    
    print(f'Time to get to the cinema: {time_to_cinema} minutes')

    now = datetime.now()
    current_time_in_minutes = now.hour * 60 + now.minute
    
    print(f'Current time in minutes: {current_time_in_minutes}')
    print(f'Projection time in minutes: {projection_time}')

    if current_time_in_minutes + time_to_cinema < projection_time:
        print("You can make it to the cinema in time for the projection!")
    else:
        print("You will not be able to reach the cinema in time for the projection.")
    #projection_time is f.e. 1345 (hhmm)

    #print the city_graph edges names
    #for edge in city_graph.edges:
    #    print('edge: ', edge)
    #print the city_graph edges info
    #for edge in city_graph.edges.data('info'):
    #    print('edge info: ', edge)
    #print the city_graph edges length
    #for edge in city_graph.edges.data('length'):
    #    print('edge length: ', edge)
    
    #print the names of the nodes in the path
    for node in path:
        print('Calle: ', city_graph.nodes[node]['name'])
        print('Línia TMB: ', city_graph.nodes[node]['line'])
        
    # Plot the path
    plot_path(city_graph, path, 'path.png')


if __name__ == '__main__':
    main()

from dataclasses import dataclass
import json
import time
from typing import List, Tuple
import datetime
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim


@dataclass
class Address:
    latitude: float
    longitude: float
    street: str


@dataclass
class Film:
    title: str
    genre: str
    director: str
    actors: List[str]


@dataclass
class Cinema:
    name: str
    address: Address


@dataclass
class Projection:
    film: Film
    cinema: Cinema
    time: Tuple[int, int]  # hour:minute
    language: str


@dataclass
class Billboard:
    films: List[Film]
    cinemas: List[Cinema]
    projections: List[Projection]

    def search_by_title(self, word: str) -> List[Projection]:
        return [p for p in self.projections if word.lower() in p.film.title.lower()]

    def search_by_genre(self, genre: str) -> List[Film]:
        return [f for f in self.films if f.genre.lower() == genre.lower()]

    def search_by_director(self, director: str) -> List[Film]:
        return [f for f in self.films if f.director.lower() == director.lower()]

    def search_by_actor(self, actor: str) -> List[Film]:
        return [f for f in self.films if actor.lower() in (a.lower() for a in f.actors)]

    def print_billboard(self):
        print(f"{'='*40}\n{' '*10}CINEMA BILLBOARD\n{'='*40}")

        print("\nFilms:")
        for film in self.films:
            print(
                f"Title: {film.title}\nGenre: {film.genre}\nDirector: {film.director}\nActors: {', '.join(film.actors)}\n{'-'*40}")

        print("\nCinemas:")
        for cinema in self.cinemas:
            print(f"Name: {cinema.name}\nAddress: {cinema.address.street}\nLatitude: {cinema.address.latitude}\nLongitude: {cinema.address.longitude}\n{'-'*40}")

        print("\nProjections:")
        for projection in self.projections:
            print(
                f"Film: {projection.film.title}\nCinema: {projection.cinema.name}\nTime: {projection.time[0]}:{projection.time[1]}\nLanguage: {projection.language}\n{'-'*40}")


def get_date_text() -> str:
    date = datetime.datetime.now()
    day = date.day
    weekday = date.weekday()
    weekdays = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
    weekday_text = weekdays[weekday]
    return weekday_text + " " + str(day)


def get_lat_long(address: str):
    geolocator = Nominatim(user_agent="geoapiExercises")
    try:
        # print("Address: " + address)

        if "Calle" in address:
            address = address.replace("Calle", "C/")
        location = geolocator.geocode(address)
        # wait a second to not overload the geolocator
        # time.sleep(1)
    except Exception as e:
        print("Exception: " + str(e))
        return None, None
    # search local registry for lat long of the address
    if location is None:
        if address == "Gran Vía de les Corts Catalanes, 385, 08015 Barcelona":
            return 41.37644410290286, 2.149453745956052
        elif address == "C/ Aribau, 8, 08011 Barcelona":
            return 41.38624248615302, 2.162546061491572
        elif address == "Paseig de Gracia, 13, 08007 Barcelona":
            return 41.389521242850776, 2.1674442707066204
        elif address == "Sta Fé de Nou Mèxic s/n, 08017 Barcelona":
            return 41.39409653060461, 2.136205065978579
        elif address == "Passeig Potosí 2 - Centro Comercial La Maquinista, 08030 Barcelona":
            return 41.43957036087736, 2.198350369068757
        elif address == "Paseo Andreu Nin s/n - Pintor Alzamora, 08016 Barcelona":
            return 41.43264617346267, 2.1817424582716707
        print("Could not find the address")
        return None, None
    else:
        return (location.latitude, location.longitude)


# The 'read' function is a placeholder here, since it's not clear where and how to return the Billboard.
def read() -> Billboard:
    # download the necessary data

    # get date_text:
    date_text = get_date_text()

    url = "https://www.sensacine.com/cines/cines-en-72480/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "lxml")

    cinemas: List[Cinema] = []
    films: List[Film] = []
    projections: List[Projection] = []

    div = soup.find("div", id="col_content")

    cinema_divs = div.find_all("div", class_="margin_10b j_entity_container")
    movie_divs = div.find_all("div", class_="j_w j_tabs")

    for cinemaDiv, movieDiv in zip(cinema_divs, movie_divs):
        name_h2 = cinemaDiv.find("h2", class_="tt_18")
        cine_name = name_h2.a.text.strip()
        address_span = cinemaDiv.find_all("span", class_="lighten")[1]
        cine_address = address_span.text.strip()
        latitude, longitude = get_lat_long(cine_address)
        cine_address = Address(latitude, longitude, cine_address)
        cinema = Cinema(cine_name, cine_address)
        cinemas.append(cinema)

        tabs_box_panels = movieDiv.find("div", class_="tabs_box_panels")
        tabs_box = tabs_box_panels.find(
            "div", class_="tabs_box_pan item-0") if tabs_box_panels else None
        if tabs_box:
            for item_resa in tabs_box.find_all("div", class_="item_resa"):
                div_j_w = item_resa.find("div", class_="j_w")
                if div_j_w.find("a", class_="underline") is None:
                    continue
                data_movie = div_j_w["data-movie"]

                ulHours = item_resa.find("ul", class_="list_hours")
                hours = []
                for li in ulHours.find_all("li"):
                    hours.append(li.em.text.strip())

                language = "ES"
                movie_data = json.loads(data_movie)

                film_title = movie_data["title"]
                genre = movie_data["genre"]
                director = movie_data["directors"][0]
                actors = movie_data["actors"]

                film = Film(film_title, genre, director, actors)
                films.append(film)

                for hour in hours:
                    # assuming time is in "HH:MM" format
                    hour_str, minute_str = hour.split(':')
                    # if minute is 0, add another 0
                    if minute_str == "0":
                        minute_str = "00"
                    time_tuple = (hour_str, minute_str)
                    projections.append(Projection(
                        film, cinema, time_tuple, language))
        else:
            continue

    return Billboard(films, cinemas, projections)

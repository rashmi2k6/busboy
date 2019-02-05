import json
from concurrent.futures import Executor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from os import makedirs, scandir
from sys import argv
from threading import Event, Timer
from time import localtime, strftime
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

import psycopg2 as pp2
import requests
from psycopg2.extras import Json

import busboy.database as db
import busboy.recording as rec
from busboy.apis import routes_at_stop, stop_passage
from busboy.constants import (
    church_cross_east,
    cycle_stops,
    route_cover,
    stop_passage_tdi,
)
from busboy.model import StopId


def main() -> None:
    if len(argv) == 1:
        rec.loop()
    elif argv[1] == "coords":
        lines(argv[2], coords)
    elif argv[1] == "lmt":
        p, t = lmt_test(int(argv[2]))
        print(f"Last modified time is {p}")
        print(f"Trip last modified time is {t}")
        print(f"Times are equal? {t == p}")
    else:
        rec.loop(argv[1:])


def make_request(url: str, trip: str) -> None:
    trip_response = requests.get(url, params={"trip": trip})
    save_response(trip, trip_response)


def save_response(trip: str, trip_response: requests.Response) -> None:
    timestamp = datetime.now()
    load_into_database(trip_response.json(), timestamp, trip)


def load_into_database(json: Dict[str, Any], timestamp: datetime, trip: str) -> None:
    print(f"Loading into database for trip {trip} at {timestamp}")
    passages = json["stopPassageTdi"]
    connection = db.default_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "insert into passage_responses_old (response, timestamp, trip) values (%s, %s, %s)",
                [Json(passages), timestamp, trip],
            )
    connection.close()


def save_response_to_file(
    trip: str, trip_response: requests.Response, stop: Any
) -> None:
    timestamp = datetime.now()
    y, m, d = timestamp.year, timestamp.month, timestamp.day
    folder = f'/Users/Noel/Developer/Projects/Busboy/src/main/resources/trace/{"/".join([y, m, d])}/{trip}'
    h, min, s = timestamp.hour, timestamp.minute, timestamp.second
    filename = f'{folder}/trace-{"-".join([h, min, s])}.json'
    makedirs(folder, exist_ok=True)
    with open(filename, "w") as f:
        f.write(json.dumps(trip_response.json(), indent=2))
    print(f"Wrote output to {filename}")


def trips(json_response: Dict[str, Any]) -> List[str]:
    """Gets the trip ids from a stop response."""
    passages = filter(lambda p: p[0] != "foo", json_response["stopPassageTdi"].items())
    passage_duids = map(lambda p: p[1]["trip_duid"]["duid"], passages)
    return list(passage_duids)


def lines(folder: str, function: Callable[[Dict[str, Any]], str]) -> None:
    fs = scandir(folder)
    jsons = map(lambda f: readJson(f.path), fs)
    output = "\n".join(list(map(function, jsons)))
    print(output)


def readJson(filePath: str) -> Dict[str, Any]:
    with open(filePath, "r") as f:
        j = json.load(f)
    return j


def coords(json: Dict[str, Any]) -> str:
    passage_zero = json["stopPassageTdi"]["passage_0"]
    raw_coords = (passage_zero["latitude"], passage_zero["longitude"])
    refined_coords = map(lambda l: l / 3_600_000, raw_coords)
    return str(tuple(refined_coords))


def minimal_route_cover() -> Set[str]:
    stops = get_stops_from_file()
    routes = get_routes_from_file()

    routes_covered: Set[str] = set()
    stop_cover = set()
    print(f"{len(stops)} stops to try")
    for stop in stops:
        try:
            print(f"Trying stop {stop}")
            print(f"Have {len(routes_covered)} routes out of {len(routes)}")
            if len(routes_covered) >= len(routes):
                break
            new_routes = routes_at_stop(stop)
            if not new_routes.issubset(routes_covered):
                stop_cover.add(stop)
                routes_covered = routes_covered.union(new_routes)
        except Exception as e:
            print(f"Got error {e} on stop {stop}")
    return stop_cover


def get_stops_from_file() -> Dict[str, str]:
    stops_json = readJson("resources/example-responses/busStopPoints.json")
    return {b["duid"]: b for k, b in stops_json["bus_stops"].items()}


def get_routes_from_file() -> Dict[str, str]:
    routes_json = readJson("resources/example-responses/routes.json")
    return {
        r["duid"]: r["short_name"]
        for k, r in routes_json["routeTdi"].items()
        if k != "foo"
    }


def lmt_test(passage_number: int) -> Tuple[str, str]:
    stop_json = requests.get(
        stop_passage_tdi, params={"stop_point": church_cross_east}
    ).json()
    passage_json = stop_json["stopPassageTdi"][f"passage_{passage_number}"]
    passage_id = passage_json["duid"]
    passage_lmt = passage_json["last_modification_timestamp"]
    trip = passage_json["trip_duid"]["duid"]
    trip_json = requests.get(stop_passage_tdi, params={"trip": trip}).json()
    trip_passages = [
        p
        for k, p in trip_json["stopPassageTdi"].items()
        if k != "foo" and p["duid"] == passage_id
    ]
    if len(trip_passages) > 1:
        raise AssertionError("Got {len(trip_passages)} matching passages (expected 1)")
    trip_lmt = trip_passages[0]["last_modification_timestamp"]
    return (passage_lmt, trip_lmt)


if __name__ == "__main__":
    main()

import math
import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv


load_dotenv()
api_key = os.getenv("api_key")

relevant_stations = [
    {"name": "Mainz Höfchen/Staatstheater", "id": "A=1@O=MZ Höfchen/Listmann", "display_name": "Höfchen"},
    {"name": "Mainz Schusterstraße", "id": "A=2@O=Schusterstraße 55116 Mainz", "display_name": "Schusterstraße"},
]

relevant_stops = [
    {"name": "Mainz Hauptbahnhof", "id": "A=1@O=Mainz Hauptbahnhof", "skip": "Mainz Hbf West/Taubertsberg Bad+Spa", "display_name": "Mainz Hbf"},
    {"name": "Mainz Hbf West/Taubertsberg Bad+Spa", "id": "A=1@O=Mainz Hbf West/Taubertsberg Bad+Spa", "display_name": "Mainz Hbf West"},
    {"name": "Mainz-Oberstadt Universität/Haupteingang", "id": "A=1@O=Mainz-Oberstadt Universität/Haupteingang", "display_name": "Universität"},
    {"name": "Mainz-Oberstadt Friedrich-von-Pfeiffer-Weg/Univers", "id": "A=1@O=MZ Friedrich-von-Pfeiffer-Weg", "display_name": "Friedr.-v.-Pf.-Weg"},
]

colors = {
    "6": {"bg": "ef7c00", "fg": "000000"},
    "28": {"bg": "dbe283", "fg": "000000"},
    "54": {"bg": "3d8823", "fg": "ffffff"},
    "55": {"bg": "3d8823", "fg": "ffffff"},
    "56": {"bg": "94c11a", "fg": "000000"},
    "57": {"bg": "94c11a", "fg": "000000"},
    "58": {"bg": "94c11a", "fg": "000000"},
    "60": {"bg": "00aecb", "fg": "ffffff"},
    "62": {"bg": "c22b02", "fg": "ffffff"},
    "63": {"bg": "00aecb", "fg": "ffffff"},
    "64": {"bg": "f59c00", "fg": "000000"},
    "65": {"bg": "f59c00", "fg": "000000"},
    "66": {"bg": "ffd400", "fg": "000000"},
    "68": {"bg": "007f3b", "fg": "ffffff"},
    "70": {"bg": "a6156f", "fg": "ffffff"},
    "71": {"bg": "a6156f", "fg": "ffffff"},
    "78": {"bg": "0a4871", "fg": "ffffff"},
    "79": {"bg": "007f3b", "fg": "ffffff"},
    "80": {"bg": "0060a7", "fg": "ffffff"},
    "81": {"bg": "0060a7", "fg": "ffffff"},
    "90": {"bg": "8d004b", "fg": "ffffff"},
    "91": {"bg": "904b00", "fg": "ffffff"},
    "93": {"bg": "58770b", "fg": "ffffff"},
}


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _safe_time_delta_minutes(start_time, end_time):
    if start_time == "N/A" or end_time == "N/A":
        return "N/A"

    return math.floor(
        (datetime.strptime(end_time, "%H:%M:%S") - datetime.strptime(start_time, "%H:%M:%S")).total_seconds() / 60
    )


def _parse_date(value):
    if not value or value == "N/A":
        return None

    for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%Y%m%d"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def _parse_time(value):
    if not value or value == "N/A":
        return None

    for time_format in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, time_format).time()
        except ValueError:
            continue
    return None


def _combine_datetime(date_value, time_value, default_date=None):
    parsed_time = _parse_time(time_value)
    if not parsed_time:
        return None

    parsed_date = _parse_date(date_value) or default_date or datetime.today().date()
    return datetime.combine(parsed_date, parsed_time)


def _normalize_rollover(reference_dt, compared_dt):
    if not reference_dt or not compared_dt:
        return compared_dt

    if compared_dt < reference_dt - timedelta(hours=12):
        return compared_dt + timedelta(days=1)
    return compared_dt


def _safe_datetime_delta_minutes(start_time, end_time, start_date=None, end_date=None, default_date=None):
    start_dt = _combine_datetime(start_date, start_time, default_date)
    if not start_dt:
        return "N/A"

    end_default_date = _parse_date(start_date) or default_date
    end_dt = _combine_datetime(end_date, end_time, end_default_date)
    if not end_dt:
        return "N/A"

    end_dt = _normalize_rollover(start_dt, end_dt)
    return math.floor((end_dt - start_dt).total_seconds() / 60)


def fetch_departures():
    if not api_key:
        raise RuntimeError("Missing api_key in environment or .env file.")

    domain = "www.rmv.de/hapi"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "accept": "application/json",
    }
    url = f"https://{domain}/departureBoard"

    departures_data = []
    relevant_station_names = {station["name"] for station in relevant_stations}
    relevant_station_display_names = {
        station["name"]: station.get("display_name", station["name"])
        for station in relevant_stations
    }
    relevant_stop_names = {stop["name"] for stop in relevant_stops}
    relevant_stop_display_names = {
        stop["name"]: stop.get("display_name", stop["name"]) for stop in relevant_stops
    }

    for relevant_station in relevant_stations:
        params = {
            "id": relevant_station["id"],
            "duration": 60,
            "passlist": 1,
        }

        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        departures = response.json().get("Departure", [])
        for departure in departures:
            if departure.get("stop") in relevant_station_names:
                departures_data.append(departure)

    now_dt = datetime.now()
    today = now_dt.date()
    departures = []

    for departure_info in departures_data:
        product = _as_dict(departure_info.get("ProductAtStop"))
        products = departure_info.get("Product", [])
        first_product = products[0] if isinstance(products, list) and products else {}
        first_product = first_product if isinstance(first_product, dict) else {}

        line = product.get("line", "N/A")
        departure = {
            "name": line,
            "color": colors.get(line, {"bg": "cccccc", "fg": "000000"}),
            "id": first_product.get("num", "N/A"),
            "station": departure_info.get("stop", "N/A"),
            "station_display_name": relevant_station_display_names.get(
                departure_info.get("stop", "N/A"),
                departure_info.get("stop", "N/A"),
            ),
            "track": departure_info.get("track", "N/A"),
            "direction": departure_info.get("direction", "N/A"),
            "scheduled_time": departure_info.get("time", "N/A"),
            "actual_time": departure_info.get("rtTime", departure_info.get("time", "N/A")),
            "time_to_departure": None,
            "delay": None,
            "messages": [],
            "stops_at": {},
        }

        stops = _as_dict(departure_info.get("Stops")).get("Stop", [])
        for stop in stops:
            stop_name = stop.get("name", "N/A")
            if stop_name in relevant_stop_names:
                arrival_time = stop.get("arrTime", "N/A")
                rt_arrival_time = stop.get("rtArrTime", arrival_time)
                arrival_date = stop.get("arrDate", departure_info.get("date", "N/A"))
                rt_arrival_date = stop.get("rtArrDate", arrival_date)
                # use the configured display_name for the stop as the key
                display_key = relevant_stop_display_names.get(stop_name, stop_name)
                departure["stops_at"][display_key] = {
                    "arrival_time": arrival_time,
                    "rt_arrival_time": rt_arrival_time,
                    "delay": _safe_datetime_delta_minutes(
                        arrival_time,
                        rt_arrival_time,
                        start_date=arrival_date,
                        end_date=rt_arrival_date,
                        default_date=today,
                    ),
                }

        for relevant_stop in relevant_stops:
            skip_name = relevant_stop.get("skip")
            # if this departure includes the referenced stop, remove the skipped stop
            if skip_name:
                src_key = relevant_stop_display_names.get(relevant_stop["name"], relevant_stop["name"])
                skip_key = relevant_stop_display_names.get(skip_name, skip_name)
                if src_key in departure["stops_at"]:
                    departure["stops_at"].pop(skip_key, None)

        messages = _as_dict(departure_info.get("Messages")).get("Message", [])
        for message in messages:
            text = message.get("text")
            if text:
                departure["messages"].append(text)

        scheduled_dt = _combine_datetime(
            departure_info.get("date", "N/A"),
            departure["scheduled_time"],
            today,
        )
        scheduled_dt = _normalize_rollover(now_dt, scheduled_dt)

        actual_dt = _combine_datetime(
            departure_info.get("rtDate", departure_info.get("date", "N/A")),
            departure["actual_time"],
            scheduled_dt.date() if scheduled_dt else today,
        )
        actual_dt = _normalize_rollover(scheduled_dt or now_dt, actual_dt)

        if actual_dt:
            departure["time_to_departure"] = math.floor((actual_dt - now_dt).total_seconds() / 60)
        else:
            departure["time_to_departure"] = "N/A"

        if actual_dt and scheduled_dt:
            departure["delay"] = (actual_dt - scheduled_dt).total_seconds() / 60
        else:
            departure["delay"] = "N/A"

        departures.append(departure)

    departures.sort(key=lambda item: item["time_to_departure"] if isinstance(item["time_to_departure"], int) else float("inf"))

    seen_ids = set()
    unique_departures = []
    for departure in departures:
        if departure["id"] in seen_ids:
            continue
        seen_ids.add(departure["id"])
        unique_departures.append(departure)

    return unique_departures
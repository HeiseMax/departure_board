
import math
import os
from datetime import datetime
from flask import Flask, render_template, jsonify
import requests
from dotenv import load_dotenv


app = Flask(__name__, template_folder=".")

# read API key from .env file
load_dotenv()
api_key = os.getenv("api_key")

# stations that should be displayed
relevant_stations = [
    {"name": "Mainz Höfchen", "id": "A=2@O=Höfchen 55116 Mainz"},
    {"name": "Mainz Schusterstraße", "id": "A=2@O=Schusterstraße 55116 Mainz"},
]

# stations/stops where we want to know if they are reachable
relevant_stops = [
    {"name": "Mainz Hauptbahnhof", "id": "A=1@O=Mainz Hauptbahnhof"},
    # TODO ?{"name": "Mainz Hbf West/Taubertsberg Bad+Spa", "id": "A=1@O=Mainz Hbf West/Taubertsberg Bad+Spa"}
    {"name": "Mainz-Oberstadt Universität/Haupteingang", "id": "A=1@O=Mainz-Oberstadt Universität/Haupteingang"}
]

# routes
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/get_departures")
def get_departures():
    domain = "www.rmv.de/hapi"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "accept": "application/json",
    }

    service = "departureBoard"
    url = f"https://{domain}/{service}"


    departures_data = []
    for relevant_station in relevant_stations:
        params = {    
            "id": relevant_station["id"],
            "duration": 30,
            "passlist": 1,
        }

        x = requests.get(url, headers=headers, params=params)
        deps = x.json().get("Departure", [])
        for dep in deps:
            if dep.get("stop") in [rs["name"] for rs in relevant_stations]:
                departures_data.append(dep)

    current_time = datetime.now().time()
    departures = []
    for departure_info in departures_data:
        id_ = departure_info.get("Product", [{}])[0].get("num", "N/A")
        departure = {
            "name": departure_info.get("name", "N/A"),
            "id": id_,
            "station": departure_info.get("stop", "N/A"),
            "track": departure_info.get("track", "N/A"),
            "direction": departure_info.get("direction", "N/A"),
            "scheduled_time": departure_info.get("time", "N/A"),
            "actual_time": departure_info.get("rtTime", departure_info.get("time", "N/A")),
            "time_to_departure": None,
            "delay": None,
            "messages": [],
            "stops_at": {},
        }

        stps = departure_info.get("Stops", {}).get("Stop", [])
        for stp in stps:
            stop_name = stp.get("name", "N/A")
            if stop_name in [rs["name"] for rs in relevant_stops]:
                stp_arrival_time = stp.get("arrTime", "N/A")
                stp_rt_arrival_time = stp.get("rtArrTime", stp_arrival_time)
                stp_delay = math.floor((datetime.strptime(stp_rt_arrival_time, "%H:%M:%S") - datetime.strptime(stp_arrival_time, "%H:%M:%S")).total_seconds() / 60) if stp_arrival_time != "N/A" and stp_rt_arrival_time != "N/A" else "N/A"
                departure["stops_at"][stop_name] = {
                    "arrival_time": stp_arrival_time,
                    "rt_arrival_time": stp_rt_arrival_time,
                    "delay": stp_delay
                }

        messages = departure_info.get("Messages", {}).get("Message", [])
        for message in messages:
            departure["messages"].append(message["text"])
            # TODO filter messages (affected stops?)
            # if "Verspätung" in message.get("text", ""):
            #     departure["message"] = message["text"]
            #     break

        actual_time = datetime.strptime(departure["actual_time"], "%H:%M:%S").time() if departure["actual_time"] != "N/A" else None
        scheduled_time = datetime.strptime(departure["scheduled_time"], "%H:%M:%S").time() if departure["scheduled_time"] != "N/A" else None

        if actual_time and current_time:
            time_to_departure = math.floor((datetime.combine(datetime.today(), actual_time) - datetime.combine(datetime.today(), current_time)).total_seconds() / 60)
        else:
            time_to_departure = "N/A"
        if actual_time and scheduled_time:
            delay = (datetime.combine(datetime.today(), actual_time) - datetime.combine(datetime.today(), scheduled_time)).total_seconds() / 60
        else:
            delay = "N/A"

        departure["time_to_departure"] = time_to_departure
        departure["delay"] = delay
        departures.append(departure)

    # sorted by time to departure (reverse for filtering)
    departures.sort(key=lambda x: x["time_to_departure"] if isinstance(x["time_to_departure"], int) else float('inf'), reverse=True)

    # get set of id's to filter out doubles
    seen_ids = set()
    departures = [dep for dep in departures if not (dep["id"] in seen_ids or seen_ids.add(dep["id"]))]
    
    return jsonify(departures[::-1])


if __name__ == "__main__":
    app.run(debug=True)


import os
from datetime import datetime
from flask import Flask, render_template, jsonify
import requests
from dotenv import load_dotenv


app = Flask(__name__, template_folder=".")

# read API key from .env file
load_dotenv()
api_key = os.getenv("api_key")

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

    params = {    
        "id": "A=2@O=Höfchen 55116 Mainz",
        "duration": 5,
    }

    x = requests.get(url, headers=headers, params=params)

    departures_data = x.json().get("Departure", [])

    departures = []
    for departure_info in departures_data:
        departure = {
            "name": departure_info.get("name", "N/A"),
            "direction": departure_info.get("direction", "N/A"),
            "scheduled_time": departure_info.get("time", "N/A"),
            "actual_time": departure_info.get("rtTime", "N/A"),
            "delay": None
        }

        actual_time = datetime.strptime(departure["actual_time"], "%H:%M:%S").time() if departure["actual_time"] != "N/A" else None
        scheduled_time = datetime.strptime(departure["scheduled_time"], "%H:%M:%S").time() if departure["scheduled_time"] != "N/A" else None


        if actual_time and scheduled_time:
            delay = (datetime.combine(datetime.today(), actual_time) - datetime.combine(datetime.today(), scheduled_time)).total_seconds() / 60
        else:
            delay = "N/A"

        departure["delay"] = delay
        departures.append(departure)
    return jsonify(departures)


if __name__ == "__main__":
    app.run(debug=True)

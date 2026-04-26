
from flask import Flask, render_template, jsonify

from departure_data import fetch_departures


app = Flask(__name__, template_folder=".")

# routes
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/get_departures")
def get_departures():
    return jsonify(fetch_departures())


if __name__ == "__main__":
    app.run(debug=True)

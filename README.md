# BahnAPI (Flask)

Small Flask app that shows upcoming departures in a browser table.

## Used API

- `RMV HAPI` (`https://www.rmv.de/hapi`)
- Endpoint used: `departureBoard`
- Auth: Bearer token from `.env` (`api_key`)

## Setup

1. Create a virtual environment (optional but recommended):
	```powershell
	python -m venv .venv (create)

	.\.venv\Scripts\activate (activate windows)
	source .venv\bin\activate (activate linux)
	```
2. Install dependencies:
	```powershell
	pip install -r requirements.txt
	```
3. Create a `.env` file in the project root:
	```env
	api_key=YOUR_RMV_API_KEY
	```

## Run

Start the app:

```powershell
python app.py
flask run --host=0.0.0.0 (accessible from whole network)
```

Open in browser:

- `http://127.0.0.1:5000/` (UI)
- `http://127.0.0.1:5000/get_departures` (JSON data)

## Terminal View

Run the same API data in the terminal with a refresh loop:

```powershell
python terminal_view.py
```

Optional environment variables:

- `REFRESH_SECONDS=15` to change the update interval

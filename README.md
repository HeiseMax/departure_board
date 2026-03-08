# BahnAPI (Flask)

Small Flask app that shows upcoming departures in a browser table.

## Used API

- `RMV HAPI` (`https://www.rmv.de/hapi`)
- Endpoint used: `departureBoard`
- Auth: Bearer token from `.env` (`api_key`)

## Setup

1. Create a virtual environment (optional but recommended):
	```powershell
	python -m venv .venv
	.\.venv\Scripts\activate
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
```

Open in browser:

- `http://127.0.0.1:5000/` (UI)
- `http://127.0.0.1:5000/get_departures` (JSON data)

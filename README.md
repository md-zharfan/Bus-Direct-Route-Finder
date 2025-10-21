# Bus Direct Route Finder

A project to query direct bus services between two stops in Singapore
using **LTA Datamall APIs** and **PTC fare tables**.

Stack: Streamlit UI · Python · SQLite (MariaDB/MySQL-ready) · MongoDB 
Data: LTA DataMall (BusStops/BusServices/BusRoutes + BusArrival), PTC fare CSVs

## Features

-   Load bus stops, services, and routes from LTA Datamall JSON files or
    API.
-   Load fare tables (Trunk, Feeder, Express) from PTC CSVs.
-   Store all data in a local SQLite database (`bus.db`).
-   Query for direct bus services between two stops.
-   Show number of hops, distance, estimated travel time.
-   Calculate fares for:
    -   Adult
    -   Senior Citizen
    -   Student / NSmen
    -   Workfare Concession
    -   Cash fares

## Project Structure

repo/
├─ app.py                      # Streamlit app (UI)
├─ directroute_finder.py       # CLI loader + direct route query (optional)
├─ fetch_lta_data.py           # Pulls LTA DataMall JSON to data/raw (optional)
├─ requirements.txt            # Python deps
├─ assets/
│  └─ style.css                # Custom UI theme (Streamlit CSS)
├─ .streamlit/
│  └─ config.toml              # Global theme (optional)
├─ data/
│  ├─ raw/                     # BusStops.json, BusServices.json, BusRoutes.json
│  └─ fares/                   # PTC fare CSVs (Trunk/Feeder/Express)
├─ .env.example                # Template for secrets (e.g., LTA_API_KEY)
└─ README.md

## Setup

1.  Clone the repo or copy files.

2.  Create and activate a virtual environment:

    ``` bash
    python -m venv .venv
    .venv\Scripts\activate   # Windows
    source .venv/bin/activate # Mac/Linux
    ```

3.  Install dependencies:

    ``` bash
    pip install -r requirements.txt
    ```

4.  Place LTA JSONs in `data/raw/` and PTC fare CSVs in `data/fares/`.

## Usage (Streamlit App)

Run the streamlit app:

``` bash
streamlit run app.py
```

Example:

    Enter FROM stop code: 75009
    Enter TO stop code: 76059

Output:

    service_no  direction  operator  category  from_stop  to_stop  hops  travel_km  est_minutes  fare
    10          1          SBST      TRUNK     75009      76059    1     0.6        2.0          $1.19
    20          1          SBST      TRUNK     75009      76059    1     0.6        2.0          $1.19
    292         1          SBST      FEEDER    75009      76059    1     0.6        2.0          $1.19

## Notes

-   LTA API key must be configured in `.env` for fetching fresh data.
-   Fare tables are effective from 28 December 2024 (PTC release).
-   SQLite database (`bus.db`) is auto-populated on first run.

## Command Reference
Start Streamlit

``` bash
streamlit run app.py
```

Stop Streamlit

CTRL + C

Activate / Deactivate venv

Activate (see Setup)

Deactivate:

```bash
deactivate
```

Rebuild requirements (pin versions)

```bash
pip freeze > requirements.txt
```
## License / Credits

Data © LTA DataMall / PTC (refer to their terms).

This app is for academic/demo purposes.

## Authors

Team: Zharfan, Eden, Kalai, Su Myat, Nayli, Xin Rong
Module: INF2003 - Database Systems

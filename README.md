# Bus Direct Route Finder

A project to query direct bus services between two stops in Singapore
using **LTA Datamall APIs** and **PTC fare tables**.

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

    bus-direct-route/
    │── data/
    │   ├── raw/        # LTA JSON files here (BusStops, BusServices, BusRoutes, BusArrival)
    │   ├── fares/      # PTC fare CSVs here (Trunk, Feeder, Express)
    │── directroute_finder.py   # Main script to run queries
    │── fetch_lta_data.py       # Script to fetch LTA JSONs using API key
    │── suggest_pairs.py        # (Optional) Helper to test stop pairs
    │── bus.db                  # SQLite database (auto-generated)
    │── requirements.txt        # Python dependencies
    │── README.md               # This file

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

## Usage

Run the direct route finder:

``` bash
python directroute_finder.py
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

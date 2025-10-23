# app.py
import os
import pandas as pd
import streamlit as st
from pathlib import Path
import json
from mongita import MongitaClientDisk

# load css if present
css_path = Path("assets/style.css")
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
else:
    st.warning("⚠️ CSS file not found — UI may not render properly.")

# config
DB_PATH = os.environ.get("BUS_DB_PATH", "bus.db")


DIRECT_SQL = """
WITH trips AS (
  SELECT rs_from.service_no, rs_from.direction, s.operator, s.category,
         LOWER(?) AS rider_type, LOWER(?) AS pay_mode,
         ? AS from_stop, ? AS to_stop,
         (rs_to.stop_sequence - rs_from.stop_sequence) AS hops,
         ROUND(rs_to.distance_km - rs_from.distance_km, 2) AS travel_km,
         ROUND(
           CASE WHEN (rs_to.distance_km - rs_from.distance_km) > 0
                THEN 3.2 * (rs_to.distance_km - rs_from.distance_km)
                ELSE 5.5 * (rs_to.stop_sequence - rs_from.stop_sequence)
           END
         ) AS est_minutes
  FROM route_stops rs_from
  JOIN route_stops rs_to
    ON rs_to.service_no = rs_from.service_no
   AND rs_to.direction  = rs_from.direction
   AND rs_to.stop_sequence > rs_from.stop_sequence
  JOIN services s
    ON s.service_no = rs_from.service_no
   AND s.direction  = rs_from.direction
  WHERE rs_from.bus_stop_code = ?
    AND rs_to.bus_stop_code   = ?
),
picked AS (
  SELECT t.*,
         CASE
           WHEN rider_type='adult'    AND pay_mode='card' THEN fb.adult_card_cents
           WHEN rider_type='adult'    AND pay_mode='cash' THEN COALESCE(fb.adult_cash_cents,   fb.adult_card_cents)
           WHEN rider_type='senior'   AND pay_mode='card' THEN fb.senior_card_cents
           WHEN rider_type='senior'   AND pay_mode='cash' THEN COALESCE(fb.senior_cash_cents,  fb.senior_card_cents)
           WHEN rider_type='student'  AND pay_mode='card' THEN fb.student_card_cents
           WHEN rider_type='student'  AND pay_mode='cash' THEN COALESCE(fb.student_cash_cents, fb.student_card_cents)
           WHEN rider_type='workfare' AND pay_mode='card' THEN fb.workfare_card_cents
           WHEN rider_type='workfare' AND pay_mode='cash' THEN COALESCE(fb.workfare_cash_cents,fb.workfare_card_cents)
           ELSE fb.adult_card_cents
         END AS fare_cents,

         CASE
           WHEN rider_type='adult'    AND pay_mode='card' THEN 'adult_card'
           WHEN rider_type='adult'    AND pay_mode='cash' THEN CASE WHEN fb.adult_cash_cents     IS NOT NULL THEN 'adult_cash'     ELSE 'adult_card' END
           WHEN rider_type='senior'   AND pay_mode='card' THEN 'senior_card'
           WHEN rider_type='senior'   AND pay_mode='cash' THEN CASE WHEN fb.senior_cash_cents    IS NOT NULL THEN 'senior_cash'    ELSE 'senior_card' END
           WHEN rider_type='student'  AND pay_mode='card' THEN 'student_card'
           WHEN rider_type='student'  AND pay_mode='cash' THEN CASE WHEN fb.student_cash_cents   IS NOT NULL THEN 'student_cash'   ELSE 'student_card' END
           WHEN rider_type='workfare' AND pay_mode='card' THEN 'workfare_card'
           WHEN rider_type='workfare' AND pay_mode='cash' THEN CASE WHEN fb.workfare_cash_cents  IS NOT NULL THEN 'workfare_cash'  ELSE 'workfare_card' END
           ELSE 'adult_card'
         END AS fare_source
  FROM trips t
  LEFT JOIN fare_bands fb
    ON UPPER(fb.category) = UPPER(t.category)
   AND t.travel_km >= fb.min_km
   AND t.travel_km <= fb.max_km
)
SELECT
  service_no, direction, operator, category,
  from_stop, to_stop, hops, travel_km, est_minutes,
  CASE WHEN fare_cents IS NOT NULL THEN '$' || printf('%.2f', fare_cents/100.0) END AS fare,
  fare_source
FROM picked
ORDER BY fare, hops, travel_km;
"""

@st.cache_resource(show_spinner=False)
def get_conn():
    import sqlite3, os
    DB_PATH = os.environ.get("BUS_DB_PATH", "bus.db")
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found at '{DB_PATH}'. Run the loader or set BUS_DB_PATH."
        )
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@st.cache_data(show_spinner=False)
def load_stops():
    conn = get_conn()                     # <-- get resource here
    df = pd.read_sql_query(
        "SELECT bus_stop_code, description, road_name FROM stops ORDER BY bus_stop_code",
        conn
    )
    df["label"] = (
        df["bus_stop_code"]
        + " — " + df["description"].fillna("")
        + " (" + df["road_name"].fillna("") + ")"
    )
    return df

def query_direct(conn, rider, mode, from_code, to_code):
    params = (rider, mode, from_code, to_code, from_code, to_code)
    df = pd.read_sql_query(DIRECT_SQL, conn, params=params)
    return df

# add your nosql functions here, for example
# --- NoSQL (Mongita) Setup ---
def load_nosql_data():
    import traceback
    db_path = os.path.join("data", "nosql")
    print(f"[DEBUG] Mongita DB path: {os.path.abspath(db_path)}")
    client = MongitaClientDisk(db_path)
    db = client["bus_data"]
    import_dir = Path("data/import")
    if not import_dir.exists():
        print("[DEBUG] Import directory does not exist.")
        return db
    json_files = list(import_dir.glob("*.json"))
    print(f"[DEBUG] JSON files to import: {json_files}")
    for file in json_files:
        collection_name = file.stem.replace('.', '_')
        collection = db[collection_name]
        try:
            if collection.count_documents({}) == 0:
                print(f"[DEBUG] Importing {file} into collection {collection_name}")
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        collection.insert_many(data)
                    else:
                        collection.insert_one(data)
        except Exception as e:
            print(f"[ERROR] Failed to import {file} into {collection_name}: {e}")
            traceback.print_exc()
    # List Mongita files in nosql dir for debug
    try:
        files = os.listdir(db_path)

        print(f"[DEBUG] Files in nosql dir after import: {files}")
    except Exception as e:
        print(f"[ERROR] Could not list files in nosql dir: {e}")
    return db

# ---------- streamlit ui ----------
st.set_page_config(page_title="Bus Route & Arrivals Demo", layout="centered")
st.title("Bus Route & Arrivals Demo")

# divider
st.markdown(
    '<hr style="border:0;height:1px;background:linear-gradient(90deg,transparent,#FF6BA3,transparent);margin:1rem 0;">',
    unsafe_allow_html=True
)

# --- section 1: direct route finder (SQL) ---
st.subheader("🚌 Direct Route Finder (SQL)")
conn = get_conn()
stops = load_stops()

c1, c2 = st.columns(2)
rider = c1.selectbox("Rider type", ["adult", "senior", "student", "workfare"])
mode = c2.selectbox("Payment mode", ["card", "cash"])

c3, c4 = st.columns(2)
from_stop = c3.selectbox("From stop", stops["label"].tolist())
to_stop = c4.selectbox("To stop", stops["label"].tolist(), index=min(1, len(stops)-1))
from_code = from_stop.split(" — ", 1)[0]
to_code = to_stop.split(" — ", 1)[0]


# --- Store and display SQL results ---
if "sql_results" not in st.session_state:
    st.session_state["sql_results"] = None
if st.button("Search direct routes"):
    with st.spinner("Querying database..."):
        df = query_direct(conn, rider, mode, from_code, to_code)
    if df.empty:
        st.warning("No direct routes found.")
        st.session_state["sql_results"] = None
    else:
        best_fare = df["fare"].str.replace("$","").astype(float).min()
        best_eta  = df["est_minutes"].min()
        services  = df["service_no"].nunique()
        operators = df["operator"].nunique()

        st.session_state["sql_results"] = {
            "df": df.drop(columns=["category"], errors="ignore").rename(columns={
                "service_no": "Service", "direction": "Dir", "operator": "Operator",
                "from_stop": "From", "to_stop": "To",
                "hops": "Hops", "travel_km": "Km", "est_minutes": "ETA (min)",
                "fare": "Fare", "fare_source": "Fare source"
            }),
            "best_fare": best_fare,
            "best_eta": best_eta,
            "services": services,
            "operators": operators,
            "from_code": from_code,
            "to_code": to_code,
            "rider": rider,
            "mode": mode
        }

# --- Show SQL results if available ---
if st.session_state.get("sql_results"):
    res = st.session_state["sql_results"]
    st.markdown(
        f"""
        <div class="kpi-row">
        <div class="kpi-card">
            <div class="label">Direct services</div>
            <div class="value">{res['services']}</div>
        </div>
        <div class="kpi-card">
            <div class="label">Cheapest fare</div>
            <div class="value">${res['best_fare']:.2f}</div>
        </div>
        <div class="kpi-card">
            <div class="label">Fastest ETA</div>
            <div class="value">{res['best_eta']} min</div>
        </div>
        <div class="kpi-card">
            <div class="label">Operators</div>
            <div class="value">{res['operators']}</div>
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        f"""
        <div class="meta-row">
        <div class="chip"><span class="tag">From</span>{res['from_code']}</div>
        <div class="chip"><span class="tag">To</span>{res['to_code']}</div>
        <div class="chip"><span class="tag">Rider</span>{res['rider']}</div>
        <div class="chip"><span class="tag">Mode</span>{res['mode']}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.dataframe(res["df"], hide_index=True, use_container_width=True)

# divider
st.markdown(
    '<hr style="border:0;height:1px;background:linear-gradient(90deg,transparent,#FF6BA3,transparent);margin:2rem 0;">',
    unsafe_allow_html=True
)


# --- section 2: live arrivals (NoSQL) ---
st.subheader("⏱️ Live Arrivals (NoSQL)")
db = load_nosql_data()
collection_names = list(db.list_collection_names())
if not collection_names:
    st.warning("No NoSQL collections found. Place JSON files in data/import/.")
else:
    # Always use the first collection, no selectbox
    collection_name = collection_names[0]
    collection = db[collection_name]
    # Simple query UI: filter by bus stop code
    query_type = st.radio("Query by", ["bus_stop_code"], horizontal=True)
    query = {}
    # Get all unique bus stop codes from the collection
    all_codes = collection.distinct("bus_stop_code")
    all_codes = sorted([c for c in all_codes if c])
    # Build a mapping from code to name using the SQL stops table
    stop_labels = {}
    try:
        stops_df = load_stops()
        stop_labels = dict(zip(stops_df["bus_stop_code"], stops_df["description"]))
    except Exception:
        pass
    options = [f"{code} — {stop_labels.get(code, '')}".strip() for code in all_codes]
    selected = st.selectbox("Select bus stop", options) if options else ""
    stop_code = selected.split(" — ", 1)[0] if selected else ""
    if stop_code:
        query["bus_stop_code"] = stop_code

    # Query and display

# --- Store and display NoSQL results ---
if "nosql_results" not in st.session_state:
    st.session_state["nosql_results"] = None
if st.button("Search"):
    results = list(collection.find(query))
    if results:
        display_rows = []
        for rec in results:
            service_no = rec.get("service_no", "-")
            arrivals = rec.get("arrivals", [])
            eta_list = []
            for arr in arrivals:
                eta_str = arr.get("eta")
                if eta_str:
                    try:
                        import datetime
                        t = datetime.datetime.fromisoformat(eta_str.replace("Z", "+00:00"))
                        eta_fmt = t.strftime("%H:%M")
                    except Exception:
                        eta_fmt = eta_str
                    eta_list.append(eta_fmt)
            display_rows.append({
                "Service": service_no,
                "Arrivals": ", ".join(eta_list) if eta_list else "-"
            })
        st.session_state["nosql_results"] = pd.DataFrame(display_rows)
    else:
        st.session_state["nosql_results"] = None

if st.session_state.get("nosql_results") is not None:
    st.write(f"Found {len(st.session_state['nosql_results'])} records:")
    st.dataframe(st.session_state["nosql_results"], hide_index=True)

# --- footer ---
st.markdown(
    '<hr style="border:0;height:1px;background:linear-gradient(90deg,transparent,#59C3C3,transparent);margin-top:2rem;">',
    unsafe_allow_html=True
)

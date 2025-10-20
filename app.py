# app.py
import os
import sqlite3
import pandas as pd
import streamlit as st

# ---------- Custom Modern Dolch 2 Theme CSS ----------
st.markdown("""
<style>
:root {
  --bg: #1e1f22;
  --panel: #242529;
  --panel2: #2b2d31;
  --text: #E6E6E6;
  --muted: #9aa0a6;
  --accent: #59C3C3;   /* Cyan accent */
  --accent2: #FF6BA3;  /* Pink glow accent */
}

/* ---------- Background ---------- */
[data-testid="stAppViewContainer"] > .main {
  background: linear-gradient(180deg, var(--bg), #17181b 60%);
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.8rem; }

/* ---------- Titles ---------- */
h1 {
  letter-spacing: .3px;
  margin-bottom: .5rem;
}

/* ---------- Tabs: Futuristic Rounded Buttons ---------- */
[data-testid="stTabs"] [role="tablist"] {
  gap: .5rem;
  border: 0;
  justify-content: center;
}
[data-testid="stTabs"] button[role="tab"] {
  background: var(--panel);
  color: var(--muted);
  border: 1px solid #3a3b3f;
  border-radius: 9999px; /* full pill shape */
  padding: .5rem 1rem;
  transition: all .18s ease;
  box-shadow: inset 0 -2px 0 rgba(255,255,255,.03);
  font-weight: 500;
}

/* --- Active Tab Glow --- */
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  color: var(--text)!important;
  border-color: transparent;
  background:
    radial-gradient(120% 100% at 50% 0%, rgba(255,255,255,.06), rgba(255,255,255,.03)),
    linear-gradient(135deg, var(--accent2) 0%, var(--accent) 100%);
  box-shadow:
    0 0 15px 2px rgba(255,107,163,.7),
    0 0 25px 5px rgba(255,107,163,.45),
    inset 0 1px 2px rgba(255,255,255,.15),
    0 6px 20px rgba(0,0,0,.4);
  transform: translateY(-1px);
  animation: pulse 2.5s ease-in-out infinite;
}

/* --- Pulse Animation for Active Tab --- */
@keyframes pulse {
  0%, 100% {
    box-shadow:
      0 0 15px 2px rgba(255,107,163,.5),
      0 0 25px 4px rgba(255,107,163,.3);
  }
  50% {
    box-shadow:
      0 0 25px 4px rgba(255,107,163,.85),
      0 0 40px 8px rgba(255,107,163,.55);
  }
}

/* --- Hover Effect --- */
[data-testid="stTabs"] button[role="tab"]:hover {
  color: var(--text);
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(0,0,0,.35);
}

/* ---------- Buttons ---------- */
.stButton > button {
  background: linear-gradient(180deg, var(--accent), #3aa9a9);
  color: #0d1117;
  border: none;
  border-radius: 12px;
  padding: .55rem 1rem;
  font-weight: 600;
  transition: transform .15s ease, filter .15s ease;
}
.stButton > button:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

/* ---------- Inputs ---------- */
.stSelectbox > div > div,
.stTextInput > div > div {
  background: var(--panel);
  border-radius: 12px;
  border: 1px solid #3a3b3f;
  color: var(--text);
}

/* ---------- DataFrame Container ---------- */
[data-testid="stDataFrame"] {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #303236;
}
</style>
""", unsafe_allow_html=True)

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

def main():
    st.set_page_config(page_title="Bus Direct Route Finder", layout="centered")
    st.title("Bus Route & Arrivals Demo")

    tab_sql, tab_nosql = st.tabs(["🚌 Direct Route Finder (SQL)", "⏱️ Live Arrivals (NoSQL)"])

    with tab_sql:
        st.subheader("Find direct services between two stops")
        conn = get_conn()
        stops = load_stops()

        col1, col2 = st.columns(2)
        rider = col1.selectbox("Rider type", ["adult", "senior", "student", "workfare"], index=0)
        mode  = col2.selectbox("Payment mode", ["card", "cash"], index=0)

        # Inputs with autocomplete
        col3, col4 = st.columns(2)
        start_label = col3.selectbox("From stop", stops["label"].tolist())
        end_label   = col4.selectbox("To stop",   stops["label"].tolist(), index=min(1, len(stops)-1))

        # Extract codes back
        start_code = start_label.split(" — ", 1)[0]
        end_code   = end_label.split(" — ", 1)[0]

        if st.button("Search direct routes"):
            with st.spinner("Querying..."):
                df = query_direct(conn, rider, mode, start_code, end_code)
            if df.empty:
                st.warning("No direct routes found. Try another pair.")
            else:
                # tidy columns
                df = df.rename(columns={
                    "service_no":"Service",
                    "direction":"Dir",
                    "operator":"Operator",
                    "category":"Category",
                    "from_stop":"From",
                    "to_stop":"To",
                    "hops":"Hops",
                    "travel_km":"Km",
                    "est_minutes":"ETA (min)",
                    "fare":"Fare",
                    "fare_source":"Fare source"
                })
                st.dataframe(df, use_container_width=True)

        with st.expander("Advanced"):
            st.caption("DB path: " + os.path.abspath(DB_PATH))
            st.write("Tables:", pd.read_sql_query(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", conn
            ))

    with tab_nosql:
        st.subheader("Live arrivals at a stop")
        st.info("Hook this up to MongoDB later. For now, we’ll show a simulated response shape.")
        st.code(
            """{
  "stop_id": "ST200",
  "route_no": "21",
  "updated_at": "2025-09-18T09:15:00Z",
  "arrivals": [ {"eta_min": 3, "status": "on-time"}, {"eta_min": 11} ],
  "alerts":   [ {"type": "crowd", "msg": "High load"} ]
}""",
            language="json"
        )
        st.caption("Planned: connect with pymongo, TTL index on updated_at, and a dropdown to pick stop_id.")
        st.caption("Tip: read MONGO_URI from .env and only enable this tab if it’s set.")
        
if __name__ == "__main__":
    main()

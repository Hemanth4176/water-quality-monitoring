# app/api/routes.py
from flask import Blueprint, jsonify, request
from app import db
from app.models import Station, River, State, Measurement
import pandas as pd
from utils.fig_to_base64 import fig_to_base64
from app.analysis.river_analysis import analyze_river
from app.analysis.station_analysis import station_summary
from app.analysis.forecasting import forecast_station_param

api = Blueprint("api", __name__, url_prefix="/api")

# helper to load dataframe from DB
def load_full_df():
    # query all measurements joined to station/river/state quickly via pandas.read_sql
    from app import db
    sql = """
        SELECT m.*, s.name as station, s.code as code, s.section_title, st.name as state, r.name as waterbody
        FROM measurements m
        JOIN stations s ON s.id = m.station_id
        LEFT JOIN states st ON st.id = s.state_id
        LEFT JOIN rivers r ON r.id = s.river_id
    """
    df = pd.read_sql(sql, db.engine)
    return df

@api.route("/meta")
def meta():
    df = load_full_df()
    return jsonify({
        "stations": int(df['station'].nunique()),
        "rivers": int(df['waterbody'].nunique()),
        "years": sorted(df['year'].unique().tolist())
    })

@api.route("/river/analysis")
def river_analysis_api():
    river_name = request.args.get("river")
    parameter = request.args.get("param", "pH")   # default = pH

    df = load_full_df()   # your function to load DF from DB
    res = analyze_river(df, river_name, parameter=parameter)

    return jsonify(res)


@api.route("/station/<station_name>/summary")
def station_api_summary(station_name):
    df = load_full_df()
    res = station_summary(df, station_name)
    return jsonify(res)

@api.route("/station/<station_name>/predict/<param>")
def station_predict(station_name, param):
    df = load_full_df()
    res = forecast_station_param(df, station_name, param=param, years_ahead=5)
    return jsonify(res)

@api.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    q_like = f"%{q}%"
    stations = Station.query.filter(Station.name.ilike(q_like)).limit(10).all()
    rivers = River.query.filter(River.name.ilike(q_like)).limit(10).all()
    # states = State.query.filter(State.name.ilike(q_like)).limit(10).all()
    states = (
        db.session.query(State)
        .join(Station, Station.state_id == State.id)
        .join(Measurement, Measurement.station_id == Station.id)
        .filter(State.name.ilike(f"%{q}%"))
        .distinct()
        .all()
    )
    res = []
    for s in stations:
        res.append({"type":"station","name":s.name,"id":s.id})
    for r in rivers:
        res.append({"type":"river","name":r.name})
    for st in states:
        res.append({"type":"state","name":st.name})
    return jsonify({"results":res})
# -----------------------------
# SEPARATE SEARCH ENDPOINTS
# -----------------------------

# @api.route("/search/station")
# def search_station():
#     q = request.args.get("q", "").strip()
#     if not q:
#         return jsonify({"results": []})
#     q_like = f"%{q}%"
#     from app.models import Station
#     stations = Station.query.filter(Station.name.ilike(q_like)).limit(20).all()
#     return jsonify({"results": [{"id":s.id, "name":s.name} for s in stations]})
@api.route("/search/station")
def search_station():
    from app.models import Station, Measurement

    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})

    q_like = f"%{q}%"
    stations = Station.query.filter(Station.name.ilike(q_like)).all()

    valid_results = []

    for st in stations:
        # Count measurements
        count = Measurement.query.filter_by(station_id=st.id).count()

        # Keep only stations with enough measurements for forecasting
        if count >= 3:
            valid_results.append({"id": st.id, "name": st.name})

    return jsonify({"results": valid_results})



@api.route("/search/river")
def search_river():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})

    from app.models import River, Station, Measurement

    # 🔍 Only rivers that have at least one station AND at least one measurement
    valid_rivers = (
        db.session.query(River)
        .join(Station)
        .join(Measurement)
        .distinct()
    )

    # 🔎 Filter valid rivers by search query
    results = valid_rivers.filter(River.name.ilike(f"%{q}%")).all()

    # 🧼 Prepare clean output
    return jsonify({
        "results": [{"name": r.name} for r in results]
    })


# @api.route("/search/river")
# def search_river():
#     q = request.args.get("q", "").strip()
#     q_like = f"%{q}%"
#     rivers = (
#         River.query
#             .filter(River.name.ilike(q_like))
#             .order_by(River.name.asc())
#             .all()
#     )
#     results = [{"name": r.name} for r in rivers]
#     return jsonify({"results": results})
#     # if not q:
#     #     return jsonify({"results": []})
#     # q_like = f"%{q}%"
#     # from app.models import River
#     # rivers = River.query.filter(River.name.ilike(q_like)).limit(20).all()
#     # return jsonify({"results": [{"name":r.name} for r in rivers]})


# @api.route("/search/state")
# def search_state():
#     q = request.args.get("q", "").strip()
#     if not q:
#         return jsonify({"results": []})
#     q_like = f"%{q}%"
#     from app.models import State
#     states = State.query.filter(State.name.ilike(q_like)).limit(20).all()
#     return jsonify({"results": [{"name":s.name} for s in states]})

@api.route("/search/state")
def search_state():

    from app.models import State, Station, Measurement
    q = request.args.get("q", "").strip()

    if not q or len(q) < 2:
        return jsonify({"results": []})

    valid_states = []

    states = State.query.filter(State.name.ilike(f"%{q}%")).all()

    for st in states:
        # Check if state has stations
        stations = Station.query.filter_by(state_id=st.id).all()
        if not stations:
            continue

        # Check if state has data Measurements
        has_data = (
            db.session.query(Measurement)
            .join(Station)
            .filter(Station.state_id == st.id)
            .first()
        )

        if not has_data:
            continue

        valid_states.append({"name": st.name})

    return jsonify({"results": valid_states})


@api.route("/state/<state_name>/details")
def state_details(state_name):
    df = load_full_df()

    df_state = df[df["state"].str.lower() == state_name.lower()]
    if df_state.empty:
        return jsonify({"error": "State not found"})

    rivers = sorted(df_state["waterbody"].dropna().unique().tolist())
    stations = (df_state[["station", "station_id"]].drop_duplicates().rename(columns={"station": "name", "station_id":"id"}).to_dict(orient="records"))

    return jsonify({
        "state": state_name,
        "rivers": rivers,
        "stations": stations
    })
@api.route("/river/stations")
def river_stations():
    river_name = request.args.get("river")
    stations = (
        db.session.query(Station.name)
        .join(River)
        .filter(River.name == river_name)
        .all()
    )
    return jsonify({"stations": [s[0] for s in stations]})




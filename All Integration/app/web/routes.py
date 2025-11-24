# app/web/routes.py
from flask import render_template, current_app, redirect, url_for, request
from app.web import web
from app.api.routes import load_full_df
from app import db

# @web.route("/")
# def index():
#     df = load_full_df()
#     # compute simple KPIs
#     kpis = {
#         "stations": int(df['station'].nunique()),
#         "rivers": int(df['waterbody'].nunique()),
#         "years": f"{df['year'].min()} - {df['year'].max()}"
#     }
#     return render_template("index.html", kpis=kpis)
@web.route("/")
def index():
    df = load_full_df()

    from app.models import Station, River, State, Measurement

    # Valid stations: must have measurements
    valid_station_ids = (
        db.session.query(Station.id)
        .join(Measurement, Measurement.station_id == Station.id)
        .distinct()
        .all()
    )
    valid_station_ids = [s[0] for s in valid_station_ids]

    # Count valid stations
    station_count = len(valid_station_ids)

    # Valid rivers: only those with valid stations
    valid_river_count = (
        db.session.query(River)
        .join(Station)
        .join(Measurement)
        .distinct()
        .count()
    )

    # Valid states: only those with valid stations
    valid_state_count = (
        db.session.query(State)
        .join(Station)
        .join(Measurement)
        .distinct()
        .count()
    )

    # Year range
    year_range = f"{df['year'].min()} - {df['year'].max()}"

    kpis = {
        "stations": station_count,
        "rivers": valid_river_count,
        "states": valid_state_count,
        "years": year_range
    }

    return render_template("index.html", kpis=kpis)

@web.route("/station/<int:station_id>")
def station_page(station_id):
    # find station name
    from app.models import Station
    st = Station.query.get_or_404(station_id)
    return render_template("station.html", station=st)

# @web.route("/river/<river_name>")
# def river_page(river_name):
#     from app.models import River, Station, Measurement

#     # 1️⃣ Check if river exists
#     river = River.query.filter_by(name=river_name).first()
#     if not river:
#         return render_template("not_found.html", message="River not found")

#     # 2️⃣ Check if river has stations
#     stations = Station.query.filter_by(river_id=river.id).all()
#     if not stations:
#         return render_template("not_found.html", message="No stations found for this river")

#     # 3️⃣ Check if river has measurements (real data)
#     has_data = (
#         db.session.query(Measurement)
#         .join(Station, Measurement.station_id == Station.id)
#         .filter(Station.river_id == river.id)
#         .first()
#     )
#     if not has_data:
#         return render_template("not_found.html", message="No data found for this river")

#     # ✔ Valid river → load page
#     return render_template("river.html", river_name=river_name)
@web.route("/river/<river_name>")
def river_page(river_name):
    from app.models import River, Station, Measurement

    # 1️⃣ Check if river exists
    river = River.query.filter_by(name=river_name).first()
    if not river:
        return render_template("not_found.html", message="River not found")

    # 2️⃣ Get all stations linked to the river
    stations = Station.query.filter_by(river_id=river.id).all()
    if not stations:
        return render_template("not_found.html", message="No stations found for this river")

    # 3️⃣ Filter only stations that have real measurement records
    valid_stations = []
    for st in stations:
        count = Measurement.query.filter_by(station_id=st.id).count()
        if count >= 3:  # Minimum data required for prediction
            valid_stations.append({"id": st.id, "name": st.name})

    # If NO stations have usable data → show warning
    if not valid_stations:
        return render_template("not_found.html", message="⚠ No usable station data available for forecasting this river.")

    # 4️⃣ Render river page with station dropdown included
    return render_template("river.html", river_name=river_name, stations=valid_stations)


@web.route("/predict/<int:station_id>")
def prediction_page(station_id):
    from app.models import Station
    st = Station.query.get_or_404(station_id)
    return render_template("prediction.html", station=st)

@web.route("/search_redirect")
def search_redirect():
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(url_for("web.index"))
    # attempt to find station first
    from app.models import Station, River, State
    station = Station.query.filter(Station.name.ilike(f"%{q}%")).first()
    if station:
        return redirect(url_for("web.station_page", station_id=station.id))
    river = River.query.filter(River.name.ilike(f"%{q}%")).first()
    if river:
        return redirect(url_for("web.river_page", river_name=river.name))
    # state = State.query.filter(State.name.ilike(f"%{q}%")).first()
    state = (
        db.session.query(State)
        .join(Station, Station.state_id == State.id)
        .join(Measurement, Measurement.station_id == Station.id)
        .filter(State.name.ilike(f"%{q}%"))
        .distinct()
        .first()
    )
    if state:
        return redirect(url_for("web.index"))  # you can implement /state/<name> later
    return redirect(url_for("web.index"))
# @web.route("/state/<state_name>")
# def state_page(state_name):
#     return render_template("state.html", state_name=state_name)
@web.route("/state/<state_name>")
def state_page(state_name):
    from app.models import State, Station, Measurement

    state = (
        db.session.query(State)
        .join(Station)
        .join(Measurement)
        .filter(State.name == state_name)
        .distinct()
        .first()
    )

    if not state:
        return render_template("not_found.html", message="State not found or has no data")

    return render_template("state.html", state_name=state_name)


# utils/ingest.py
import pandas as pd
from app import db
from app.models import River, State, Station, Measurement
import os
from utils.river_cleaner import clean_river_name

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CSV_PATH = os.path.join(BASE_DIR, "data", "water_quality_2016_2023.csv")

# CSV_PATH = r"C:\Users\V.Hemanth Venkat Sai\OneDrive - National Institute of Technology\Desktop\Documents\water-quality-dashboard\data\water_quality_2016_2023.csv"

# CSV_PATH = "/mnt/data/water_quality_2016_2023.csv"  # uploaded file path

def ingest(csv_path=CSV_PATH, commit=True):
    df = pd.read_csv(csv_path)
    # standardize column names
    df.columns = [c.strip() for c in df.columns]

    # Fill missing required columns safely
    df['waterbody'] = df.get('waterbody') if 'waterbody' in df else df.get('waterboday', None)

    with db.session.no_autoflush:
        # Rivers
        # ---- RIVERS ----
        cleaned_rivers = set()

        for raw_river in df['waterbody'].dropna():
            clean_name = clean_river_name(str(raw_river).strip())
            cleaned_rivers.add(clean_name)

        for river_name in cleaned_rivers:
            if not River.query.filter_by(name=river_name).first():
                db.session.add(River(name=river_name))


        # States
        for state_name in df['state'].dropna().unique():
            if not State.query.filter_by(name=state_name).first():
                db.session.add(State(name=state_name))

        db.session.commit()

        # Stations & measurements
        for _, row in df.iterrows():
            raw_name = row.get("station")
            if pd.isna(raw_name) or raw_name.strip() == "":
                station_name = f"Unknown_Station_{_}"
            else:
                station_name = str(raw_name).strip()
            river = None
            state = None
            if pd.notna(row.get('waterbody')):
                clean_river = clean_river_name(row.get('waterbody'))
                river = River.query.filter_by(name = clean_river).first()
                # river = River.query.filter_by(name=row.get('waterbody')).first()
            if pd.notna(row.get('state')):
                state = State.query.filter_by(name=row.get('state')).first()

            # try code if exists
            code = row.get('code') if 'code' in row else None
            station = None
            if code:
                station = Station.query.filter_by(code=code).first()
            if not station:
                station = Station.query.filter_by(name=station_name, river=river).first()
            if not station:
                station = Station(
                    code=code,
                    name=station_name,
                    section_title=row.get('section_title'),
                    state=state,
                    river=river
                )
                db.session.add(station)
                db.session.flush()

            # Create measurement
            try:
                year = int(row['year'])
            except Exception:
                continue
            meas = Measurement(
                station_id=station.id,
                year=year,
                pH=_safe(row.get('pH')),
                conductivity_uScm=_safe(row.get('conductivity_uScm')),
                BOD_mg_L=_safe(row.get('BOD_mg_L')),
                DO_mg_L=_safe(row.get('DO_mg_L')),
                nitrate_mg_L=_safe(row.get('nitrate_mg_L'))
            )
            db.session.add(meas)

        if commit:
            db.session.commit()

def _safe(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None

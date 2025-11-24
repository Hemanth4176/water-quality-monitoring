# app/models.py
from datetime import datetime
from app import db

class River(db.Model):
    __tablename__ = "rivers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    stations = db.relationship("Station", backref="river", lazy="dynamic")

class State(db.Model):
    __tablename__ = "states"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    stations = db.relationship("Station", backref="state", lazy="dynamic")

class Station(db.Model):
    __tablename__ = "stations"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=True)
    name = db.Column(db.String(256), nullable=False)
    section_title = db.Column(db.String(256))
    state_id = db.Column(db.Integer, db.ForeignKey("states.id"))
    river_id = db.Column(db.Integer, db.ForeignKey("rivers.id"))
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    measurements = db.relationship("Measurement", backref="station", lazy="dynamic")

class Measurement(db.Model):
    __tablename__ = "measurements"
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id"), nullable=False)
    year = db.Column(db.Integer, index=True, nullable=False)
    month = db.Column(db.Integer, nullable=True)
    pH = db.Column(db.Float)
    conductivity_uScm = db.Column(db.Float)
    BOD_mg_L = db.Column(db.Float)
    DO_mg_L = db.Column(db.Float)
    nitrate_mg_L = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

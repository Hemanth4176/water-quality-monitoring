# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()

def create_app(test_config=None):
    app = Flask(__name__, static_folder="static", template_folder="web/templates")
    app.config.from_object("app.config.Config")

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    CORS(app)

    with app.app_context():
        # Create DB tables if they don't exist
        db.create_all()

    # Register Blueprints
    from app.api.routes import api as api_bp
    from app.web.routes import web as web_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)

    return app

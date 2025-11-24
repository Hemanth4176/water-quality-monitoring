from app import create_app, db
from utils.ingest import ingest

app = create_app()

with app.app_context():
    print("Creating database tables...")
    db.create_all()       # MUST BE CALLED BEFORE ingest()

    print("Ingesting data...")
    ingest()              # Insert CSV data into tables

print("DONE! Database ready.")

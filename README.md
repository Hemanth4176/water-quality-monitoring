
#  Water Quality Monitoring Dashboard

This document explains the **code structure and purpose of every component** within the project.  
This repository represents the final integrated system including:

✔ Data extraction and cleaning  
✔ Database ingestion  
✔ REST API backend  
✔ Forecasting engine  
✔ Interactive web dashboard  

---

## Project Structure Overview

```

water-quality-dashboard/
│   run.py
│   makeDatabase.py
│   requirements.txt
│
├── app/
│   ├── **init**.py
│   ├── config.py
│   ├── models.py
│   │
│   ├── analysis/
│   │   ├── forecasting.py
│   │   ├── river_analysis.py
│   │   ├── station_analysis.py
│   │   ├── year_analysis.py
│   │   └── plots.py
│   │
│   ├── api/
│   │   ├── routes.py
│   │   └── **init**.py
│   │
│   ├── web/
│   │   ├── routes.py
│   │   ├── **init**.py
│   │   └── templates/
│   │        ├── base.html
│   │        ├── index.html
│   │        ├── station.html
│   │        ├── prediction.html
│   │        ├── river.html
│   │        ├── state.html
│   │        └── search.html
│   │
│   └── static/
│       └── js/
│            ├── search.js
│            └── site.js
│
├── data/
│   ├── water_quality_2016_2023.csv
│   └── wq.db
│
├── Data Extraction and Preprocessing/
│   ├── webscraping.py
│   ├── extract_by_section.py
│   ├── preprocess_merge.py
│   │
│   ├── Raw_pdfs/
│   ├── extracted_csv_by_section/
│   └── processed/
│
├── outputs/
│   └── river_reports/
│
└── utils/
├── ingest.py
├── fig_to_base64.py
└── river_cleaner.py

````

---

##  What Each Folder Does

| Folder | Purpose |
|--------|---------|
| `app/` | Main Flask application (API, routes, analysis and UI logic) |
| `analysis/` | ML models & graphs for forecasting and insights |
| `api/` | REST API endpoints returning JSON responses |
| `web/` | Frontend routes and user-facing templates |
| `static/` | JavaScript files used for interactive UI |
| `utils/` | Helper utilities for ingestion, cleaning, and encoding |
| `Data Extraction and Preprocessing/` | Scripts used to generate the clean dataset |
| `data/` | Final dataset and SQLite database |
| `outputs/` | Generated plots and reports |

---

##  Important Files and Their Role

###  Root Files

| File | Role |
|------|------|
| `requirements.txt` | All dependencies required to run the project |
| `run.py` | Application startup script |
| `makeDatabase.py` | Initializes the database using cleaned CSV data |

---

###  App Core

| File | Description |
|------|------------|
| `app/config.py` | Application configuration (database URI, debug mode, etc.) |
| `app/models.py` | SQLAlchemy ORM models mapping tables: River, State, Station, Measurement |
| `app/__init__.py` | Flask app factory; registers API and web blueprints |

---

###  Database & REST API

| Component | Purpose |
|----------|---------|
| `app/api/routes.py` | Defines all data-access REST endpoints (search, forecast, analysis JSON responses) |
| `utils/ingest.py` | Converts cleaned CSV dataset into database tables |

---

###  Analysis & Machine Learning

| File | Purpose |
|------|---------|
| `forecasting.py` | Linear Regression–based forecasting with confidence bounds |
| `river_analysis.py` | Generates insights and plots for any selected river |
| `station_analysis.py` | (Optional) Station-level analytics |
| `year_analysis.py` | (Optional) Time-series dataset summary |
| `plots.py` | Reusable plotting utilities (line charts, heatmaps, bar plots) |

---

###  Frontend View Layer

| Folder/File | Purpose |
|------------|---------|
| `templates/*.html` | Jinja templates for dashboard pages |
| `search.js` | AJAX search feature for station/state/river lookup |
| `site.js` | Handles dynamic plot loading, dropdown behavior, UI logic |

---

### Preprocessing & PDF Extraction Scripts

| Script | Description |
|--------|-------------|
| `webscraping.py` | Automatically downloads PDFs from CPCB portal |
| `extract_by_section.py` | Extracts station-wise measurements from PDFs |
| `preprocess_merge.py` | Standardizes, cleans, and merges yearly datasets |

---

##  Running the System

```sh
cd water-quality-dashboard
pip install -r requirements.txt
python makeDatabase.py   # optional: rebuild DB
python run.py            # launch web dashboard
````

---

### Summary

This repository implements a full data pipeline:

| Stage         | Technology                       |
| ------------- | -------------------------------- |
| Extraction    | Python + Camelot + BeautifulSoup |
| Cleaning      | Pandas + Regex                   |
| Storage       | SQLAlchemy ORM + SQLite          |
| Forecasting   | Linear Regression                |
| Visualization | Matplotlib + Seaborn + Base64    |
| Frontend      | Flask + Bootstrap + JavaScript   |

---



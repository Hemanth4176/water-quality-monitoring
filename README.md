# Water Quality Monitoring Project

This README documents the **data acquisition, extraction, preprocessing, and analysis** part of the project.  
(Backend, database, and dashboard components are documented separately.)

---

## 1. Environment Setup

Activate the virtual environment:

.\venv\Scripts\activate

Install dependencies:

cd scripts
pip install -r requirements.txt

---

## 2. Code Organization and Role of Each File

### 2.1 Top-level Structure (this module)

water-quality-monitoring/
├── data/
│ ├── raw_pdfs/ # Optional: manually downloaded PDFs
│ ├── CPCB_Rivers_Main_Data/ # NWMP river PDFs downloaded via webscraping.py
│ ├── extracted_csv_by_section/ # Per-year CSVs extracted from PDFs (raw tables)
│ └── processed/ # Cleaned & merged CSVs (per-year + master)
│
├── scripts/
│ ├── webscraping.py # Download NWMP river PDFs from CPCB website
│ ├── extract_by_section.py # Extract river/section tables from PDFs to CSV
│ ├── preprocess_merge.py # Clean, standardize, and merge yearly CSVs
│ ├── river_analysis_and_plots.py # River-wise safety analysis + plots + reports
│ ├── Extract_from_pdf.ipynb # Exploratory notebook (optional)
│ └── requirements.txt # Python dependencies for this pipeline
│
└── outputs/
└── river_reports/ # Per-river CSVs, JSON reports, and visualization PNGs

---

## 3. Commands to Run the Pipeline

From the repository root (`water-quality-monitoring/`):

1) Download NWMP river PDFs (2016–2023) into data/CPCB_Rivers_Main_Data/
python scripts/webscraping.py

2) Extract station-wise tables from PDFs into data/extracted_csv_by_section/
python scripts/extract_by_section.py

3) Clean, standardize, and merge yearly CSVs into data/processed/
python scripts/preprocess_merge.py

4) Run river-wise analysis and generate plots/reports for a river (example: Beas)
python scripts/river_analysis_and_plots.py
--data ../data/processed/water_quality_2016_2023.csv
--river "Beas"
--out-dir ../outputs/river_reports

(Adjust `--data` and paths if you run from a different working directory.)

---

## 4. `scripts/` Folder – File Roles

### 4.1 `webscraping.py`

**Role:** Data acquisition.

- Downloads NWMP river water‑quality PDF reports for a given year range from the CPCB website.
- Uses `requests`, `BeautifulSoup`, and `urllib3` to:
  - Access `https://cpcb.nic.in/nwmp-data-<year>/`.
  - Find the main “Rivers” PDF link (excluding “medium”/“minor”).
  - Save it as `data/CPCB_Rivers_Main_Data/<year>.pdf`.

---

### 4.2 `extract_by_section.py`

**Role:** PDF table extraction.

- Reads each yearly PDF in `data/CPCB_Rivers_Main_Data/` and extracts station‑wise tables.
- Uses:
  - `camelot` (both lattice and stream flavors) to extract tables.
  - `pdfminer.six` to detect section titles (river/tributary names).
- Filters valid station rows based on station-code pattern, maps raw columns to a fixed schema, and writes per‑year CSVs into:

data/extracted_csv_by_section/water_quality_by_section_<year>.csv

---

### 4.3 `preprocess_merge.py`

**Role:** Data cleaning and standardization.

- Takes the raw per‑year CSVs from `data/extracted_csv_by_section/`.
- Normalizes text (whitespace, casing).
- Converts numeric min/max columns to floats via a custom converter.
- Drops rows with no numeric data at all.
- Computes representative means for each parameter (pH, DO, BOD, conductivity, nitrate).
- Derives clean `waterbody` names using regex patterns.
- Outputs:
  - Standardized per‑year CSVs: `data/processed/water_quality_standardized_<year>.csv`
  - Single merged master file: `data/processed/water_quality_2016_2023.csv`

---

### 4.4 `river_analysis_and_plots.py`

**Role:** River‑wise analysis and visualization.

- Loads the master processed CSV.
- Performs safety assessment for a chosen river using two criteria:
  - **BIS pH gate** (pH between 6.5 and 8.5).
  - **Composite raw‑water gate** (pH, DO, BOD, fecal coliform, total coliform).
- Produces, for each analyzed river:
  - `<river>_records.csv` – all records and derived fields.
  - `<river>_latest.csv` – one latest entry per station.
  - `<river>_report.json` – summary statistics and SAFE/UNSAFE/UNKNOWN verdicts.
  - Multiple PNG plots (trends, heatmaps, compliance over time, state‑wise status, parameter correlation) stored under `outputs/river_reports/`.

---

### 4.5 `Extract_from_pdf.ipynb`

**Role:** Exploratory notebook.

- Used during development to experiment with PDF extraction and inspect tables manually.
- Not required for running the final automated pipeline (optional in submission).

---

### 4.6 `requirements.txt`

**Role:** Dependency specification.

- Lists all Python libraries needed to run the scripts:
  - Web scraping (`requests`, `beautifulsoup4`, `urllib3`)
  - PDF processing (`camelot-py`, `pdfminer.six`)
  - Data handling (`pandas`, `numpy`)
  - Plotting (`matplotlib`, `seaborn`)

---

## 5. `data/` Folder – Contents

### 5.1 `raw_pdfs/`

- Optional folder to keep any manually downloaded sample PDFs.
- Not required by the automated pipeline.

### 5.2 `CPCB_Rivers_Main_Data/`

- Destination for PDFs downloaded by `webscraping.py`.
- Contains one file per year (e.g., `2016.pdf`, `2017.pdf`, …, `2023.pdf`).

### 5.3 `extracted_csv_by_section/`

- Contains intermediate CSVs created by `extract_by_section.py`, one per year.
- Each row corresponds to a station/section with min/max values for multiple parameters.

### 5.4 `processed/`

- Contains cleaned, standardized CSVs created by `preprocess_merge.py`.
- Includes:
  - Per‑year standardized files.
  - Final merged dataset `water_quality_2016_2023.csv` used by the analysis script and by the backend team.

---

## 6. `outputs/` Folder – Contents

### 6.1 `river_reports/`

- Output location for `river_analysis_and_plots.py`.
- For each analyzed river, typically contains:
  - `<river>_records.csv` – all records used.
  - `<river>_latest.csv` – one latest entry per station.
  - `<river>_report.json` – summary statistics and safety verdicts.
  - Several PNG plots and supporting CSV files:
    - Temporal trends
    - Station–year heatmaps
    - Top 5 worst stations
    - Compliance over time
    - State‑wise compliance
    - Parameter correlation


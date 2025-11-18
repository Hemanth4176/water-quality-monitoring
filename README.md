# Water Quality Monitoring Project

Updated by Hemanth Venkata Sai
 
"# Contribution: Added preprocessing function" 
 
"Updated by VamsiKirhsnaYadav" 

"testing again for conflict

 
"# Contribution: Added preprocessing function" 
 
"Updated by Aditya" 



Temporarily allow activation
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Activating venv
.\venv\Scripts\activate

Updated python script for river reports by VamsiKrishnaYadav


commands to run the files:

python scripts/webscraping.py   saves data into CPCB_Rivers_Main_Data

python scripts/extract_by_section.py

python scripts/preprocess_merge.py

python river_analysis_and_plots.py --data ../data/processed/water_quality_2016_2023.csv --river "Beas" --out-dir ../outputs/river_reports
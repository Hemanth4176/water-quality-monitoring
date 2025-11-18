import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3

# Suppress only the single InsecureRequestWarning from urllib3 needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_main_rivers_strict(start_year, end_year):
    output_folder = "../data/CPCB_Rivers_Main_Data"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created directory: {output_folder}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for year in range(start_year, end_year + 1):
        page_url = f"https://cpcb.nic.in/nwmp-data-{year}/"
        print(f"\nProcessing Year: {year}...")
        
        try:
            # ADDED verify=False to bypass SSL error
            response = requests.get(page_url, headers=headers, verify=False)
            
            if response.status_code != 200:
                print(f"  Could not access page (Status: {response.status_code})")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a', href=True)
            
            file_found = False

            for link in links:
                href = link['href']
                
                link_text = link.get_text(strip=True).lower()
                description = ""
                parent_td = link.find_parent('td')
                if parent_td:
                    prev_td = parent_td.find_previous_sibling('td')
                    if prev_td:
                        description = prev_td.get_text(strip=True).lower()
                
                full_text = f"{link_text} {description}"

                # Strict Filter: Must have 'river' but NO 'medium' or 'minor'
                if "river" in full_text and "medium" not in full_text and "minor" not in full_text:
                    if href.lower().endswith('.pdf') or 'download' in link_text:
                        
                        full_url = urljoin("https://cpcb.nic.in/", href)
                        filename = f"{year}.pdf"
                        file_path = os.path.join(output_folder, filename)

                        print(f"  [Found Main Data] Downloading as {filename}...")
                        try:
                            # ADDED verify=False here as well
                            file_resp = requests.get(full_url, headers=headers, stream=True, verify=False)
                            
                            with open(file_path, 'wb') as f:
                                for chunk in file_resp.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            print(f"  -> Success")
                            
                            file_found = True
                            break 
                        except Exception as e:
                            print(f"  -> Failed: {e}")
            
            if not file_found:
                print(f"  No main 'Rivers' file found for {year}.")

        except Exception as e:
            print(f"  Error: {e}")

    print(f"\nAll available files saved to: {os.path.abspath(output_folder)}")

if __name__ == "__main__":
    download_main_rivers_strict(2016, 2023)
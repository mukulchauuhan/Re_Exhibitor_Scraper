`# RE+ Exhibitor Scraper`
For educational/demo purposes. Respect site terms; do not overload servers.
### Overview
This script automates scraping the RE+ exhibitor gallery and each exhibitor’s detail sub‑page to collect:
 - Company Name
 - Booth Number
 - Address, City, State, Zip, Country
 - Phone
 - Website
 - Email
 - Description
 - Detail Page URL
 - Scraped Date
It navigates the gallery, discovers detail links, and extracts scoped fields from the “Company Information” and “Booths” sections on each exhibitor page. Outputs are saved to CSV and Excel, and you can upload the CSV to Google Sheets for sharing.
### Why this approach works
- Detail-page scraping: avoids header/footer noise and captures canonical data per exhibitor.
- Website: picked from scoped links and filtered against non-company domains.
- Phone/Email: prefers tel:/mailto: then falls back to regex within the scoped block.
- Address: DOM-first selection for the left column under “Company Information” plus strict filtering to avoid URLs/phones/emails; includes heuristics to parse US formats and a robust fallback for non‑US formats.
## Features
- Automatic exhibitor link discovery from the gallery
- Robust extraction on each detail page
- CSV and Excel outputs with de-duplication by detail URL
- Tunable max exhibitors for quick samples or full runs

## Tech stack
- Python 3.10+ recommended
- Selenium + webdriver-manager
- pandas, openpyxl

## Setup
### 1) Clone and create a virtual environment`

git clone  [https://github.com/mukulchauuhan/Re_Exhibitor_Scraper.git](https://github.com/mukulchauuhan/Re_Exhibitor_Scraper.git)
cd re-exhibitor-scraper
python -m venv venv

# Windows

venv\Scripts\activate

# macOS/Linux

source venv/bin/activate

 ### 2) Install dependencies
pip install -r requirements.txt

 ## How to run
 ### Basic run

python scraper.py

 Defaults:
 - Base URL: the RE+ exhibitor gallery
 - MAX_EXHIBITORS: set in the file (e.g., 5 or 50)   To adjust:
 Open `scraper.py` and set: `MAX_EXHIBITORS = 50` for a larger sample - `scraper = REExhibitorScraper(headless=False)` to see the browser, or `True` for headless.

### Outputs
- `re_exhibitors.csv`
- `re_exhibitors.xlsx`
- You can drag-and-drop the CSV into Google Drive, open it as Google Sheets, and set “Anyone with the link” -> Viewer for submission.
## Address parsing notes
- US format:
 -- Street line is chosen from lines containing numbers/street keywords.
 -- City/State/Zip parsed from lines like “City ST 12345” or “City State 12345”.
 -- Country inferred when present (e.g., “United States of America”).
 -- Non‑US format: If no ZIP/state pattern exists, the final locality line is preserved in “City” and State/Zip remain “N/A”. - Country filled if a country line is present.

## License This project is released under the MIT License. See [LICENSE](./LICENSE).


MIT License

Copyright (c) 2025 Mukul Chauhan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the “Software”), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

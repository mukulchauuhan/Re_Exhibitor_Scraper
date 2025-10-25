from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
from datetime import datetime
import re

# Regex and Config
PHONE_RX = re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
EMAIL_RX = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
CITY_STATE_ZIP_RX = re.compile(r'([A-Za-z .]+)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)')
# Detects http/https/www or bare domains like foo.example or foo.example.com
DOMAIN_RX = re.compile(r'(?:https?://|www\.|[A-Za-z0-9-]+\.[A-Za-z]{2,})', re.IGNORECASE)
BLACKLIST = [
    "mapyourshow.com","re-plus.com","re-plus.events",
    "solarpowerinternational.com","facebook.com","twitter.com",
    "linkedin.com","instagram.com","youtube.com"
]

def normalize_phone(s: str) -> str:
    if not s or not isinstance(s, str):
        return "N/A"
    digits = re.sub(r"[^\d+]", "", s)
    m = re.search(r"(?:\+?1)?(\d{10})$", digits)
    if m:
        d = m.group(1)
        return f"+1-{d[0:3]}-{d[3:6]}-{d[6:]}"
    return digits if digits else "N/A"

# Scraper Class
class REExhibitorScraper:
    """
    Scraper for RE+ Event Exhibitor Data from MapYourShow Platform
    """

    def __init__(self, headless=False):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 12)
        self.exhibitors_data = []

    # Gallery Links
    def get_exhibitor_links(self, base_url, max_exhibitors=100):
        print("Opening exhibitor gallery page....")
        self.driver.get(base_url)
        time.sleep(2.5)

        exhibitor_links = []
        try:
            print("Waiting for exhibitor cards to load...")
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='exhibitor-details']"))
            )

            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts, max_scrolls = 0, 10

            while scroll_attempts < max_scrolls:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
                print(f"Scrolling... attempt {scroll_attempts}")

            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='exhibitor-details']")
            for link in links:
                href = link.get_attribute("href")
                if href and href not in exhibitor_links:
                    exhibitor_links.append(href)
                if len(exhibitor_links) >= max_exhibitors:
                    break
            print(f"Found {len(exhibitor_links)} exhibitor links")
        except Exception as e:
            print(f"Error getting exhibitor links: {e}")

        return exhibitor_links

    # Detail Page
    def scrape_exhibitor_details(self, url):
        data = {
            'Company Name': 'N/A', 'Booth Number': 'N/A', 'Address': 'N/A',
            'City': 'N/A', 'State': 'N/A', 'Zip': 'N/A', 'Country': 'N/A',
            'Phone': 'N/A', 'Website': 'N/A', 'Email': 'N/A', 'Description': 'N/A',
            'Detail Page URL': url, 'Scraped Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        self.driver.get(url)
        time.sleep(0.6)

        # 1) Company Name
        try:
            name_el = WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "h1, h1.exhibitor-name, .exhibitor-name h1, .company-name"))
            )
            name = (name_el.text or "").strip()
            if not name:
                name = self.driver.execute_script(
                    "return document.querySelector(\"meta[property='og:title']\")?.content || '';"
                ) or ""
            data["Company Name"] = name.strip() or "N/A"
        except Exception:
            pass

        # Scoping a "Company Information" container
        info_section = None
        for sel in [
            "section:has(h2:contains('Company Information'))",
            ".contact-info", ".company-info", "[class*='company']",
            "[class*='contact']", "[class*='address']"
        ]:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                if el and el.text.strip():
                    info_section = el
                    break
            except Exception:
                continue
        if not info_section:
            try:
                info_section = self.driver.find_element(By.XPATH, "//h2[contains(., 'Company Information')]/following-sibling::*[1]")
            except Exception:
                try:
                    info_section = self.driver.find_element(By.CSS_SELECTOR, "main, #content, .mys_content, body")
                except Exception:
                    info_section = self.driver.find_element(By.TAG_NAME, "body")

        # Left column as they are present in the left column of the website
        try:
            left_col = info_section.find_element(By.XPATH, ".//..//div[1]")
        except Exception:
            left_col = info_section
        scope_for_text = left_col

        # Finding the main 'Company Information' container with multiple fallback strategies
        info_section = None

        # Strategy 1: XPath for h2 with "Company Information"
        try:
            info_section = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'Company Information')]/following-sibling::div[1]")
        except NoSuchElementException:
            pass

        # Strategy 2: Try different XPath patterns
        if info_section is None:
            try:
                info_section = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Company Information')]/following-sibling::*[1]")
            except NoSuchElementException:
                pass

        # Strategy 3: Common class names
        if info_section is None:
            try:
                info_section = self.driver.find_element(By.CSS_SELECTOR, ".contact-info")
            except NoSuchElementException:
                pass

        # Strategy 4: More class patterns
        if info_section is None:
            try:
                info_section = self.driver.find_element(By.CSS_SELECTOR, ".company-info")
            except NoSuchElementException:
                pass

        # Strategy 5: Looking for any section containing address patterns
        if info_section is None:
            try:
                info_section = self.driver.find_element(By.XPATH, "//div[contains(., 'United States') or contains(., 'USA')]")
            except NoSuchElementException:
                pass

        # Strategy 6: Using body as last resort
        if info_section is None:
            info_section = self.driver.find_element(By.TAG_NAME, "body")
            print("  Warning: Using body as fallback for info section")

        # Left column scope used by other fields
        try:
            left_col = info_section.find_element(By.XPATH, ".//..//div[1]")
        except Exception:
            left_col = info_section
        scope_for_text = left_col

        # 2) Extract Address, City, State, Zip, Country
        try:
            # Starting with broad text approach
            address_text = (info_section.text or "").strip()
            lines = [ln.strip() for ln in address_text.splitlines() if ln.strip()]

            # Hard filter: drop lines that are clearly not postal
            filtered = []
            for ln in lines:
                if re.search(r'(?:https?://|www\.|[A-Za-z0-9-]+\.[A-Za-z]{2,})', ln, re.IGNORECASE):  # bare domains too
                    continue
                if EMAIL_RX.search(ln) or PHONE_RX.search(ln):
                    continue
                if ln.lower() in {"company information", "contact us", "contact"}:
                    continue
                filtered.append(ln)

            # If broad parse is too noisy or empty, fall back to the first column under the header (precise DOM target)
            if not filtered:
                try:
                    precise_el = self.driver.find_element(
                        By.XPATH,
                        "//h2[contains(., 'Company Information')]/following-sibling::*[1]//div[1]"
                    )
                    address_text = (precise_el.text or "").strip()
                    filtered = [ln.strip() for ln in address_text.splitlines() if ln.strip()]
                except Exception:
                    filtered = []

            # Applying address heuristics on the filtered list
            if filtered:
                # Country usually present at last
                last = filtered[-1]
                if re.match(r"^[A-Za-z .]+$", last) and ("united" in last.lower() or "america" in last.lower() or len(last.split()) >= 2):
                    data["Country"] = last
                    core = filtered[:-1]
                else:
                    core = filtered

                # Choose street line: starts with number or contains street markers
                street = None
                for ln in core:
                    if re.search(r"\d", ln) or re.search(r"(Street|St\.|Ave|Road|Rd\.|Blvd|Suite|Ste\.|Level|Floor|Drive|Dr\.|Lane|Ln\.|Court|Ct\.)", ln, re.IGNORECASE):
                        street = ln
                        break
                if not street and core:
                    street = core[0]
                if street:
                    data["Address"] = street

                # City/State/Zip: scan last two core lines for 2-letter or long-form state names
                locality_candidates = core[-2:] if len(core) >= 2 else core
                for ln in locality_candidates:
                    m = re.search(r"([A-Za-z .]+?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)", ln)
                    if m:
                        data["City"], data["State"], data["Zip"] = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
                        break
                    m2 = re.search(r"([A-Za-z .]+?)\s+([A-Za-z]{3,})\s+(\d{5}(?:-\d{4})?)", ln)
                    if m2:
                        data["City"], data["State"], data["Zip"] = m2.group(1).strip(), m2.group(2).strip(), m2.group(3).strip()
                        break
        except Exception as e:
            print(f"  Warning: Could not parse address - {e}")


        # 3) Website (scoped + blacklist + trailing dot trim)
        try:
            links = scope_for_text.find_elements(By.CSS_SELECTOR, "a[href^='http']")
            for a in links:
                href = (a.get_attribute("href") or "").strip()
                if href and not any(b in href for b in BLACKLIST):
                    data["Website"] = href.rstrip(".")
                    break
        except Exception:
            pass

        # 4) Phone (tel: then regex)
        try:
            phone_el = info_section.find_element(By.CSS_SELECTOR, "a[href^='tel:']")
            tel_raw = phone_el.get_attribute("href")
            if tel_raw:
                data["Phone"] = normalize_phone(tel_raw.replace("tel:", ""))
        except Exception:
            try:
                m = PHONE_RX.search(info_section.text)
                if m:
                    data["Phone"] = normalize_phone(m.group(0))
            except Exception:
                pass

        # 5) Email (mailto: then regex)
        try:
            mail = info_section.find_element(By.CSS_SELECTOR, "a[href^='mailto:']").get_attribute("href")
            data["Email"] = (mail or "").replace("mailto:", "").strip() or "N/A"
        except Exception:
            try:
                m = EMAIL_RX.search(info_section.text)
                if m:
                    data["Email"] = m.group(0)
            except Exception:
                pass

        # 6) Booth Number (code)
        try:
            booth_txt = ""
            try:
                booths_card = self.driver.find_element(By.XPATH, "//*[contains(., 'Booths')]/ancestor::*[self::div or self::section][1]")
                booth_link = booths_card.find_element(By.XPATH, ".//a[contains(@href,'floorplan')]")
                booth_txt = (booth_link.text or "").strip()
            except Exception:
                booth_link = self.driver.find_element(By.XPATH, "//a[contains(@href,'floorplan')]")
                booth_txt = (booth_link.text or "").strip()
            m = re.search(r"\b([A-Z]\d{4,5})\b", booth_txt)
            if m:
                data["Booth Number"] = m.group(1)
            else:
                if "—" in booth_txt:
                    data["Booth Number"] = booth_txt.split("—")[-1].strip()
        except Exception:
            pass

        # 7) Description
        for sel in [".description", ".company-description", "[class*='description']"]:
            try:
                desc_el = self.driver.find_element(By.CSS_SELECTOR, sel)
                txt = (desc_el.text or "").strip()
                if txt:
                    data["Description"] = txt[:500]
                    break
            except Exception:
                continue

        print(f"Scraped {data['Company Name']} | Website: {data['Website']} | Phone: {data['Phone']} | Address: {data['Address']}")
        return data

    # Orchestration
    def scrape_all(self, base_url, max_exhibitors=100):
        print("=" * 60)
        print("RE+ EXHIBITOR SCRAPER")
        print("=" * 60)

        exhibitor_links = self.get_exhibitor_links(base_url, max_exhibitors)
        if not exhibitor_links:
            print("No exhibitor links found!")
            return []

        print(f"\nStarting to scrape {len(exhibitor_links)} exhibitors....")
        print("=" * 60)
        for idx, link in enumerate(exhibitor_links, 1):
            print(f"\n[{idx}/{len(exhibitor_links)}] Processing: {link}")
            data = self.scrape_exhibitor_details(link)
            self.exhibitors_data.append(data)
            time.sleep(0.8)

        print("\n" + "=" * 60)
        print(f"Scraping complete! Total: {len(self.exhibitors_data)} exhibitors")
        print("=" * 60)
        return self.exhibitors_data

    # Saving in different formats
    def save_to_csv(self, filename="re_exhibitors.csv"):
        df = pd.DataFrame(self.exhibitors_data)
        if 'Detail Page URL' in df.columns:
            df = df.drop_duplicates(subset='Detail Page URL', keep='first')
        df = df.sort_values(['Company Name','Detail Page URL'])
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"\nData saved successfully to: {filename}")
        return df

    def save_to_excel(self, filename="re_exhibitors.xlsx"):
        df = pd.DataFrame(self.exhibitors_data)
        if 'Detail Page URL' in df.columns:
            df = df.drop_duplicates(subset='Detail Page URL', keep='first')
        df = df.sort_values(['Company Name', 'Detail Page URL'])
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Exhibitors")
        print(f"Data saved to: {filename}")
        return df

    # Closing
    def close(self):
        self.driver.quit()
        print("\nBrowser Closed!")

# Main
if __name__ == "__main__":
    BASE_URL = "https://re25.mapyourshow.com/8_0/explore/exhibitor-gallery.cfm?featured=false"
    MAX_EXHIBITORS = 10

    scraper = REExhibitorScraper(headless=False)
    try:
        data = scraper.scrape_all(BASE_URL, MAX_EXHIBITORS)
        df = scraper.save_to_csv("re_exhibitors.csv")
        scraper.save_to_excel("re_exhibitors.xlsx")

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total exhibitors scraped: {len(df)}")
        print(f"Companies with websites: {df['Website'].ne('N/A').sum()}")
        print(f"Companies with phone: {df['Phone'].ne('N/A').sum()}")
        print(f"Companies with email: {df['Email'].ne('N/A').sum()}")
        print("\nFirst 5 companies:")
        print(df[["Company Name", "Booth Number", "Website"]].head())
    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

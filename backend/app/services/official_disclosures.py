"""Official government disclosure scrapers for House and Senate stock trades.

Sources:
- House: disclosures-clerk.house.gov/FinancialDisclosure
- Senate: efdsearch.senate.gov

These scrapers use Selenium WebDriver to access JavaScript-heavy official
government sources, providing authoritative and current data on congressional
stock trades.
"""

import os
import asyncio
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def init_driver():
    """Initialize headless Chrome WebDriver for Railway environment."""
    service = Service(os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
    options = Options()

    # Headless mode for server environment
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--window-size=1920,1080")

    # User agent to appear as normal browser
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )

    # Set Chrome binary location from environment
    chrome_bin = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/chromium")
    if os.path.exists(chrome_bin):
        options.binary_location = chrome_bin

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver


class SenateDisclosureScraper:
    """Scraper for Senate Electronic Financial Disclosure (EFD) system.

    The Senate EFD system at efdsearch.senate.gov provides periodic transaction
    reports (PTRs) filed by senators. This scraper uses Selenium to:
    1. Accept the usage agreement
    2. Search for PTRs via the search form
    3. Parse individual PTR pages for transaction details
    """

    BASE_URL = "https://efdsearch.senate.gov"
    SEARCH_URL = f"{BASE_URL}/search/"
    REPORT_URL = f"{BASE_URL}/search/view/ptr/"

    def _accept_agreement_and_search(
        self,
        driver: webdriver.Chrome,
        start_date: str,
        end_date: str
    ) -> list[dict]:
        """Accept agreement and search for PTRs using Selenium."""
        results = []

        try:
            # Navigate to search page
            print(f"Senate: Navigating to {self.SEARCH_URL}")
            driver.get(self.SEARCH_URL)
            print(f"Senate: Current URL after navigation: {driver.current_url}")

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print(f"Senate: Page loaded, title: {driver.title}")

            # Check for and accept the agreement checkbox
            try:
                agreement_checkbox = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "agree_statement"))
                )
                print("Senate: Found agreement checkbox")
                if not agreement_checkbox.is_selected():
                    agreement_checkbox.click()
                    print("Senate: Clicked agreement checkbox")

                # Click the button to submit agreement (it's type="button" not submit)
                # Find the button - it's the only button on the page
                buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"Senate: Found {len(buttons)} buttons")
                clicked = False
                for btn in buttons:
                    btn_type = btn.get_attribute("type")
                    btn_class = btn.get_attribute("class")
                    btn_text = btn.text
                    print(f"Senate: Button type={btn_type}, class={btn_class}, text={btn_text}")
                    if btn_type == "button":
                        # Try regular click first
                        try:
                            btn.click()
                            print("Senate: Clicked agreement button (regular click)")
                            clicked = True
                        except Exception as click_err:
                            print(f"Senate: Regular click failed: {click_err}")
                            # Try JavaScript click as fallback
                            driver.execute_script("arguments[0].click();", btn)
                            print("Senate: Clicked agreement button (JS click)")
                            clicked = True
                        break
                if not clicked:
                    print("Senate: Warning - no button was clicked")

                # Wait for search page to load after agreement
                import time
                time.sleep(2)  # Give page time to transition
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "filer_type"))
                )
                print("Senate: Search form loaded after agreement")
                print(f"Senate: Current URL after agreement: {driver.current_url}")
            except TimeoutException as te:
                # Agreement may already be accepted or not present
                print(f"Senate: Agreement timeout: {te}")
                print(f"Senate: Current URL: {driver.current_url}")
                # Check if we're already on the search page
                if "filer_type" in driver.page_source:
                    print("Senate: Already on search page")
                else:
                    print("Senate: Not on search page, page source snippet:")
                    print(driver.page_source[:500])

            # Fill in search form
            try:
                # Select filer type (Senator)
                filer_type = driver.find_element(By.ID, "filer_type")
                filer_type.send_keys("1")  # 1 = Senator
                print("Senate: Set filer_type to Senator")

                # Select report type (Periodic Transaction Report)
                report_type = driver.find_element(By.ID, "report_type")
                report_type.send_keys("11")  # 11 = PTR
                print("Senate: Set report_type to PTR")

                # Set date range
                start_date_input = driver.find_element(By.ID, "submitted_start_date")
                start_date_input.clear()
                start_date_input.send_keys(start_date)
                print(f"Senate: Set start_date to {start_date}")

                end_date_input = driver.find_element(By.ID, "submitted_end_date")
                end_date_input.clear()
                end_date_input.send_keys(end_date)
                print(f"Senate: Set end_date to {end_date}")

                # Submit search
                search_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-primary")
                search_btn.click()
                print("Senate: Clicked search button")

                # Wait for results table
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "filedReports"))
                )
                print("Senate: Results table found")

                # Give the DataTable time to populate
                import time
                time.sleep(2)

                # Parse results table
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                table = soup.find('table', {'id': 'filedReports'})
                print(f"Senate: Table found: {table is not None}")

                if table:
                    tbody = table.find('tbody')
                    print(f"Senate: Tbody found: {tbody is not None}")
                    if tbody:
                        rows = tbody.find_all('tr')
                        print(f"Senate: Found {len(rows)} rows in tbody")
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) >= 4:
                                # Extract link to PTR
                                link = cells[0].find('a')
                                ptr_url = None
                                if link:
                                    href = link.get('href', '')
                                    if href.startswith('/'):
                                        ptr_url = f"{self.BASE_URL}{href}"
                                    else:
                                        ptr_url = href

                                results.append({
                                    'name': cells[0].get_text(strip=True),
                                    'office': cells[1].get_text(strip=True),
                                    'report_type': cells[2].get_text(strip=True),
                                    'date': cells[3].get_text(strip=True),
                                    'url': ptr_url
                                })
                    else:
                        # Try looking for rows in the table directly
                        all_rows = table.find_all('tr')
                        print(f"Senate: Total rows in table: {len(all_rows)}")
                        # Check page source snippet for debugging
                        page_src = driver.page_source
                        if "No matching records" in page_src:
                            print("Senate: 'No matching records' found in page")
                        print(f"Senate: Page source length: {len(page_src)}")

                print(f"Senate: Found {len(results)} PTRs")

            except Exception as e:
                import traceback
                print(f"Senate: Error during search: {e}")
                print(f"Senate: Traceback: {traceback.format_exc()}")

        except Exception as e:
            print(f"Error accessing Senate EFD site: {e}")

        return results

    def _parse_ptr_page(self, driver: webdriver.Chrome, url: str, senator_name: str) -> list[dict]:
        """Parse a single PTR page to extract transactions."""
        transactions = []

        try:
            driver.get(url)

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Find transaction tables
            tables = soup.find_all('table', class_='table')

            for table in tables:
                # Check if this looks like a transaction table
                headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]

                if any('transaction' in h or 'asset' in h or 'ticker' in h for h in headers):
                    rows = table.find_all('tr')

                    for row in rows[1:]:  # Skip header
                        cells = row.find_all('td')
                        if len(cells) >= 5:
                            tx = self._parse_transaction_row(cells, senator_name, url)
                            if tx:
                                transactions.append(tx)

        except Exception as e:
            print(f"Error parsing Senate PTR page: {e}")

        return transactions

    def _parse_transaction_row(self, cells: list, senator_name: str, filing_url: str) -> Optional[dict]:
        """Parse a single transaction row from the PTR table."""
        try:
            # Expected columns: Transaction Date, Owner, Ticker, Asset Name, Type, Amount
            tx_date = cells[0].get_text(strip=True) if len(cells) > 0 else None
            owner = cells[1].get_text(strip=True) if len(cells) > 1 else None
            ticker = cells[2].get_text(strip=True) if len(cells) > 2 else None
            asset_name = cells[3].get_text(strip=True) if len(cells) > 3 else None
            tx_type = cells[4].get_text(strip=True) if len(cells) > 4 else None
            amount = cells[5].get_text(strip=True) if len(cells) > 5 else None

            if not tx_date or not asset_name:
                return None

            parsed_date = self._parse_date(tx_date)

            return {
                "representative": senator_name,
                "chamber": "senate",
                "transaction_date": parsed_date,
                "disclosure_date": parsed_date,  # Will be overwritten if filing date known
                "owner": owner,
                "ticker": ticker if ticker and ticker != "--" else None,
                "asset_description": asset_name,
                "transaction_type": self._normalize_type(tx_type),
                "amount_range": amount,
                "amount_min": self._parse_amount_min(amount),
                "amount_max": self._parse_amount_max(amount),
                "filing_url": filing_url,
            }
        except Exception:
            return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format."""
        if not date_str:
            return None

        for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"]:
            try:
                return datetime.strptime(date_str, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    def _normalize_type(self, tx_type: str) -> str:
        """Normalize transaction type."""
        if not tx_type:
            return "unknown"

        tx_lower = tx_type.lower()
        if "purchase" in tx_lower or "buy" in tx_lower:
            return "purchase"
        elif "sale" in tx_lower or "sell" in tx_lower:
            return "sale"
        elif "exchange" in tx_lower:
            return "exchange"
        return "unknown"

    def _parse_amount_min(self, amount: str) -> Optional[int]:
        """Parse minimum amount from range."""
        if not amount:
            return None

        amount_ranges = {
            "$1,001 - $15,000": 1001,
            "$15,001 - $50,000": 15001,
            "$50,001 - $100,000": 50001,
            "$100,001 - $250,000": 100001,
            "$250,001 - $500,000": 250001,
            "$500,001 - $1,000,000": 500001,
            "$1,000,001 - $5,000,000": 1000001,
        }

        for range_str, min_val in amount_ranges.items():
            if range_str.lower() in amount.lower():
                return min_val
        return None

    def _parse_amount_max(self, amount: str) -> Optional[int]:
        """Parse maximum amount from range."""
        if not amount:
            return None

        amount_ranges = {
            "$1,001 - $15,000": 15000,
            "$15,001 - $50,000": 50000,
            "$50,001 - $100,000": 100000,
            "$100,001 - $250,000": 250000,
            "$250,001 - $500,000": 500000,
            "$500,001 - $1,000,000": 1000000,
            "$1,000,001 - $5,000,000": 5000000,
        }

        for range_str, max_val in amount_ranges.items():
            if range_str.lower() in amount.lower():
                return max_val
        return None

    def _sync_get_recent_transactions(self, days: int = 90, limit: int = 100) -> list[dict]:
        """Synchronous method to get recent Senate transactions."""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%m/%d/%Y")
        end_date = datetime.now().strftime("%m/%d/%Y")
        all_transactions = []
        driver = None

        try:
            driver = init_driver()

            # Search for PTRs
            ptrs = self._accept_agreement_and_search(driver, start_date, end_date)

            # Process each PTR
            for i, ptr in enumerate(ptrs[:limit]):
                try:
                    if ptr.get('url'):
                        transactions = self._parse_ptr_page(
                            driver,
                            ptr['url'],
                            ptr.get('name', '')
                        )

                        # Add disclosure date from PTR filing date
                        filing_date = self._parse_date(ptr.get('date'))
                        for tx in transactions:
                            if filing_date:
                                tx['disclosure_date'] = filing_date

                        all_transactions.extend(transactions)

                        # Rate limiting
                        import time
                        time.sleep(1.0)

                except Exception as e:
                    print(f"Error processing Senate PTR {i}: {e}")
                    continue

        except Exception as e:
            print(f"Senate scraper error: {e}")
        finally:
            if driver:
                driver.quit()

        print(f"Retrieved {len(all_transactions)} Senate transactions")
        return all_transactions

    async def get_recent_transactions(self, days: int = 90, limit: int = 100) -> list[dict]:
        """Get recent Senate transactions from official source.

        Args:
            days: Number of days to look back
            limit: Maximum number of PTRs to process

        Returns:
            List of transaction dictionaries
        """
        # Run synchronous Selenium code in thread pool
        return await asyncio.to_thread(
            self._sync_get_recent_transactions, days, limit
        )


class HouseDisclosureScraper:
    """Scraper for House Financial Disclosure system.

    The House disclosure system at disclosures-clerk.house.gov provides
    financial disclosure reports including PTRs. This scraper uses Selenium to:
    1. Search the financial disclosure database
    2. Download and parse PTR pages
    3. Extract transaction details
    """

    BASE_URL = "https://disclosures-clerk.house.gov"
    SEARCH_URL = f"{BASE_URL}/FinancialDisclosure"

    def _search_and_get_ptrs(
        self,
        driver: webdriver.Chrome,
        filing_year: int
    ) -> list[dict]:
        """Search for House PTRs using Selenium."""
        results = []

        try:
            # Navigate to search page
            driver.get(self.SEARCH_URL)

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Look for search form and fill it
            try:
                # Select filing year
                year_select = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "FilingYear"))
                )
                year_select.send_keys(str(filing_year))

                # Select report type (PTR)
                # The form might have different element IDs
                try:
                    report_type = driver.find_element(By.ID, "ReportType")
                    report_type.send_keys("P")  # P for Periodic Transaction
                except NoSuchElementException:
                    pass

                # Submit search
                search_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
                search_btn.click()

                # Wait for results
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "library-table"))
                )

            except TimeoutException:
                print("Timeout waiting for House search form/results")
                return []

            # Parse results from page
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table', class_='library-table')

            if table:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        # Extract member info and report link
                        name_cell = cells[0]
                        link = name_cell.find('a')

                        if link:
                            href = link.get('href', '')
                            full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"

                            results.append({
                                "name": name_cell.get_text(strip=True),
                                "office": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                                "filing_year": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                                "report_type": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                                "url": full_url,
                            })

            # Check for pagination and get more results
            while True:
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "a.next, .pagination .next a")
                    next_btn.click()

                    WebDriverWait(driver, 10).until(
                        EC.staleness_of(table) if table else EC.presence_of_element_located((By.CLASS_NAME, "library-table"))
                    )

                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    table = soup.find('table', class_='library-table')

                    if table:
                        rows = table.find_all('tr')
                        for row in rows[1:]:
                            cells = row.find_all('td')
                            if len(cells) >= 4:
                                name_cell = cells[0]
                                link = name_cell.find('a')
                                if link:
                                    href = link.get('href', '')
                                    full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                                    results.append({
                                        "name": name_cell.get_text(strip=True),
                                        "office": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                                        "filing_year": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                                        "report_type": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                                        "url": full_url,
                                    })
                except (NoSuchElementException, TimeoutException):
                    break

            print(f"Found {len(results)} House reports for {filing_year}")

        except Exception as e:
            print(f"Error searching House disclosures: {e}")

        return results

    def _parse_ptr_page(self, driver: webdriver.Chrome, url: str, member_name: str) -> list[dict]:
        """Parse a House PTR page to extract transactions."""
        transactions = []

        try:
            driver.get(url)

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check if this redirected to a PDF
            if url.lower().endswith('.pdf') or 'pdf' in driver.current_url.lower():
                print(f"Skipping PDF: {url}")
                return []

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Find transaction tables
            tables = soup.find_all('table')

            for table in tables:
                # Look for transaction-related headers
                headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]

                if any('transaction' in h or 'asset' in h for h in headers):
                    rows = table.find_all('tr')

                    for row in rows[1:]:  # Skip header
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            tx = self._parse_house_transaction(cells, member_name, url)
                            if tx:
                                transactions.append(tx)

        except Exception as e:
            print(f"Error parsing House PTR: {e}")

        return transactions

    def _parse_house_transaction(self, cells: list, member_name: str, filing_url: str) -> Optional[dict]:
        """Parse a House transaction row."""
        try:
            # Column order can vary, but typically:
            # Asset, Transaction Type, Date, Amount, etc.
            asset = cells[0].get_text(strip=True) if len(cells) > 0 else ""
            tx_type = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            tx_date = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            amount = cells[3].get_text(strip=True) if len(cells) > 3 else ""

            if not asset:
                return None

            # Extract ticker from asset description
            ticker = self._extract_ticker(asset)
            parsed_date = self._parse_date(tx_date)

            return {
                "representative": member_name,
                "chamber": "house",
                "transaction_date": parsed_date,
                "disclosure_date": parsed_date,
                "ticker": ticker,
                "asset_description": asset,
                "transaction_type": self._normalize_type(tx_type),
                "amount_range": amount,
                "amount_min": self._parse_amount_min(amount),
                "amount_max": self._parse_amount_max(amount),
                "filing_url": filing_url,
            }
        except Exception:
            return None

    def _extract_ticker(self, asset: str) -> Optional[str]:
        """Extract stock ticker from asset description."""
        patterns = [
            r'\(([A-Z]{1,5})\)',
            r'\[([A-Z]{1,5})\]',
            r'^([A-Z]{1,5})\s*[-–—]',
            r'^([A-Z]{1,5})\s+',
        ]

        for pattern in patterns:
            match = re.search(pattern, asset)
            if match:
                return match.group(1)
        return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format."""
        if not date_str:
            return None

        for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y"]:
            try:
                return datetime.strptime(date_str, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    def _normalize_type(self, tx_type: str) -> str:
        """Normalize transaction type."""
        if not tx_type:
            return "unknown"

        tx_lower = tx_type.lower()
        if "purchase" in tx_lower or "buy" in tx_lower or "p" == tx_lower:
            return "purchase"
        elif "sale" in tx_lower or "sell" in tx_lower or "s" == tx_lower:
            return "sale"
        elif "exchange" in tx_lower:
            return "exchange"
        return "unknown"

    def _parse_amount_min(self, amount: str) -> Optional[int]:
        """Parse minimum amount from range."""
        if not amount:
            return None

        amount_ranges = {
            "$1,001 - $15,000": 1001,
            "$15,001 - $50,000": 15001,
            "$50,001 - $100,000": 50001,
            "$100,001 - $250,000": 100001,
            "$250,001 - $500,000": 250001,
            "$500,001 - $1,000,000": 500001,
            "$1,000,001 - $5,000,000": 1000001,
        }

        for range_str, min_val in amount_ranges.items():
            if range_str.lower() in amount.lower():
                return min_val
        return None

    def _parse_amount_max(self, amount: str) -> Optional[int]:
        """Parse maximum amount from range."""
        if not amount:
            return None

        amount_ranges = {
            "$1,001 - $15,000": 15000,
            "$15,001 - $50,000": 50000,
            "$50,001 - $100,000": 100000,
            "$100,001 - $250,000": 250000,
            "$250,001 - $500,000": 500000,
            "$500,001 - $1,000,000": 1000000,
            "$1,000,001 - $5,000,000": 5000000,
        }

        for range_str, max_val in amount_ranges.items():
            if range_str.lower() in amount.lower():
                return max_val
        return None

    def _sync_get_recent_transactions(self, years: list[int] = None, limit: int = 100) -> list[dict]:
        """Synchronous method to get recent House transactions."""
        if not years:
            current_year = datetime.now().year
            years = [current_year, current_year - 1]

        all_transactions = []
        driver = None

        try:
            driver = init_driver()

            for year in years:
                print(f"Searching House disclosures for {year}...")

                # Search for PTRs
                results = self._search_and_get_ptrs(driver, year)

                # Filter for PTRs only
                ptrs = [r for r in results if 'ptr' in r.get('report_type', '').lower()
                        or 'periodic' in r.get('report_type', '').lower()
                        or 'transaction' in r.get('report_type', '').lower()]

                print(f"Found {len(ptrs)} House PTRs for {year}")

                # Process each PTR
                for i, ptr in enumerate(ptrs[:limit]):
                    try:
                        transactions = self._parse_ptr_page(
                            driver,
                            ptr['url'],
                            ptr['name']
                        )
                        all_transactions.extend(transactions)

                        # Rate limiting
                        import time
                        time.sleep(0.5)

                    except Exception as e:
                        print(f"Error processing House PTR {i}: {e}")
                        continue

        except Exception as e:
            print(f"House scraper error: {e}")
        finally:
            if driver:
                driver.quit()

        print(f"Retrieved {len(all_transactions)} House transactions")
        return all_transactions

    async def get_recent_transactions(self, years: list[int] = None, limit: int = 100) -> list[dict]:
        """Get recent House transactions from official source.

        Args:
            years: Filing years to search (default: current and previous year)
            limit: Maximum number of reports to process per year

        Returns:
            List of transaction dictionaries
        """
        # Run synchronous Selenium code in thread pool
        return await asyncio.to_thread(
            self._sync_get_recent_transactions, years, limit
        )


class OfficialDisclosureClient:
    """Combined client for both House and Senate official disclosures."""

    def __init__(self):
        self.senate_scraper = SenateDisclosureScraper()
        self.house_scraper = HouseDisclosureScraper()

    async def get_all_transactions(self, days: int = 90, limit_per_source: int = 50) -> list[dict]:
        """Get transactions from both House and Senate official sources.

        Args:
            days: Number of days to look back
            limit_per_source: Maximum PTRs to process per source

        Returns:
            Combined list of all transactions
        """
        all_transactions = []

        # Get Senate transactions
        try:
            senate_txs = await self.senate_scraper.get_recent_transactions(
                days=days,
                limit=limit_per_source
            )
            all_transactions.extend(senate_txs)
        except Exception as e:
            print(f"Senate scraper failed: {e}")

        # Get House transactions
        try:
            house_txs = await self.house_scraper.get_recent_transactions(
                limit=limit_per_source
            )
            all_transactions.extend(house_txs)
        except Exception as e:
            print(f"House scraper failed: {e}")

        return all_transactions

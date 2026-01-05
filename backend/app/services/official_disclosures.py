"""Official government disclosure scrapers for House and Senate stock trades.

Sources:
- House: disclosures-clerk.house.gov/FinancialDisclosure
- Senate: efdsearch.senate.gov

These scrapers access the official government sources directly, providing
authoritative and current data on congressional stock trades.
"""

import httpx
import asyncio
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential


class SenateDisclosureScraper:
    """Scraper for Senate Electronic Financial Disclosure (EFD) system.

    The Senate EFD system at efdsearch.senate.gov provides periodic transaction
    reports (PTRs) filed by senators. This scraper:
    1. Establishes a session and gets CSRF token
    2. Searches for PTRs via the internal API
    3. Parses individual PTR pages for transaction details
    """

    BASE_URL = "https://efdsearch.senate.gov"
    SEARCH_URL = f"{BASE_URL}/search/"
    REPORT_URL = f"{BASE_URL}/search/view/ptr/"

    def __init__(self):
        self.csrf_token: Optional[str] = None
        self.cookies: dict = {}

    async def _get_csrf_token(self, client: httpx.AsyncClient) -> str:
        """Get CSRF token from the search page."""
        response = await client.get(
            self.SEARCH_URL,
            follow_redirects=True,
            timeout=30.0
        )

        # Store cookies
        self.cookies = dict(response.cookies)

        # Extract CSRF token from the page
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for csrftoken in cookies or hidden input
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input:
            return csrf_input.get('value', '')

        # Check cookies
        if 'csrftoken' in self.cookies:
            return self.cookies['csrftoken']

        # Try to find in response cookies
        for cookie in response.cookies.jar:
            if cookie.name == 'csrftoken':
                return cookie.value

        return ''

    async def _accept_agreement(self, client: httpx.AsyncClient) -> bool:
        """Accept the usage agreement on the search page."""
        if not self.csrf_token:
            self.csrf_token = await self._get_csrf_token(client)

        # The agreement is typically accepted by POSTing to the search page
        # with the agreement checkbox value
        headers = {
            'X-CSRFToken': self.csrf_token,
            'Referer': self.SEARCH_URL,
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        data = {
            'csrfmiddlewaretoken': self.csrf_token,
            'prohibition_agreement': '1',  # Accept agreement
        }

        response = await client.post(
            self.SEARCH_URL,
            data=data,
            headers=headers,
            cookies=self.cookies,
            follow_redirects=True,
            timeout=30.0
        )

        self.cookies.update(dict(response.cookies))
        return response.status_code == 200

    async def _search_ptrs(
        self,
        client: httpx.AsyncClient,
        first_name: str = "",
        last_name: str = "",
        start_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """Search for Periodic Transaction Reports."""
        if not self.csrf_token:
            self.csrf_token = await self._get_csrf_token(client)
            await self._accept_agreement(client)

        # Default to last 2 years if no start date
        if not start_date:
            start_date = (datetime.now() - timedelta(days=730)).strftime("%m/%d/%Y")

        headers = {
            'X-CSRFToken': self.csrf_token,
            'Referer': self.SEARCH_URL,
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
        }

        # The Senate EFD uses specific form field names
        data = {
            'csrfmiddlewaretoken': self.csrf_token,
            'first_name': first_name,
            'last_name': last_name,
            'filer_type': '1',  # Senators
            'report_type': '11',  # Periodic Transaction Reports
            'submitted_start_date': start_date,
            'submitted_end_date': datetime.now().strftime("%m/%d/%Y"),
        }

        try:
            # Try the search home page first to get proper session
            home_response = await client.get(
                f"{self.SEARCH_URL}home/",
                cookies=self.cookies,
                timeout=30.0,
                follow_redirects=True
            )
            self.cookies.update(dict(home_response.cookies))

            response = await client.post(
                f"{self.SEARCH_URL}report/data/",
                data=data,
                headers=headers,
                cookies=self.cookies,
                timeout=30.0
            )

            print(f"Senate search response status: {response.status_code}")
            print(f"Senate search response headers: {dict(response.headers)[:200] if response.headers else 'none'}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Senate search result keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")
                    return result.get('data', [])
                except Exception as e:
                    print(f"Senate JSON parse error: {e}")
                    print(f"Response text: {response.text[:500]}")
                    return []
            else:
                print(f"Senate PTR search failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []
        except Exception as e:
            print(f"Senate PTR search error: {e}")
            return []

    async def _parse_ptr_page(self, client: httpx.AsyncClient, ptr_id: str) -> list[dict]:
        """Parse a single PTR page to extract transactions."""
        url = f"{self.REPORT_URL}{ptr_id}/"

        try:
            response = await client.get(
                url,
                cookies=self.cookies,
                timeout=30.0
            )

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            transactions = []

            # Find the transactions table
            tables = soup.find_all('table', class_='table')

            for table in tables:
                rows = table.find_all('tr')

                for row in rows[1:]:  # Skip header
                    cells = row.find_all('td')
                    if len(cells) >= 5:
                        transaction = self._parse_transaction_row(cells)
                        if transaction:
                            transactions.append(transaction)

            return transactions

        except Exception as e:
            print(f"Error parsing PTR {ptr_id}: {e}")
            return []

    def _parse_transaction_row(self, cells: list) -> Optional[dict]:
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

            return {
                "transaction_date": self._parse_date(tx_date),
                "owner": owner,
                "ticker": ticker if ticker and ticker != "--" else None,
                "asset_description": asset_name,
                "transaction_type": self._normalize_type(tx_type),
                "amount_range": amount,
                "amount_min": self._parse_amount_min(amount),
                "amount_max": self._parse_amount_max(amount),
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

    async def get_recent_transactions(self, days: int = 90, limit: int = 100) -> list[dict]:
        """Get recent Senate transactions from official source.

        Args:
            days: Number of days to look back
            limit: Maximum number of PTRs to process

        Returns:
            List of transaction dictionaries
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime("%m/%d/%Y")
        all_transactions = []

        async with httpx.AsyncClient() as client:
            # Get CSRF token and accept agreement
            self.csrf_token = await self._get_csrf_token(client)
            await self._accept_agreement(client)

            # Search for PTRs
            ptrs = await self._search_ptrs(client, start_date=start_date, limit=limit)
            print(f"Found {len(ptrs)} Senate PTRs")

            # Process each PTR
            for i, ptr in enumerate(ptrs[:limit]):
                try:
                    # Extract PTR ID and senator info
                    # PTR data structure varies, try to extract key fields
                    ptr_link = None
                    senator_name = ""
                    file_date = None

                    if isinstance(ptr, list) and len(ptr) >= 4:
                        # Format: [name, office, report_type, date, link_html]
                        senator_name = ptr[0] if ptr[0] else ""
                        file_date = ptr[3] if len(ptr) > 3 else None
                        link_html = ptr[4] if len(ptr) > 4 else ""

                        # Extract PTR ID from link
                        match = re.search(r'/ptr/([a-f0-9-]+)/', str(link_html))
                        if match:
                            ptr_link = match.group(1)

                    if not ptr_link:
                        continue

                    # Get transactions from this PTR
                    transactions = await self._parse_ptr_page(client, ptr_link)

                    # Add senator info to each transaction
                    for tx in transactions:
                        tx["senator"] = senator_name
                        tx["representative"] = senator_name
                        tx["chamber"] = "senate"
                        tx["disclosure_date"] = self._parse_date(file_date) if file_date else tx.get("transaction_date")
                        tx["filing_url"] = f"{self.REPORT_URL}{ptr_link}/"

                    all_transactions.extend(transactions)

                    # Rate limiting
                    if i < len(ptrs) - 1:
                        await asyncio.sleep(1.0)

                except Exception as e:
                    print(f"Error processing Senate PTR: {e}")
                    continue

        print(f"Retrieved {len(all_transactions)} Senate transactions")
        return all_transactions


class HouseDisclosureScraper:
    """Scraper for House Financial Disclosure system.

    The House disclosure system at disclosures-clerk.house.gov provides
    financial disclosure reports including PTRs. This scraper:
    1. Searches the financial disclosure database
    2. Downloads and parses PTR pages
    3. Extracts transaction details
    """

    BASE_URL = "https://disclosures-clerk.house.gov"
    SEARCH_URL = f"{BASE_URL}/FinancialDisclosure/ViewMemberSearchResult"

    async def _search_members(
        self,
        client: httpx.AsyncClient,
        last_name: str = "",
        filing_year: int = None,
        state: str = ""
    ) -> list[dict]:
        """Search for member financial disclosures."""
        if not filing_year:
            filing_year = datetime.now().year

        params = {
            "LastName": last_name,
            "FilingYear": filing_year,
            "State": state,
            "District": "",
        }

        try:
            response = await client.get(
                self.SEARCH_URL,
                params=params,
                timeout=30.0,
                follow_redirects=True
            )

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            # Parse the results table
            table = soup.find('table', class_='library-table')
            if not table:
                return []

            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all('td')
                if len(cells) >= 4:
                    # Extract member info and report link
                    name_cell = cells[0]
                    link = name_cell.find('a')

                    if link:
                        results.append({
                            "name": name_cell.get_text(strip=True),
                            "office": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                            "filing_year": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                            "report_type": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                            "url": self.BASE_URL + link.get('href', ''),
                        })

            return results

        except Exception as e:
            print(f"House search error: {e}")
            return []

    async def _parse_ptr_page(self, client: httpx.AsyncClient, url: str, member_name: str) -> list[dict]:
        """Parse a House PTR page to extract transactions."""
        try:
            response = await client.get(url, timeout=30.0, follow_redirects=True)

            if response.status_code != 200:
                return []

            # Check if this is a PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type.lower():
                # Skip PDFs for now - would need PDF parsing
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            transactions = []

            # Find transaction tables (PTR format)
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

            return transactions

        except Exception as e:
            print(f"Error parsing House PTR: {e}")
            return []

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

            return {
                "representative": member_name,
                "chamber": "house",
                "transaction_date": self._parse_date(tx_date),
                "disclosure_date": self._parse_date(tx_date),  # Will be updated if available
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
        # Common patterns: "AAPL - Apple Inc" or "(AAPL)" or "[AAPL]"
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

    async def get_recent_transactions(self, years: list[int] = None, limit: int = 100) -> list[dict]:
        """Get recent House transactions from official source.

        Args:
            years: Filing years to search (default: current and previous year)
            limit: Maximum number of reports to process per year

        Returns:
            List of transaction dictionaries
        """
        if not years:
            current_year = datetime.now().year
            years = [current_year, current_year - 1]

        all_transactions = []

        async with httpx.AsyncClient() as client:
            for year in years:
                print(f"Searching House disclosures for {year}...")

                # Search for all PTRs in the year
                # We search without a last name to get all members
                results = await self._search_members(client, filing_year=year)

                # Filter for PTRs only
                ptrs = [r for r in results if 'ptr' in r.get('report_type', '').lower()
                        or 'periodic' in r.get('report_type', '').lower()
                        or 'transaction' in r.get('report_type', '').lower()]

                print(f"Found {len(ptrs)} House PTRs for {year}")

                # Process each PTR
                for i, ptr in enumerate(ptrs[:limit]):
                    try:
                        transactions = await self._parse_ptr_page(
                            client,
                            ptr['url'],
                            ptr['name']
                        )
                        all_transactions.extend(transactions)

                        # Rate limiting
                        if i < len(ptrs) - 1:
                            await asyncio.sleep(0.5)

                    except Exception as e:
                        print(f"Error processing House PTR: {e}")
                        continue

        print(f"Retrieved {len(all_transactions)} House transactions")
        return all_transactions


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

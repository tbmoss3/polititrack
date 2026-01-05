"""Official government disclosure URL generators.

Instead of scraping government websites, we provide direct links to the
official disclosure search pages where users can view the authoritative
source documents.

Sources:
- Senate: efdsearch.senate.gov - Electronic Financial Disclosure
- House: disclosures-clerk.house.gov - Financial Disclosure Reports
- Capitol Trades: capitoltrades.com - Aggregated congressional trading data
"""

from urllib.parse import quote_plus


# Official disclosure search URLs
SENATE_EFD_SEARCH_URL = "https://efdsearch.senate.gov/search/"
SENATE_EFD_HOME_URL = "https://efdsearch.senate.gov/search/home/"
HOUSE_DISCLOSURE_URL = "https://disclosures-clerk.house.gov/FinancialDisclosure"
HOUSE_DISCLOSURE_SEARCH_URL = "https://disclosures-clerk.house.gov/FinancialDisclosure#Search"

# Capitol Trades - aggregated congressional trading data
CAPITOL_TRADES_URL = "https://www.capitoltrades.com/trades"
CAPITOL_TRADES_POLITICIAN_URL = "https://www.capitoltrades.com/politicians"


def get_senate_disclosure_url(last_name: str = "", first_name: str = "") -> str:
    """
    Get the URL to search for a Senator's financial disclosures.

    The Senate EFD site requires accepting an agreement before searching,
    so we link to the home page which will guide users through that process.

    Args:
        last_name: Senator's last name (optional, for context)
        first_name: Senator's first name (optional, for context)

    Returns:
        URL to the Senate EFD search page
    """
    # The Senate site doesn't support direct URL parameters for searching
    # Users must accept the agreement and then use the search form
    return SENATE_EFD_HOME_URL


def get_house_disclosure_url(last_name: str = "", state: str = "") -> str:
    """
    Get the URL to search for a House member's financial disclosures.

    Args:
        last_name: Representative's last name (optional)
        state: Two-letter state code (optional)

    Returns:
        URL to the House Financial Disclosure search page
    """
    # The House site uses a client-side search, so we link to the search section
    return HOUSE_DISCLOSURE_SEARCH_URL


def get_capitol_trades_url(last_name: str = "", first_name: str = "") -> str:
    """
    Get the URL to view a politician's trades on Capitol Trades.

    Args:
        last_name: Politician's last name
        first_name: Politician's first name

    Returns:
        URL to Capitol Trades (politician search or trades page)
    """
    # Capitol Trades allows searching by politician name
    if last_name:
        # URL encode the name for search - use lowercase with + for spaces
        name_query = f"{first_name} {last_name}".strip().lower().replace(" ", "+")
        return f"{CAPITOL_TRADES_POLITICIAN_URL}?search={name_query}"
    return CAPITOL_TRADES_URL


def get_disclosure_links(chamber: str, last_name: str = "", first_name: str = "", state: str = "") -> dict:
    """
    Get official disclosure links for a politician based on their chamber.

    Args:
        chamber: 'house' or 'senate'
        last_name: Politician's last name
        first_name: Politician's first name
        state: Two-letter state code

    Returns:
        Dictionary with disclosure URL and source information
    """
    if chamber.lower() == "senate":
        return {
            "financial_disclosure_url": get_senate_disclosure_url(last_name, first_name),
            "financial_disclosure_source": "Senate Electronic Financial Disclosure (EFD)",
            "capitol_trades_url": get_capitol_trades_url(last_name, first_name),
        }
    else:
        return {
            "financial_disclosure_url": get_house_disclosure_url(last_name, state),
            "financial_disclosure_source": "House Office of the Clerk - Financial Disclosure",
            "capitol_trades_url": get_capitol_trades_url(last_name, first_name),
        }


# Additional helpful links for reference
ADDITIONAL_RESOURCES = {
    "senate_ptr_info": "https://www.ethics.senate.gov/public/index.cfm/financialdisclosure",
    "house_ptr_info": "https://ethics.house.gov/financial-disclosure/general-information-about-financial-disclosure",
    "stock_act_info": "https://www.congress.gov/bill/112th-congress/senate-bill/2038",
}

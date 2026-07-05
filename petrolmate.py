import httpx
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

def get_cheapest_7eleven_stations():
    url = "https://petrolmate.com.au/brand/7-eleven"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    stations = []
    try:
        response = httpx.get(url, headers=headers, follow_redirects=True, timeout=10.0)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the table with "Cheapest 7-Eleven stations right now"
        # We look for a table that has "Price" in its header
        tables = soup.find_all('table')
        for table in tables:
            header = table.find('thead')
            if header and "Price" in header.get_text():
                rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        # Extract Name, Suburb, State, Price
                        name_link = cols[1].find('a')
                        name = name_link.get_text(strip=True) if name_link else cols[1].get_text(strip=True)

                        suburb_state = cols[2].get_text(strip=True)
                        price_text = cols[3].get_text(strip=True)

                        price_match = re.search(r'(\d+\.?\d*)', price_text)
                        if price_match:
                            price = float(price_match.group(1))

                            parts = suburb_state.split(',')
                            suburb = parts[0].strip()
                            state = parts[1].strip() if len(parts) > 1 else ""

                            stations.append({
                                "name": name,
                                "suburb": suburb.upper(),
                                "state": state.upper(),
                                "price": price
                            })
                break
    except Exception as e:
        logger.error(f"Error scraping Petrolmate: {e}")

    return stations

if __name__ == "__main__":
    stations = get_cheapest_7eleven_stations()
    for s in stations:
        print(s)

import json
import re
import urllib.request
import datetime
import sys

def scrape_city(url):
    req = urllib.request.Request(
        url, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            pattern = re.compile(
                r'benzin\s+fiyat[ıi]\s*([0-9,]+)\s*lira.*motorin\s+fiyat[ıi]\s*([0-9,]+)\s*lira.*LPG\s+fiyat[ıi]\s*([0-9,]+)\s*lira',
                re.IGNORECASE
            )
            match = pattern.search(html)
            if match:
                gasoline = float(match.group(1).replace(',', '.'))
                diesel = float(match.group(2).replace(',', '.'))
                lpg = float(match.group(3).replace(',', '.'))
                return {"gasoline": gasoline, "diesel": diesel, "lpg": lpg}
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    return None

def main():
    print("Scraping fuel prices from doviz.com...")
    
    istanbul_avrupa = scrape_city("https://www.doviz.com/akaryakit-fiyatlari/istanbul-avrupa")
    istanbul_anadolu = scrape_city("https://www.doviz.com/akaryakit-fiyatlari/istanbul-anadolu")
    istanbul = None
    if istanbul_avrupa and istanbul_anadolu:
        istanbul = {
            "gasoline": round((istanbul_avrupa["gasoline"] + istanbul_anadolu["gasoline"]) / 2, 2),
            "diesel": round((istanbul_avrupa["diesel"] + istanbul_anadolu["diesel"]) / 2, 2),
            "lpg": round((istanbul_avrupa["lpg"] + istanbul_anadolu["lpg"]) / 2, 2)
        }
    elif istanbul_avrupa:
        istanbul = istanbul_avrupa
    elif istanbul_anadolu:
        istanbul = istanbul_anadolu

    ankara = scrape_city("https://www.doviz.com/akaryakit-fiyatlari/ankara")

    izmir = scrape_city("https://www.doviz.com/akaryakit-fiyatlari/izmir/buca")
    if not izmir:
        izmir = scrape_city("https://www.doviz.com/akaryakit-fiyatlari/izmir")

    if not istanbul and not ankara and not izmir:
        print("Error: Could not scrape any city prices. Aborting update.")
        sys.exit(1)

    print("Scraped values:")
    print(f"Istanbul: {istanbul}")
    print(f"Ankara: {ankara}")
    print(f"Izmir: {izmir}")

    try:
        with open("tolls.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading tolls.json: {e}")
        sys.exit(1)

    if "fuel_prices" not in data:
        data["fuel_prices"] = {}

    if istanbul:
        data["fuel_prices"]["istanbul"] = istanbul
    if ankara:
        data["fuel_prices"]["ankara"] = ankara
    if izmir:
        data["fuel_prices"]["izmir"] = izmir

    if "metadata" not in data:
        data["metadata"] = {}
    data["metadata"]["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"

    try:
        with open("tolls.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Successfully updated tolls.json!")
    except Exception as e:
        print(f"Error writing tolls.json: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

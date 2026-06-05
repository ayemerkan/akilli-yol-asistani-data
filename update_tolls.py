import json
import re
import urllib.request
import datetime
import sys
import os
import ssl
# SSL sertifika dogrulamalarini devre disi birakalim (KGM sitesindeki SSL hatalarini bypass etmek icin)
ssl_context = ssl._create_unverified_context()
try:
    from pypdf import PdfReader
except ImportError:
    class PdfReader:
        def __init__(self, path):
            self.pages = []
def clean_price(price_str):
    return float(price_str.replace('.', '').replace(',', '.'))
def scrape_city(url):
    req = urllib.request.Request(
        url, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
            return response.read()
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return None
def extract_pdf_text(pdf_bytes):
    if not pdf_bytes:
        return ""
    temp_filename = "temp.pdf"
    with open(temp_filename, "wb") as f:
        f.write(pdf_bytes)
    
    text = ""
    try:
        reader = PdfReader(temp_filename)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    return text
def discover_kgm_toll_page_url():
    """KGM ana sayfasindan aktif ucret sayfasini dinamik olarak bulur."""
    ana_url = "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Otoyollar/UcretlerAna.aspx"
    default_url = "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Otoyollar/UcretlerYeni.aspx"
    
    print(f"Attempting to dynamically discover active KGM toll page from {ana_url}...")
    req = urllib.request.Request(
        ana_url, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as r:
            html = r.read().decode('utf-8')
            
        matches = re.findall(r'href="([^"]*ucret[^"]+\.aspx)"', html, re.IGNORECASE)
        
        discovered_urls = []
        for match in matches:
            if match.startswith("/"):
                full_url = "https://www.kgm.gov.tr" + match
            elif match.startswith("http"):
                full_url = match
            else:
                full_url = "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Otoyollar/" + match
                
            page_name = full_url.split("/")[-1].lower()
            if "ucretler" in page_name and "ana" not in page_name:
                discovered_urls.append(full_url)
                
        if discovered_urls:
            def sort_key(url):
                url_lower = url.lower()
                score = 0
                if "yeni" in url_lower:
                    score += 10
                years = re.findall(r'20\d{2}', url_lower)
                if years:
                    score += int(years[0]) - 2000
                return score
            
            discovered_urls.sort(key=sort_key, reverse=True)
            active_url = discovered_urls[0]
            print(f"Dynamic discovery SUCCESS! Found active toll page: {active_url}")
            return active_url
            
    except Exception as e:
        print(f"Dynamic discovery failed ({e}). Falling back to default URL.")
        
    print(f"Using default URL: {default_url}")
    return default_url
def main():
    kgm_page_url = discover_kgm_toll_page_url()
    print(f"Fetching KGM Toll Rates Page: {kgm_page_url}")
    req = urllib.request.Request(
        kgm_page_url, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as r:
            html = r.read().decode('utf-8')
    except Exception as e:
        print(f"Error loading KGM page: {e}")
        sys.exit(1)
        
    pdf_regex = re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE)
    pdf_links = pdf_regex.findall(html)
    
    pdf_map = {}
    for link in pdf_links:
        full_url = "https://www.kgm.gov.tr" + link if link.startswith("/") else link
        filename = link.split("/")[-1]
        fn_lower = filename.lower()
        
        if "osmangazi" in fn_lower:
            pdf_map["osmangazi_koprusu"] = full_url
        elif "yss" in fn_lower and "kuzey" not in fn_lower and "cevre" not in fn_lower:
            pdf_map["yavuz_sultan_selim_koprusu"] = full_url
        elif "canakkale" in fn_lower or "1915" in fn_lower:
            pdf_map["canakkale_koprusu"] = full_url
        elif "gebze" in fn_lower or "orhangazi" in fn_lower or ("izmir" in fn_lower and "istanbul" in fn_lower):
            pdf_map["izmir_istanbul_otoyolu"] = full_url
        elif "nigde" in fn_lower or "ankara-nigde" in fn_lower:
            pdf_map["ankara_nigde_otoyolu"] = full_url
        elif "anadolu" in fn_lower:
            pdf_map["anadolu_otoyolu"] = full_url
        elif "kuzey" in fn_lower or "marmara" in fn_lower:
            pdf_map["kuzey_marmara_otoyolu"] = full_url
    print("Found KGM PDF URLs:")
    for k, v in pdf_map.items():
        print(f"  {k}: {v}")
    # tolls.json dosyasini oku
    if not os.path.exists("tolls.json"):
        print("Error: tolls.json file not found in the current directory.")
        sys.exit(1)
        
    try:
        with open("tolls.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading tolls.json: {e}")
        sys.exit(1)
    tolls_list = data.get("tolls", [])
    updated_count = 0
    
    # Kopru PDF'leri icin genel regex (1-6 sinif fiyatlari)
    bridge_regex = re.compile(
        r'1\s+([0-9.,]+)\s*(?:₺)?\s*2\s+([0-9.,]+)\s*(?:₺)?\s*3\s+([0-9.,]+)\s*(?:₺)?\s*4\s+([0-9.,]+)\s*(?:₺)?\s*5\s+([0-9.,]+)\s*(?:₺)?\s*6\s+([0-9.,]+)',
        re.IGNORECASE
    )
    
    for toll in tolls_list:
        toll_id = toll.get("id")
        scraped_prices = None
        
        # Kopruler (Osmangazi, YSS, Canakkale)
        if toll_id in ["osmangazi_koprusu", "yavuz_sultan_selim_koprusu", "canakkale_koprusu"]:
            url = pdf_map.get(toll_id)
            if url:
                print(f"Downloading and parsing {toll_id}...")
                pdf_bytes = scrape_city(url)
                text = extract_pdf_text(pdf_bytes)
                match = bridge_regex.search(text)
                if match:
                    scraped_prices = {
                        "class1": clean_price(match.group(1)),
                        "class2": clean_price(match.group(2)),
                        "class3": clean_price(match.group(3)),
                        "class4": clean_price(match.group(4)),
                        "class5": clean_price(match.group(5)),
                        "class6": clean_price(match.group(6))
                    }
                else:
                    print(f"  Warning: Could not parse prices from PDF for {toll_id}")
                    
        # Ankara-Nigde Otoyolu
        elif toll_id == "ankara_nigde_otoyolu":
            url = pdf_map.get(toll_id)
            if url:
                print(f"Downloading and parsing {toll_id}...")
                pdf_bytes = scrape_city(url)
                text = extract_pdf_text(pdf_bytes)
                match = bridge_regex.search(text)
                if match:
                    scraped_prices = {
                        "class1": clean_price(match.group(1)),
                        "class2": clean_price(match.group(2)),
                        "class3": clean_price(match.group(3)),
                        "class4": clean_price(match.group(4)),
                        "class5": clean_price(match.group(5)),
                        "class6": clean_price(match.group(6))
                    }
                else:
                    print(f"  Warning: Could not parse prices from PDF for {toll_id}")
                    
        # Anadolu Otoyolu
        elif toll_id == "anadolu_otoyolu":
            url = pdf_map.get(toll_id)
            if url:
                print(f"Downloading and parsing {toll_id}...")
                pdf_bytes = scrape_city(url)
                text = extract_pdf_text(pdf_bytes)
                match = bridge_regex.search(text)
                if match:
                    scraped_prices = {
                        "class1": clean_price(match.group(1)),
                        "class2": clean_price(match.group(2)),
                        "class3": clean_price(match.group(3)),
                        "class4": clean_price(match.group(4)),
                        "class5": clean_price(match.group(5)),
                        "class6": clean_price(match.group(6))
                    }
                else:
                    print(f"  Warning: Could not parse prices from PDF for {toll_id}")
                    
        # Izmir-Istanbul Otoyolu
        elif toll_id == "izmir_istanbul_otoyolu":
            url = pdf_map.get(toll_id)
            if url:
                print(f"Downloading and parsing {toll_id}...")
                pdf_bytes = scrape_city(url)
                text = extract_pdf_text(pdf_bytes)
                match = bridge_regex.search(text)
                if match:
                    scraped_prices = {
                        "class1": clean_price(match.group(1)),
                        "class2": clean_price(match.group(2)),
                        "class3": clean_price(match.group(3)),
                        "class4": clean_price(match.group(4)),
                        "class5": clean_price(match.group(5)),
                        "class6": clean_price(match.group(6))
                    }
                else:
                    print(f"  Warning: Could not parse prices from PDF for {toll_id}")
                    
        # Kuzey Marmara Otoyolu
        elif toll_id == "kuzey_marmara_otoyolu":
            url = pdf_map.get(toll_id)
            if url:
                print(f"Downloading and parsing {toll_id}...")
                pdf_bytes = scrape_city(url)
                text = extract_pdf_text(pdf_bytes)
                match = bridge_regex.search(text)
                if match:
                    scraped_prices = {
                        "class1": clean_price(match.group(1)),
                        "class2": clean_price(match.group(2)),
                        "class3": clean_price(match.group(3)),
                        "class4": clean_price(match.group(4)),
                        "class5": clean_price(match.group(5)),
                        "class6": clean_price(match.group(6))
                    }
                else:
                    print(f"  Warning: Could not parse prices from PDF for {toll_id}")
        
        # Avrasya Tuneli - KGM'de yok, sabit fiyat kullaniyoruz
        elif toll_id == "avrasya_tuneli":
            print(f"Skipping {toll_id} - not managed by KGM, using fixed prices.")
            # Avrasya Tuneli KGM tarafindan yonetilmiyor, fiyatlarini elle guncelliyoruz
            continue
        if scraped_prices:
            old_prices = toll.get("prices", {})
            diff = False
            for k in ["class1", "class2", "class3", "class4", "class5", "class6"]:
                if old_prices.get(k) != scraped_prices.get(k):
                    diff = True
                    break
            
            if diff:
                print(f"Toll rate change detected for {toll_id}!")
                print(f"  Old: {old_prices}")
                print(f"  New: {scraped_prices}")
                toll["prices"] = scraped_prices
                updated_count += 1
            else:
                print(f"No changes for {toll_id}.")
    if updated_count > 0:
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        with open("tolls.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully updated tolls.json with {updated_count} changed toll roads/bridges!")
    else:
        print("All otoyol and bridge tolls are up to date.")
if __name__ == "__main__":
    main()

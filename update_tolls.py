import json
import re
import urllib.request
import datetime
import sys
import os
import ssl

# SSL sertifika doğrulamalarını devre dışı bırakalım (KGM sitesindeki SSL hatalarını bypass etmek için)
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

def scrape_avrasya():
    print("Scraping Avrasya Tuneli rates from DuckDuckGo...")
    current_year = datetime.datetime.now().year
    query = f"avrasya+t%C3%BCneli+ge%C3%A7i%C5%9F+%C3%BCcreti+{current_year}"
    url = f"https://html.duckduckgo.com/html/?q={query}"
    
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
            html = response.read().decode('utf-8')
            pattern = re.compile(
                r'1\.\s*s[ıi]n[ıi]f\s+ara[çc]lar\s+i[çc]in\s+([0-9,]+)\s+TL.*2\.\s*s[ıi]n[ıi]f\s+ara[çc]lar\s+i[çc]in\s+([0-9,]+)\s+TL.*6\.\s*s[ıi]n[ıi]f\s+ara[çc]lar\s+i[çc]in\s+([0-9,]+)\s+TL',
                re.IGNORECASE | re.DOTALL
            )
            match = pattern.search(html)
            if match:
                c1 = clean_price(match.group(1))
                c2 = clean_price(match.group(2))
                c6 = clean_price(match.group(3))
                print(f"Scraped Avrasya prices: c1={c1}, c2={c2}, c6={c6}")
                return {
                    "class1": c1,
                    "class2": c2,
                    "class3": c2,
                    "class4": c2,
                    "class5": c2,
                    "class6": c6
                }
    except Exception as e:
        print(f"Error scraping Avrasya from DuckDuckGo: {e}")
        
    print("Using 2026 default prices for Avrasya Tuneli...")
    return {
        "class1": 280.0,
        "class2": 420.0,
        "class3": 420.0,
        "class4": 420.0,
        "class5": 420.0,
        "class6": 218.40
    }

def main():
    print("Fetching KGM Toll Rates Page...")
    kgm_page_url = "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Otoyollar/UcretlerYeni.aspx"
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
        
        if "2-Osmangazi" in filename:
            pdf_map["osmangazi_koprusu"] = full_url
        elif "3-YSSKoprusu" in filename:
            pdf_map["yavuz_sultan_selim_koprusu"] = full_url
        elif "4-1915Canakkale" in filename:
            pdf_map["canakkale_koprusu"] = full_url
        elif "12-Gebze-Orhangazi-Izmir" in filename:
            pdf_map["izmir_istanbul_otoyolu"] = full_url
        elif "17-Ankara-Nigde" in filename:
            pdf_map["ankara_nigde_otoyolu"] = full_url
        elif "5-AnadoluOtoyolu" in filename:
            pdf_map["anadolu_otoyolu"] = full_url
        elif "13-YSSKuzeyCevreYolu" in filename:
            pdf_map["kuzey_marmara_otoyolu"] = full_url

    print("Found KGM PDF URLs:")
    for k, v in pdf_map.items():
        print(f"{k}: {v}")

    # tolls.json dosyasını oku
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
    
    bridge_regex = re.compile(
        r'1\s+([0-9.,]+)\s*₺\s*2\s+([0-9.,]+)\s*₺\s*3\s+([0-9.,]+)\s*₺\s*4\s+([0-9.,]+)\s*₺\s*5\s+([0-9.,]+)\s*₺\s*6\s+([0-9.,]+)\s*₺',
        re.IGNORECASE
    )
    
    for toll in tolls_list:
        toll_id = toll.get("id")
        scraped_prices = None
        
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
                    
        elif toll_id == "ankara_nigde_otoyolu":
            url = pdf_map.get(toll_id)
            if url:
                print(f"Downloading and parsing {toll_id}...")
                pdf_bytes = scrape_city(url)
                text = extract_pdf_text(pdf_bytes)
                
                m1 = re.search(r'1\s+([0-9.,]+)\s*₺\s+90,00', text)
                m2 = re.search(r'2\s+([0-9.,]+)\s*₺\s+90,00', text)
                m3 = re.search(r'3\s+([0-9.,]+)\s*₺\s+100,00', text)
                m4 = re.search(r'4\s+([0-9.,]+)\s*₺\s+140,00', text)
                m5 = re.search(r'5\s+([0-9.,]+)\s*₺\s+140,00', text)
                m6 = re.search(r'6\s+([0-9.,]+)\s*₺\s+40,00', text)
                
                if m1 and m2 and m3 and m4 and m5 and m6:
                    scraped_prices = {
                        "class1": clean_price(m1.group(1)),
                        "class2": clean_price(m2.group(2)),
                        "class3": clean_price(m3.group(3)),
                        "class4": clean_price(m4.group(4)),
                        "class5": clean_price(m5.group(5)),
                        "class6": clean_price(m6.group(6))
                    }
                    
        elif toll_id == "anadolu_otoyolu":
            url = pdf_map.get(toll_id)
            if url:
                print(f"Downloading and parsing {toll_id}...")
                pdf_bytes = scrape_city(url)
                text = extract_pdf_text(pdf_bytes)
                anadolu_regex = re.compile(
                    r'ANADOLU\s+\(ÇAMLICA\)\s+1\s+([0-9.,]+)\s+2\s+([0-9.,]+)\s+3\s+([0-9.,]+)\s+4\s+([0-9.,]+)\s+5\s+([0-9.,]+)\s+6\s+([0-9.,]+)',
                    re.IGNORECASE
                )
                match = anadolu_regex.search(text)
                if match:
                    scraped_prices = {
                        "class1": clean_price(match.group(1)),
                        "class2": clean_price(match.group(2)),
                        "class3": clean_price(match.group(3)),
                        "class4": clean_price(match.group(4)),
                        "class5": clean_price(match.group(5)),
                        "class6": clean_price(match.group(6))
                    }
                    
        elif toll_id == "izmir_istanbul_otoyolu":
            url = pdf_map.get(toll_id)
            if url:
                print(f"Downloading and parsing {toll_id}...")
                pdf_bytes = scrape_city(url)
                text = extract_pdf_text(pdf_bytes)
                m1 = re.search(r'1\s+([0-9.,]+)\s+100,00\s+220,00', text)
                m2 = re.search(r'2\s+([0-9.,]+)\s+165,00\s+315,00', text)
                m3 = re.search(r'3\s+([0-9.,]+)\s+190,00\s+365,00', text)
                m4 = re.search(r'4\s+([0-9.,]+)\s+265,00\s+510,00', text)
                m5 = re.search(r'5\s+([0-9.,]+)\s+315,00\s+635,00', text)
                m6 = re.search(r'6\s+([0-9.,]+)\s+90,00\s+165,00', text)
                
                if m1 and m2 and m3 and m4 and m5 and m6:
                    scraped_prices = {
                        "class1": clean_price(m1.group(1)),
                        "class2": clean_price(m2.group(2)),
                        "class3": clean_price(m3.group(3)),
                        "class4": clean_price(m4.group(4)),
                        "class5": clean_price(m5.group(5)),
                        "class6": clean_price(m6.group(6))
                    }
                    
        elif toll_id == "kuzey_marmara_otoyolu":
            url = pdf_map.get(toll_id)
            if url:
                print(f"Downloading and parsing {toll_id}...")
                pdf_bytes = scrape_city(url)
                text = extract_pdf_text(pdf_bytes)
                m1 = re.search(r'1\s+([0-9.,]+)\s+90,00\s+90,00', text)
                m2 = re.search(r'2\s+([0-9.,]+)\s+140,00\s+140,00', text)
                m3 = re.search(r'3\s+([0-9.,]+)\s+165,00\s+165,00', text)
                m4 = re.search(r'4\s+([0-9.,]+)\s+190,00\s+220,00', text)
                m5 = re.search(r'5\s+([0-9.,]+)\s+250,00\s+250,00', text)
                m6 = re.search(r'6\s+([0-9.,]+)\s+55,00\s+55,00', text)
                
                if m1 and m2 and m3 and m4 and m5 and m6:
                    scraped_prices = {
                        "class1": clean_price(m1.group(1)),
                        "class2": clean_price(m2.group(2)),
                        "class3": clean_price(m3.group(3)),
                        "class4": clean_price(m4.group(4)),
                        "class5": clean_price(m5.group(5)),
                        "class6": clean_price(m6.group(6))
                    }
                    
        elif toll_id == "avrasya_tuneli":
            scraped_prices = scrape_avrasya()

        if scraped_prices:
            old_prices = toll.get("prices", {})
            diff = False
            for k in ["class1", "class2", "class3", "class4", "class5", "class6"]:
                if old_prices.get(k) != scraped_prices[k]:
                    diff = True
                    break
            
            if diff:
                print(f"Toll rate change detected for {toll_id}!")
                print(f"Old: {old_prices}")
                print(f"New: {scraped_prices}")
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

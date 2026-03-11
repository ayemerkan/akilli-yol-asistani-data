import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# GitHub reponuzun kök dizinindeki tolls.json dosyasının yolu
# Action çalıştığında kök dizinde olacağı için doğrudan dosya adını veriyoruz.
FILE_PATH = '../tolls.json' 
if not os.path.exists(FILE_PATH):
    # Eğer lokalde çalıştırılıyorsa path'i düzeltmek için
    FILE_PATH = 'tolls.json'

def fetch_current_prices_from_source():
    """
    Bu fonksiyon Karayolları Genel Müdürlüğü (KGM) veya ilgili köprü işletmesinin web 
    sitesinden güncel fiyatları çekecek mantığı barındırır.
    
    Örnek olarak requests ve BeautifulSoup kullanarak bir web sayfasından 
    veri çekme şablonu aşağıdadır. (Gerçek KGM sitesinin HTML yapısına 
    göre spesifik 'find' veya 'select' metodları kullanmanız gerekir.)
    """
    print(f"[{datetime.now()}] Web scrap işlemi başlatılıyor...")
    
    # -----------------------------------------------------------------
    # BURAYA GERÇEK KAZIMA (SCRAPING) MANTIĞI GELECEK
    # url = "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Otoyollar/UcretlerYeni.aspx"
    # response = requests.get(url, verify=False)
    # soup = BeautifulSoup(response.text, "html.parser")
    # fiyat_etiketi = soup.find('div', class_='fiyat-tablosu')
    # ...
    # -----------------------------------------------------------------
    
    # Şimdilik sistemin hata vermeden çalışması ve mantığı kavramanız için 
    # manuel hazırlanmış veya parse edilmiş bir veriyi listeye dönüştürüyoruz.
    # Yapmanız gereken şey, yukarıdaki soup parse işleminden çıkan fiyatları 
    # aşağıdaki yapıdaki 'prices' karşılıklarına yazdırmaktır.

    scraped_data = [
      {
        "id": "izmir_istanbul_otoyolu",
        "name": "İzmir - İstanbul Otoyolu (Osmangazi Köprüsü Dahil)",
        "location": {
          "latitude": 40.5445,
          "longitude": 29.5165
        },
        "prices": {
          "class1": 1580.0,
          "class2": 2525.0,
          "class3": 3000.0,
          "class4": 3000.0,
          "class5": 3000.0,
          "class6": 660.0
        }
      },
      {
        "id": "osmangazi_koprusu",
        "name": "Osmangazi Köprüsü (Geçiş Noktası)",
        "location": {
          "latitude": 40.7330,
          "longitude": 29.5110
        },
        "prices": {
          "class1": 790.0,
          "class2": 1265.0,
          "class3": 1500.0,
          "class4": 1500.0,
          "class5": 1500.0,
          "class6": 330.0
        }
      },
      {
        "id": "canakkale_koprusu",
        "name": "1915 Çanakkale Köprüsü",
        "location": {
          "latitude": 40.3392,
          "longitude": 26.6385
        },
        "prices": {
          "class1": 930.0,
          "class2": 1160.0,
          "class3": 2185.0,
          "class4": 2325.0,
          "class5": 4370.0,
          "class6": 230.0
        }
      },
      {
        "id": "yavuz_sultan_selim_koprusu",
        "name": "Yavuz Sultan Selim Köprüsü",
        "location": {
          "latitude": 41.2014,
          "longitude": 29.1121
        },
        "prices": {
          "class1": 135.0,
          "class2": 180.0,
          "class3": 220.0,
          "class4": 220.0,
          "class5": 220.0,
          "class6": 65.0
        }
      },
      {
        "id": "anadolu_otoyolu",
        "name": "Anadolu Otoyolu (Çamlıca İstasyonu)",
        "location": {
          "latitude": 40.9796,
          "longitude": 29.1919
        },
        "prices": {
          "class1": 210.0,
          "class2": 280.0,
          "class3": 355.0,
          "class4": 355.0,
          "class5": 355.0,
          "class6": 65.0
        }
      }
    ]
    return scraped_data

def update_tolls_file():
    # 1. Mevcut tolls.json dosyasını oku
    existing_data = []
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                print("Mevcut JSON okunamadı, boş kabul edilecek.")
    
    # 2. Web'den güncel veriyi çek
    new_data = fetch_current_prices_from_source()
    
    # 3. İki JSON objesini karşılaştır (Sıralama farketmeksizin veri yapısı aynı mı?)
    # En basit kontrol string karşılaştırma yerin obje düzeyinde kontroldür:
    if existing_data != new_data:
        print(f"[{datetime.now()}] Fiyatlarda değişiklik tespit edildi! JSON güncelleniyor...")
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        print("tolls.json başarıyla yeni fiyatlarla kaydedildi.")
    else:
        print(f"[{datetime.now()}] Sistem fiyatlarında herhangi bir değişiklik yok.")

if __name__ == "__main__":
    update_tolls_file()

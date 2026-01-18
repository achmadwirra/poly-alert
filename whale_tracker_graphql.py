import requests
import time
import json
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

WHALE_ADDRESS = "0x589222a5124a96765443b97a3498d89ffd824ad2"
WHALE_USERNAME = "PurpleThunderBicycleMountain"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HISTORY_FILE = "whale_tx_hashes.json"
CHECK_INTERVAL = 60

# Setup Selenium (headless)
def init_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        })
    except Exception as e:
        print(f"[Telegram Error] {e}")

def get_tx_hashes(address):
    resp = requests.get(f"https://data-api.polymarket.com/traded?user={address}", timeout=10)
    return set(resp.json())

def scrape_latest_activity(username):
    """Scrape hanya 1 baris aktivitas terbaru dari halaman profil."""
    driver = init_driver()
    try:
        url = f"https://polymarket.com/@{username}?via=polydata"
        driver.get(url)
        
        wait = WebDriverWait(driver, 15)
        # Klik tab Activity jika perlu
        try:
            activity_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Activity')]")))
            activity_tab.click()
        except:
            pass  # Mungkin sudah otomatis di Activity
        
        # Ambil baris pertama di tabel
        first_row = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        cols = first_row.find_elements(By.TAG_NAME, "td")
        
        if len(cols) >= 4:
            action = cols[0].text.strip()
            market = cols[1].text.strip()
            amount = cols[3].text.strip()
            return f"{action} | {market} | {amount}"
        return "Aktivitas terdeteksi (detail tidak tersedia)"
    except Exception as e:
        return f"Aktivitas terdeteksi (scraping error: {str(e)[:50]}...)"
    finally:
        driver.quit()

def main():
    print(f"[INFO] Memantau whale: @{WHALE_USERNAME}")
    seen_hashes = set()
    
    # Load history
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            seen_hashes = set(json.load(f))
    
    while True:
        try:
            current_hashes = get_tx_hashes(WHALE_ADDRESS)
            new_hashes = current_hashes - seen_hashes
            
            if new_hashes:
                print(f"[ALERT] {len(new_hashes)} transaksi baru terdeteksi!")
                
                # Ambil detail dari web (hanya sekali)
                detail = scrape_latest_activity(WHALE_USERNAME)
                
                msg = f"🐋 <b>@{WHALE_USERNAME}</b> baru saja bertransaksi!\n\n{detail}"
                if len(new_hashes) > 1:
                    msg += f"\n(+{len(new_hashes)-1} transaksi lain)"
                
                print(msg)
                send_telegram(msg)
                
                # Simpan hash terbaru
                seen_hashes = current_hashes
                with open(HISTORY_FILE, 'w') as f:
                    json.dump(list(seen_hashes), f)
            
            else:
                print(f"[{time.strftime('%H:%M')}] Tidak ada aktivitas baru.")
                
        except Exception as e:
            print(f"[ERROR] {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
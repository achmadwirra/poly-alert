import requests
import time
import json
import os
from dotenv import load_dotenv

# Muat variabel dari .env
load_dotenv()

# === Baca Konfigurasi dari .env ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Validasi wajib
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID harus diisi di .env!")

# Muat daftar whale dinamis
WHALES = []
i = 1
while True:
    name = os.getenv(f"WHALE_{i}_NAME")
    addr = os.getenv(f"WHALE_{i}_ADDRESS")
    if not name or not addr:
        break
    WHALES.append({"name": name, "address": addr})
    i += 1

if not WHALES:
    raise ValueError("❌ Tidak ada whale ditemukan di .env! Tambahkan WHALE_1_NAME dan WHALE_1_ADDRESS.")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))  # default 60 detik
DATA_DIR = "whale_data"
os.makedirs(DATA_DIR, exist_ok=True)

print(f"✅ Memantau {len(WHALES)} whale:")
for w in WHALES:
    print(f"   - {w['name']} ({w['address'][:8]}...)")
print(f"⏱️  Interval: {CHECK_INTERVAL} detik\n")

# === Fungsi Telegram ===
def send_telegram(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code != 200:
            print(f"[⚠️ Telegram Error] {resp.text}")
    except Exception as e:
        print(f"[⚠️ Gagal kirim Telegram] {e}")

# === Fungsi Polymarket ===
def get_positions(address: str):
    try:
        url = f"https://data-api.polymarket.com/positions?user={address}&sortBy=CURRENT&sortDirection=DESC&sizeThreshold=0.01&limit=100"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ERROR] Gagal ambil posisi untuk {address}: {e}")
        return []

def load_saved(whale_name: str):
    path = os.path.join(DATA_DIR, f"{whale_name}.json")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def save_positions(whale_name: str, positions):
    path = os.path.join(DATA_DIR, f"{whale_name}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(positions, f, indent=2, ensure_ascii=False)

def positions_equal(old, new):
    if old is None or new is None:
        return False
    if len(old) != len(new):
        return False
    def key(p): return (p.get("market", ""), p.get("outcome", ""))
    return sorted(old, key=key) == sorted(new, key=key)

# === Main Loop ===
def main():
    print("🚀 Whale Tracker dimulai! Menunggu perubahan...\n")
    
    # Snapshot awal
    for whale in WHALES:
        current = get_positions(whale["address"])
        if current is not None:
            save_positions(whale["name"], current)
        time.sleep(1)  # jangan spam API

    while True:
        for whale in WHALES:
            name = whale["name"]
            addr = whale["address"]
            
            current = get_positions(addr)
            if current is None:
                continue

            last = load_saved(name)
            
            if not positions_equal(last, current):
                # Ada perubahan!
                total = len(current)
                new_count = total - (len(last) if last else 0)
                
                # Bangun pesan
                msg = f"🐋 <b>{name}</b> baru saja mengubah posisi!\n"
                msg += f"📊 Total posisi aktif: {total}\n\n"
                
                # Tampilkan maks 5 posisi teratas
                for i, pos in enumerate(current[:5]):
                    market = pos.get("market", "Unknown Market")
                    outcome = pos.get("outcome", "?")
                    amount = float(pos.get("amount", 0))
                    price = float(pos.get("price", 0))
                    value = amount * price
                    msg += f"{i+1}. <b>{market}</b>\n"
                    msg += f"   → {outcome} | {amount:.2f} @ ${price:.4f} = ${value:.2f}\n"
                
                if total > 5:
                    msg += f"\n... dan {total - 5} posisi lainnya"
                
                print(f"🚨 ALERT: {name} bergerak!")
                send_telegram(msg)
                save_positions(name, current)
            
            time.sleep(2)  # jeda antar request
        
        print(f"[{time.strftime('%H:%M:%S')}] Semua whale dipantau. Tidur {CHECK_INTERVAL} detik...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
import requests
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

# === Muat whale dari .env ===
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
    raise ValueError("❌ Tidak ada whale di .env!")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("❌ Lengkapi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di .env!")

HISTORY_FILE = "whale_seen_fingerprints.json"
CHECK_INTERVAL = 5  # detik


def send_telegram(message: str):
    try:
        # ✅ Perbaiki: hapus spasi setelah /bot
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"[⚠️ Telegram Error] {e}")


def get_fingerprint(whale_name, act):
    market = act.get("title", "Unknown Market")
    outcome = act.get("outcome", "?")
    price = float(act.get("price", 0))
    timestamp = int(act.get("timestamp", "0"))
    rounded_time = timestamp - (timestamp % 30)
    return f"{whale_name}|{market}|{outcome}|{price:.4f}|{rounded_time}"


def safe_timestamp(act):
    ts = act.get("timestamp")
    if not ts:
        return 0
    try:
        return int(ts)
    except (ValueError, TypeError):
        return 0


def main():
    print(f"[INFO] 🟢 Memantau {len(WHALES)} whale secara real-time!")
    for w in WHALES:
        print(f"   - {w['name']} ({w['address'][:8]}...)")
    print(f"[INFO] Interval: {CHECK_INTERVAL} detik\n")

    seen_fingerprints = set()
    try:
        with open(HISTORY_FILE, 'r') as f:
            seen_fingerprints = set(json.load(f))
    except FileNotFoundError:
        pass

    while True:
        for whale in WHALES:
            try:
                # ✅ Perbaiki URL: hapus spasi ekstra
                url = f"https://data-api.polymarket.com/activity?user={whale['address']}"
                resp = requests.get(url, timeout=8)
                resp.raise_for_status()  # akan error jika status bukan 2xx
                activities = resp.json()

                # Filter hanya aktivitas BUY
                buy_activities = [
                    act for act in activities
                    if str(act.get("side", "")).upper() == "BUY"
                ]

                # Urutkan berdasarkan timestamp: terbaru dulu (aman terhadap data rusak)
                buy_activities.sort(key=safe_timestamp, reverse=True)

                # Ambil maksimal 2 aktivitas terbaru
                for act in buy_activities[:2]:
                    fp = get_fingerprint(whale["name"], act)
                    if fp in seen_fingerprints:
                        continue

                    # Ekstrak data
                    market = act.get("title", "Unknown Market")
                    outcome = act.get("outcome", "?")
                    amount = float(act.get("size", 0))
                    price = float(act.get("price", 0))
                    usd_value = round(amount * price, 2)

                    # Buat link
                    market_id = act.get("marketId")
                    if market_id:
                        market_link = f"https://polymarket.com/market/{market_id}"
                        link_text = f"<a href='{market_link}'>Lihat Pasar</a>"
                    else:
                        link_text = f"<a href='https://polymarket.com/@{whale['name']}'>Profil Whale</a>"

                    # Kirim notifikasi
                    msg = (
                        f"🟢 <b>{whale['name']}</b> just voted!\n"
                        f"• 🟢 Buy {market} → {outcome} | {amount:.2f} @ ${price:.4f} = ${usd_value:.2f}\n"
                        f"🔗 {link_text}"
                    )
                    send_telegram(msg)
                    print(f"[{time.strftime('%H:%M:%S')}] 🟢 {msg}")

                    seen_fingerprints.add(fp)

            except Exception as e:
                print(f"[ERROR] {whale['name']}: {type(e).__name__}: {e}")

            time.sleep(1)  # jeda antar whale

        # Simpan semua fingerprint sekali per siklus
        with open(HISTORY_FILE, 'w') as f:
            json.dump(list(seen_fingerprints), f)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
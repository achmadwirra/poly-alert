import requests
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

WHALE_ADDRESS = "0x589222a5124a96765443b97a3498d89ffd824ad2"
WHALE_NAME = "PurpleThunderBicycleMountain"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ACTIVITY_URL = f"https://data-api.polymarket.com/activity?user={WHALE_ADDRESS}"
HISTORY_FILE = "whale_activity_last.json"  # Simpan data terakhir sebagai JSON
CHECK_INTERVAL = 60

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("❌ Lengkapi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di .env!")

def send_telegram(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"[⚠️ Telegram Error] {e}")

def get_activity(address: str):
    try:
        resp = requests.get(
            f"https://data-api.polymarket.com/activity?user={address}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ERROR] Gagal ambil activity: {e}")
        return []

def load_last_activity():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def save_last_activity(activities):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(activities, f, indent=2, ensure_ascii=False)

def is_new_activity(old_activities, new_activities):
    """Deteksi apakah ada aktivitas baru berdasarkan timestamp dan amount."""
    if old_activities is None:
        return True
    
    # Ambil timestamp terbaru dari aktivitas lama
    old_latest = max([a.get("timestamp", "") for a in old_activities], default="")
    
    # Ambil timestamp terbaru dari aktivitas baru
    new_latest = max([a.get("timestamp", "") for a in new_activities], default="")
    
    # Jika timestamp terbaru berbeda → ada aktivitas baru
    if new_latest != old_latest:
        return True
    
    # Jika timestamp sama, cek jumlah aktivitas
    if len(new_activities) != len(old_activities):
        return True
    
    return False

def main():
    print(f"[INFO] Memantau aktivitas whale: {WHALE_NAME} ({WHALE_ADDRESS[:8]}...)")
    print(f"[INFO] Interval: {CHECK_INTERVAL} detik\n")

    last_activity = load_last_activity()

    while True:
        current_activity = get_activity(WHALE_ADDRESS)
        if not current_activity:
            time.sleep(CHECK_INTERVAL)
            continue

        if is_new_activity(last_activity, current_activity):
            print("\n" + "="*80)
            print(f"🚨 WHALE ALERT: {WHALE_NAME} BERGERAK!")
            print("="*80)
            
            # Tampilkan 5 transaksi terbaru
            for act in current_activity[:5]:
                side = act.get("side", "unknown")
                market = act.get("market", {}).get("question", "Unknown Market")
                outcome = act.get("outcome", "?")
                amount = float(act.get("amount", 0))
                price = float(act.get("price", 0))
                usd_value = round(amount * price, 2)
                timestamp = act.get("timestamp", "")
                
                action = "🟢 BUY" if side == "buy" else "🔴 SELL"
                print(f"{action} | {market}")
                print(f"      Outcome: {outcome} | Amount: {amount:.2f} | Price: ${price:.4f} | Value: ${usd_value:.2f}")
                print(f"      Time: {timestamp}")
                print("-" * 80)
            
            # Kirim ke Telegram
            msg = f"🐋 <b>{WHALE_NAME}</b> baru saja bertransaksi!\n"
            for act in current_activity[:5]:
                side = act.get("side", "unknown")
                market = act.get("market", {}).get("question", "Unknown Market")
                outcome = act.get("outcome", "?")
                amount = float(act.get("amount", 0))
                price = float(act.get("price", 0))
                usd_value = round(amount * price, 2)
                action = "🟢 Buy" if side == "buy" else "🔴 Sell"
                msg += f"• <b>{action}</b> {market}\n"
                msg += f"  → {outcome} | {amount:.2f} @ ${price:.4f} = ${usd_value:.2f}\n"
            if len(current_activity) > 5:
                msg += f"\n... dan {len(current_activity)-5} transaksi lainnya"
            send_telegram(msg)
            
            # Simpan snapshot terbaru
            save_last_activity(current_activity)
            last_activity = current_activity

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
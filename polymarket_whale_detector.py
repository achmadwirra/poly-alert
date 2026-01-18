import requests
import time
from typing import Optional

# === Konfigurasi ===
MARKET_ID = "@PurpleThunderBicycleMountain"  # Ganti dengan market ID yang Anda pantau
THRESHOLD_PCT = 10.0  # Persentase perubahan volume yang dianggap "whale"
CHECK_INTERVAL = 30   # Detik antar pemindaian

POLYMARKET_API_BASE = "https://api.polymarket.com"

def get_orderbook(market_id: str):
    """Ambil orderbook publik dari Polymarket (tanpa API key)."""
    url = f"{POLYMARKET_API_BASE}/markets/{market_id}/orderbook"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Gagal ambil orderbook: {e}")
        return None

def calculate_total_volume(orders: list) -> float:
    """Hitung total volume dari daftar order [price, amount]."""
    return sum(float(amount) for _, amount in orders)

def monitor_whale(market_id: str, threshold_pct: float = 10.0, interval: int = 30):
    print(f"[INFO] Memulai pemantauan whale di market: {market_id}")
    print(f"[INFO] Threshold: {threshold_pct}%, Interval: {interval} detik\n")

    prev_bids_vol = 0.0
    prev_asks_vol = 0.0
    first_run = True

    while True:
        data = get_orderbook(market_id)
        if not data:
            time.sleep(interval)
            continue

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        current_bids_vol = calculate_total_volume(bids)
        current_asks_vol = calculate_total_volume(asks)

        if first_run:
            prev_bids_vol = current_bids_vol
            prev_asks_vol = current_asks_vol
            first_run = False
            print(f"[INIT] Snapshot awal: Bids={current_bids_vol:.2f}, Asks={current_asks_vol:.2f}")
            time.sleep(interval)
            continue

        # Hitung persentase perubahan
        bid_change = abs(current_bids_vol - prev_bids_vol) / prev_bids_vol * 100 if prev_bids_vol > 0 else 0
        ask_change = abs(current_asks_vol - prev_asks_vol) / prev_asks_vol * 100 if prev_asks_vol > 0 else 0

        alert_triggered = False

        if bid_change >= threshold_pct:
            print("🚨 WHALE ALERT — BIDS MELONJAK!")
            print(f"   Perubahan: +{bid_change:.2f}%")
            print(f"   Sebelum: {prev_bids_vol:.2f} → Sekarang: {current_bids_vol:.2f}")
            alert_triggered = True

        if ask_change >= threshold_pct:
            print("🚨 WHALE ALERT — ASKS MELONJAK!")
            print(f"   Perubahan: +{ask_change:.2f}%")
            print(f"   Sebelum: {prev_asks_vol:.2f} → Sekarang: {current_asks_vol:.2f}")
            alert_triggered = True

        if alert_triggered:
            print("-" * 50)

        # Update snapshot
        prev_bids_vol = current_bids_vol
        prev_asks_vol = current_asks_vol

        time.sleep(interval)

# === Cara Dapatkan MARKET_ID ===
# 1. Buka https://polymarket.com
# 2. Pilih pasar, misal: https://polymarket.com/event/.../market/0xabc123...
# 3. Salin bagian akhir URL setelah `/market/` → itu MARKET_ID Anda

if __name__ == "__main__":
    # Ganti MARKET_ID di atas sebelum jalankan!
    monitor_whale(MARKET_ID, THRESHOLD_PCT, CHECK_INTERVAL)
# Polymarket Whale Alert Bot 🐋

Bot Telegram untuk memantau aktivitas voting (BUY) dari whale Polymarket secara real-time.

## Fitur
- Pantau multiple whale
- Notifikasi Telegram instan
- Hanya tampilkan 2 aktivitas terbaru per whale
- Hindari duplikat notifikasi

## Setup
1. Salin `.env.example` ke `.env`
2. Isi `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID`
3. Tambahkan whale di `.env`
4. Jalankan: `python whale_buy_only.py`
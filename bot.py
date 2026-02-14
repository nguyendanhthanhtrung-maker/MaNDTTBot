import requests
import time
import re
from datetime import datetime, timedelta, timezone
import threading
from flask import Flask
import os

# --- CẤU HÌNH ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = str(os.getenv("CHAT_ID") or "7346983056") 
BASE_URL_PREFIX = "https://telegra.ph/NH%E1%BA%ACN-XU-BOT-DVK-"

def get_vn_time():
    return datetime.now(timezone.utc) + timedelta(hours=7)

status_info = {
    "current_index": 1,
    "current_date": get_vn_time().strftime("%m-%d"),
    "total_codes": 0,
    "last_code": "Chưa có"
}

app = Flask(__name__)

def send_tele(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
    except: pass

@app.route('/')
def home():
    return f"Bot Online - Page: {status_info['current_index']}"

# --- LUỒNG NGHE LỆNH (SỬA LỖI Ở ĐÂY) ---
def telegram_listener():
    last_id = 0
    print("--- ĐANG ĐỢI LỆNH TỪ TELEGRAM ---")
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_id+1}&timeout=20"
            response = requests.get(url, timeout=25).json()
            
            if "result" in response:
                for update in response["result"]:
                    last_id = update["update_id"]
                    
                    if "message" in update:
                        msg = update["message"]
                        text = msg.get("text", "")
                        from_id = str(msg.get("chat", {}).get("id", ""))
                        
                        # KIỂM TRA CHÍNH XÁC ID VÀ LỆNH
                        if from_id == CHAT_ID:
                            if text == "/status":
                                report = (f"🤖 **TRẠNG THÁI HIỆN TẠI**\n"
                                          f"📅 Ngày quét: `{status_info['current_date']}`\n"
                                          f"📂 Trang hiện tại: `{status_info['current_index']}`\n"
                                          f"🎁 Tổng mã: `{status_info['total_codes']}`\n"
                                          f"✨ Mã cuối: `{status_info['last_code']}`")
                                send_tele(report)
                            elif text == "/start":
                                send_tele("👋 Chào sếp! Bot săn xu DVK đã sẵn sàng. Gõ /status để xem tình hình.")
        except Exception as e:
            print(f"Lỗi listener: {e}")
        time.sleep(1)

# --- LUỒNG QUÉT MÃ ---
def bot_worker():
    sent_codes = set()
    while True:
        try:
            # Logic nhảy trang đa điểm
            for i in range(5, -1, -1):
                check_idx = status_info["current_index"] + i
                url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{check_idx}"
                res = requests.get(url, timeout=10)
                
                if res.status_code == 200:
                    if check_idx > status_info["current_index"]:
                        status_info["current_index"] = check_idx
                    
                    codes = re.findall(r'/nhapxu\s+([a-zA-Z0-9\-_]+)', res.text, re.IGNORECASE)
                    for c in codes:
                        full = f"/nhapxu {c}"
                        if full not in sent_codes:
                            send_tele(f"🎁 **Mã mới (Trang {check_idx}):**\n`{full}`")
                            sent_codes.add(full)
                            status_info["total_codes"] += 1
                            status_info["last_code"] = full
                    break
        except: pass
        time.sleep(40)

if __name__ == "__main__":
    threading.Thread(target=bot_worker, daemon=True).start()
    threading.Thread(target=telegram_listener, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

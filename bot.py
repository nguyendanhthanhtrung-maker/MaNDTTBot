import requests
import time
import re
from datetime import datetime, timedelta, timezone
import threading
from flask import Flask
import os

# --- CẤU HÌNH ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "7346983056"
BASE_URL_PREFIX = "https://telegra.ph/NH%E1%BA%ACN-XU-BOT-DVK-"

# Lấy giờ Việt Nam chuẩn
def get_vn_time():
    return datetime.now(timezone.utc) + timedelta(hours=7)

status_info = {
    "current_index": 1, 
    "current_date": get_vn_time().strftime("%m-%d"),
    "total_codes_found": 0,
    "last_code": "Chưa có"
}

app = Flask(__name__)

@app.route('/')
def index():
    vn_now = get_vn_time().strftime("%H:%M:%S")
    return f"Bot Source Reader Online | VN: {vn_now} | Page: {status_info['current_date']}-{status_info['current_index']}"

@app.route('/ping')
def ping():
    return {"status": "alive"}, 200

# --- LOGIC QUÉT MÃ NGUỒN ---
def bot_worker():
    sent_codes = set()
    print("--- BOT SOURCE READER STARTED ---")
    
    while True:
        try:
            # 1. Tự động đổi ngày theo giờ VN
            now_date = get_vn_time().strftime("%m-%d")
            if now_date != status_info["current_date"]:
                status_info["current_date"] = now_date
                status_info["current_index"] = 1
                sent_codes.clear()
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                             data={'chat_id': CHAT_ID, 'text': f"📅 Ngày mới: {now_date}. Bắt đầu quét từ trang 1."})

            # 2. Truy cập URL
            url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{status_info['current_index']}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # Lấy trực tiếp mã nguồn (Raw HTML)
                html_source = response.text
                
                # Quét Regex trực tiếp trên Source Code
                # Lấy cụm /nhapxu và mã phía sau (không quan tâm thẻ HTML bao quanh)
                matches = re.findall(r'/nhapxu\s+([a-zA-Z0-9\-_]+)', html_source, re.IGNORECASE)
                
                for code_only in matches:
                    full_cmd = f"/nhapxu {code_only}"
                    if full_cmd not in sent_codes:
                        # Gửi mã về Telegram
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                     data={
                                         'chat_id': CHAT_ID, 
                                         'text': f"🎁 **Tìm thấy mã trong Source:**\n`{full_cmd}`", 
                                         'parse_mode': 'Markdown'
                                     })
                        sent_codes.add(full_cmd)
                        status_info["total_codes_found"] += 1
                        status_info["last_code"] = full_cmd

            # 3. Tự động nhảy trang (Index + 1)
            next_idx = status_info["current_index"] + 1
            next_url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{next_idx}"
            
            # Kiểm tra nhanh trang kế tiếp
            if requests.get(next_url, timeout=5).status_code == 200:
                status_info["current_index"] = next_idx
                print(f"Nhảy sang trang: {next_idx}")
                continue # Quét luôn không chờ
                
        except Exception as e:
            print(f"Lỗi: {e}")
        
        time.sleep(60)

if __name__ == "__main__":
    # Luồng xử lý lệnh /status đơn giản
    def telegram_listener():
        last_id = 0
        while True:
            try:
                r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_id+1}&timeout=30").json()
                for u in r.get("result", []):
                    last_id = u["update_id"]
                    if u.get("message", {}).get("text") == "/status":
                        msg = f"📂 Đang quét: `{status_info['current_date']}-{status_info['current_index']}`\n🎁 Tổng mã: `{status_info['total_codes_found']}`"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'})
            except: pass
            time.sleep(2)

    threading.Thread(target=bot_worker, daemon=True).start()
    threading.Thread(target=telegram_listener, daemon=True).start()
    
    # Chạy Web Server cho Render
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
    

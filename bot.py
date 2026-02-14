import requests
import time
import re
from datetime import datetime, timedelta, timezone
import threading
from flask import Flask
import os

# --- CẤU HÌNH ---
# Render sẽ lấy Token từ Environment Variables (Biến môi trường)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "7346983056"
BASE_URL_PREFIX = "https://telegra.ph/NH%E1%BA%ACN-XU-BOT-DVK-"

# Hàm lấy giờ Việt Nam (GMT+7)
def get_vn_time():
    return datetime.now(timezone.utc) + timedelta(hours=7)

status_info = {
    "current_index": 1, 
    "current_date": get_vn_time().strftime("%m-%d"),
    "total_codes_found": 0,
    "last_code": "Chưa có",
    "bot_start": get_vn_time().strftime("%d/%m %H:%M")
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

            # 2. Truy cập và đọc mã nguồn (Raw HTML)
            url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{status_info['current_index']}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                html_source = response.text # Đây là mã nguồn thô
                
                # Quét Regex lấy cụm /nhapxu và mã phía sau
                matches = re.findall(r'(/nhapxu\s+[a-zA-Z0-9\-_]+)', html_source, re.IGNORECASE)
                
                for full_cmd in matches:
                    if full_cmd not in sent_codes:
                        # Gửi mã về Telegram
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                     data={
                                         'chat_id': CHAT_ID, 
                                         'text': f"🎁 **Tìm thấy mã mới:**\n`{full_cmd}`", 
                                         'parse_mode': 'Markdown'
                                     })
                        sent_codes.add(full_cmd)
                        status_info["total_codes_found"] += 1
                        status_info["last_code"] = full_cmd

            # 3. LOGIC TỰ ĐỔI TRANG (Nhảy Index)
            next_idx = status_info["current_index"] + 1
            next_url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{next_idx}"
            
            try:
                if requests.get(next_url, timeout=5).status_code == 200:
                    status_info["current_index"] = next_idx
                    print(f"Nhảy sang trang mới: {next_idx}")
                    continue # Quét ngay lập tức trang mới
            except:
                pass
                
        except Exception as e:
            print(f"Lỗi: {e}")
        
        time.sleep(60)

# --- LUỒNG NGHE LỆNH /status ---
def telegram_listener():
    last_id = 0
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_id+1}&timeout=30").json()
            for u in r.get("result", []):
                last_id = u["update_id"]
                msg_obj = u.get("message", {})
                if msg_obj.get("text") == "/status" and str(msg_obj.get("chat", {}).get("id")) == CHAT_ID:
                    report = (f"🤖 **BÁO CÁO BOT DVK**\n"
                              f"📂 Đang quét: `{status_info['current_date']}-{status_info['current_index']}`\n"
                              f"🎁 Mã gần nhất: `{status_info['last_code']}`\n"
                              f"📊 Tổng mã tìm thấy: `{status_info['total_codes_found']}`\n"
                              f"🚀 Khởi động lúc: `{status_info['bot_start']}`")
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                 data={'chat_id': CHAT_ID, 'text': report, 'parse_mode': 'Markdown'})
        except: pass
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=bot_worker, daemon=True).start()
    threading.Thread(target=telegram_listener, daemon=True).start()
    
    # Render yêu cầu PORT từ biến môi trường
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

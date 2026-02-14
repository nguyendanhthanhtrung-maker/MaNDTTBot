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

def get_vn_time():
    return datetime.now(timezone.utc) + timedelta(hours=7)

status_info = {
    "current_index": 1, 
    "current_date": get_vn_time().strftime("%m-%d"),
    "total_codes_found": 0,
    "last_code": "Chưa có"
}

app = Flask(__name__)

# --- HÀM GỬI TIN NHẮN AN TOÀN ---
def send_tele_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code != 200:
            print(f"❌ Lỗi Telegram: {res.text}")
        return res.status_code == 200
    except Exception as e:
        print(f"⚠️ Không thể kết nối Telegram: {e}")
        return False

@app.route('/')
def index():
    return f"Bot Status: Online | Page: {status_info['current_date']}-{status_info['current_index']}"

@app.route('/ping')
def ping():
    return {"status": "alive"}, 200

# --- LOGIC QUÉT MÃ ---
def bot_worker():
    sent_codes = set()
    # Gửi thông báo khởi động để kiểm tra bot có quyền gửi tin không
    send_tele_message("🚀 **Bot đã khởi động thành công và đang bắt đầu quét!**")
    
    while True:
        try:
            now_date = get_vn_time().strftime("%m-%d")
            if now_date != status_info["current_date"]:
                status_info["current_date"] = now_date
                status_info["current_index"] = 1
                sent_codes.clear()

            found_any = False
            # Dò tìm trong phạm vi 10 trang kế tiếp
            for i in range(10, -1, -1):
                check_idx = status_info["current_index"] + i
                url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{check_idx}"
                
                try:
                    response = requests.get(url, timeout=5, headers={'Cache-Control': 'no-cache'})
                    if response.status_code == 200:
                        if check_idx > status_info["current_index"]:
                            status_info["current_index"] = check_idx
                        
                        html_source = response.text
                        matches = re.findall(r'(/nhapxu\s+[a-zA-Z0-9\-_]+)', html_source, re.IGNORECASE)
                        
                        for full_cmd in matches:
                            if full_cmd not in sent_codes:
                                # Nếu gửi thành công mới thêm vào bộ nhớ đã gửi
                                if send_tele_message(f"🎁 **Mã mới (Trang {check_idx}):**\n`{full_cmd}`"):
                                    sent_codes.add(full_cmd)
                                    status_info["total_codes_found"] += 1
                                    status_info["last_code"] = full_cmd
                        
                        found_any = True
                        break 
                except: continue

        except Exception as e:
            print(f"Lỗi Worker: {e}")
        
        time.sleep(30 if found_any else 60)

# --- LUỒNG NGHE LỆNH ---
def telegram_listener():
    last_id = 0
    while True:
        try:
            # Dùng getUpdates để nhận lệnh /status
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_id+1}&timeout=30", timeout=35).json()
            for u in r.get("result", []):
                last_id = u["update_id"]
                msg = u.get("message", {})
                if msg.get("text") == "/status" and str(msg.get("chat", {}).get("id")) == CHAT_ID:
                    report = (f"🤖 **BÁO CÁO**\n"
                              f"📂 Trang: `{status_info['current_date']}-{status_info['current_index']}`\n"
                              f"🎁 Tổng mã: `{status_info['total_codes_found']}`")
                    send_tele_message(report)
        except: pass
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=bot_worker, daemon=True).start()
    threading.Thread(target=telegram_listener, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

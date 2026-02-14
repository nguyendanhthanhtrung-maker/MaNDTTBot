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
    "last_code": "Chưa có",
    "bot_start": get_vn_time().strftime("%d/%m %H:%M")
}

app = Flask(__name__)

@app.route('/')
def index():
    vn_now = get_vn_time().strftime("%H:%M:%S")
    return f"Bot Online | VN: {vn_now} | Page: {status_info['current_date']}-{status_info['current_index']}"

@app.route('/ping')
def ping():
    return {"status": "alive"}, 200

# --- LOGIC QUÉT MÃ NGUỒN TỐI ƯU ---
def bot_worker():
    sent_codes = set()
    print("--- BOT STARTED ---")
    
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

            # 2. DÒ TÌM TRANG MỚI NHẤT (Kiểm tra từ xa về gần để tránh kẹt)
            found_any_page = False
            # Dò trong phạm vi 10 trang kế tiếp để tránh admin nhảy số
            for i in range(10, -1, -1): 
                check_idx = status_info["current_index"] + i
                url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{check_idx}"
                
                try:
                    # Thêm headers để lấy data mới nhất từ server
                    response = requests.get(url, timeout=5, headers={'Cache-Control': 'no-cache'})
                    if response.status_code == 200:
                        # Cập nhật index nếu tìm thấy trang cao hơn
                        if check_idx > status_info["current_index"]:
                            status_info["current_index"] = check_idx
                            print(f"🚀 Đã nhảy tới trang mới: {check_idx}")

                        # Quét mã nguồn trang này
                        html_source = response.text
                        matches = re.findall(r'(/nhapxu\s+[a-zA-Z0-9\-_]+)', html_source, re.IGNORECASE)
                        
                        for full_cmd in matches:
                            if full_cmd not in sent_codes:
                                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                             data={
                                                 'chat_id': CHAT_ID, 
                                                 'text': f"🎁 **Mã mới (Trang {check_idx}):**\n`{full_cmd}`", 
                                                 'parse_mode': 'Markdown'
                                             })
                                sent_codes.add(full_cmd)
                                status_info["total_codes_found"] += 1
                                status_info["last_code"] = full_cmd
                        
                        found_any_page = True
                        break # Tìm thấy trang cao nhất rồi thì dừng vòng lặp dò tìm
                except:
                    continue
                    
        except Exception as e:
            print(f"Lỗi hệ thống: {e}")
        
        # Nếu tìm thấy trang/mã thì quét nhanh (20s), nếu không thì quét chậm (45s)
        time.sleep(20 if found_any_page else 45)

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
                    report = (f"🤖 **BÁO CÁO TRẠNG THÁI**\n"
                              f"📂 Đang quét: `{status_info['current_date']}-{status_info['current_index']}`\n"
                              f"🎁 Mã gần nhất: `{status_info['last_code']}`\n"
                              f"📊 Tổng mã đã hốt: `{status_info['total_codes_found']}`")
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                 data={'chat_id': CHAT_ID, 'text': report, 'parse_mode': 'Markdown'})
        except: pass
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=bot_worker, daemon=True).start()
    threading.Thread(target=telegram_listener, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

import requests
from bs4 import BeautifulSoup
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

# Hàm lấy giờ Việt Nam chuẩn (GMT+7) bất kể server ở đâu
def get_vn_time():
    utc_now = datetime.now(timezone.utc)
    vn_now = utc_now + timedelta(hours=7)
    return vn_now

status_info = {
    "current_index": 1, 
    "current_date": get_vn_time().strftime("%m-%d"),
    "total_codes_found": 0,
    "last_code": "Chưa có"
}

app = Flask(__name__)

@app.route('/')
def index():
    vn_now = get_vn_time().strftime("%d/%m %H:%M:%S")
    return f"Bot DVK Online | VN Time: {vn_now} | Ngay: {status_info['current_date']} | Trang: {status_info['current_index']}"

@app.route('/ping')
def ping():
    return {"status": "alive"}, 200

# --- LUỒNG QUÉT MÃ TỰ ĐỘNG ---
def bot_worker():
    sent_codes = set()
    print(f"--- BOT STARTED | DATE: {status_info['current_date']} ---")
    
    while True:
        try:
            # 1. Kiểm tra đổi ngày theo giờ Việt Nam
            now_vn = get_vn_time()
            now_date = now_vn.strftime("%m-%d")
            
            if now_date != status_info["current_date"]:
                print(f"Chuyển ngày: {status_info['current_date']} -> {now_date}")
                status_info["current_date"] = now_date
                status_info["current_index"] = 1
                sent_codes.clear()
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                             data={'chat_id': CHAT_ID, 'text': f"📅 **Hệ thống chuyển ngày VN:** {now_date}\nBắt đầu lại từ trang 1."})

            # 2. Quét trang hiện tại
            url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{status_info['current_index']}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                article = soup.find('article')
                if article:
                    content = article.get_text(separator="\n")
                    matches = re.findall(r'(/nhapxu\s+[a-zA-Z0-9\-_]+)', content, re.IGNORECASE)
                    for full_cmd in matches:
                        if full_cmd not in sent_codes:
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                         data={'chat_id': CHAT_ID, 
                                               'text': f"🎁 **Mã mới:**\n`{full_cmd}`", 
                                               'parse_mode': 'Markdown'})
                            sent_codes.add(full_cmd)
                            status_info["total_codes_found"] += 1
                            status_info["last_code"] = full_cmd

            # 3. LOGIC TỰ ĐỔI TRANG (INDEX + 1)
            # Thử kiểm tra xem trang kế tiếp có tồn tại không
            next_idx = status_info["current_index"] + 1
            next_url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{next_idx}"
            
            try:
                next_check = requests.get(next_url, timeout=5)
                # Nếu trang tiếp theo trả về 200 (tồn tại), nhảy index ngay
                if next_check.status_code == 200:
                    status_info["current_index"] = next_idx
                    print(f"Phát hiện trang mới: {next_idx}")
                    # Không sleep, quay lại vòng lặp để quét ngay trang mới
                    continue 
            except:
                pass

        except Exception as e:
            print(f"Lỗi: {e}")
        
        # Nghỉ 60 giây nếu chưa có trang mới
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

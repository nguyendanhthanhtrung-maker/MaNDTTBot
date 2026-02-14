import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
import threading
from flask import Flask
import os

# --- CẤU HÌNH ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "7346983056"
BASE_URL_PREFIX = "https://telegra.ph/NH%E1%BA%ACN-XU-BOT-DVK-"

app = Flask(__name__)

# --- WEB GIAO DIỆN (Để Render không tắt) ---
@app.route('/')
def index():
    # Lấy định dạng tháng-ngày hiện tại để hiển thị lên web kiểm tra
    now_str = datetime.now().strftime("%m-%d")
    return f"Bot đang chạy ngày: {now_str} | Chat ID: {CHAT_ID}"

@app.route('/ping')
def ping():
    return {"status": "alive"}, 200

# --- LOGIC QUÉT MÃ ---
def bot_worker():
    current_index = 1
    # Lấy tháng-ngày hiện tại (Ví dụ: 02-14)
    current_date = datetime.now().strftime("%m-%d")
    sent_codes = set()
    
    print(f"--- BOT STARTED | DATE: {current_date} ---")
    
    while True:
        try:
            # Kiểm tra xem máy chủ đã sang ngày mới chưa để đổi URL
            now_date = datetime.now().strftime("%m-%d")
            if now_date != current_date:
                current_date = now_date
                current_index = 1
                sent_codes.clear()
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                             data={'chat_id': CHAT_ID, 'text': f"📅 Đã sang ngày mới: {current_date}\nBot bắt đầu quét từ trang 1."})

            # Tạo URL đúng định dạng: PREFIX + THÁNG-NGÀY + INDEX
            # Kết quả: https://telegra.ph/NHẬN-XU-BOT-DVK-02-14-1
            url = f"{BASE_URL_PREFIX}{current_date}-{current_index}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                article = soup.find('article')
                if article:
                    content = article.get_text(separator="\n")
                    for line in content.split("\n"):
                        if "/nhapxu" in line.lower():
                            parts = re.split(r'/nhapxu\s*', line, flags=re.IGNORECASE)
                            if len(parts) > 1:
                                code = parts[1].strip().split()[0]
                                if code not in sent_codes:
                                    # Gửi về Telegram (Bấm vào mã để copy)
                                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                                 data={
                                                     'chat_id': CHAT_ID, 
                                                     'text': f"🎁 **Mã {current_date} (Trang {current_index}):**\n`{code}`", 
                                                     'parse_mode': 'Markdown'
                                                 })
                                    sent_codes.add(code)

            # Thử dò trang tiếp theo (ví dụ từ 1 lên 2)
            next_idx = current_index + 1
            next_url = f"{BASE_URL_PREFIX}{current_date}-{next_idx}"
            try:
                if requests.get(next_url, timeout=5).status_code == 200:
                    current_index = next_idx
                    continue # Quét ngay trang mới không cần chờ
            except:
                pass

        except Exception as e:
            print(f"Lỗi: {e}")
        
        # Nghỉ 60 giây trước khi quét lại
        time.sleep(60)

if __name__ == "__main__":
    # Chạy luồng quét ngầm
    threading.Thread(target=bot_worker, daemon=True).start()
    
    # Chạy Web Server cho Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

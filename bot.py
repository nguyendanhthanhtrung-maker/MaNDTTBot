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

# Biến toàn cục để theo dõi
status_info = {
    "current_index": 1, 
    "current_date": datetime.now().strftime("%m-%d"),
    "total_codes_found": 0,
    "last_code": "Chưa có"
}

app = Flask(__name__)

@app.route('/')
def index():
    now_str = datetime.now().strftime("%d/%m %H:%M:%S")
    return f"Bot DVK Online | Ngay: {status_info['current_date']} | Trang: {status_info['current_index']} | Update: {now_str}"

@app.route('/ping')
def ping():
    return {"status": "alive"}, 200

# --- LUỒNG XỬ LÝ LỆNH /status ---
def handle_telegram_updates():
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            response = requests.get(url, timeout=35).json()
            if "result" in response:
                for update in response["result"]:
                    last_update_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"]
                        if str(update["message"]["chat"]["id"]) == CHAT_ID and text == "/status":
                            msg = (f"🤖 **TRẠNG THÁI BOT SĂN XU**\n"
                                   f"📅 Ngày: `{status_info['current_date']}`\n"
                                   f"📂 Đang quét trang: `{status_info['current_index']}`\n"
                                   f"🎁 Lệnh mới nhất: `{status_info['last_code']}`\n"
                                   f"📊 Tổng mã đã săn: `{status_info['total_codes_found']}`")
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                         data={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'})
        except: pass
        time.sleep(2)

# --- LUỒNG QUÉT MÃ TỰ ĐỘNG ---
def bot_worker():
    sent_codes = set()
    print(f"--- BOT STARTED ---")
    
    while True:
        try:
            # 1. Kiểm tra đổi ngày
            now_date = datetime.now().strftime("%m-%d")
            if now_date != status_info["current_date"]:
                status_info["current_date"] = now_date
                status_info["current_index"] = 1
                sent_codes.clear()
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                             data={'chat_id': CHAT_ID, 'text': f"📅 **Hệ thống chuyển ngày:** {status_info['current_date']}\nBắt đầu dò từ trang 1."})

            # 2. Quét trang hiện tại
            url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{status_info['current_index']}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                article = soup.find('article')
                if article:
                    content = article.get_text(separator="\n")
                    # Regex lấy cả cụm /nhapxu và mã phía sau
                    matches = re.findall(r'(/nhapxu\s+[a-zA-Z0-9\-_]+)', content, re.IGNORECASE)
                    for full_cmd in matches:
                        if full_cmd not in sent_codes:
                            # GỬI MÃ MỚI VỀ TELEGRAM
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                         data={'chat_id': CHAT_ID, 
                                               'text': f"🎁 **Cập nhật mã mới:**\n`{full_cmd}`", 
                                               'parse_mode': 'Markdown'})
                            sent_codes.add(full_cmd)
                            status_info["total_codes_found"] += 1
                            status_info["last_code"] = full_cmd

            # 3. Kiểm tra xem có trang tiếp theo (index + 1) chưa
            next_idx = status_info["current_index"] + 1
            next_url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{next_idx}"
            try:
                # Kiểm tra nhanh tiêu đề trang tiếp theo
                if requests.get(next_url, timeout=5).status_code == 200:
                    status_info["current_index"] = next_idx
                    print(f"Đã nhảy sang trang {next_idx}")
                    continue # Quét ngay trang mới
            except:
                pass

        except Exception as e:
            print(f"Lỗi: {e}")
        
        # Nghỉ 60 giây để tránh bị Telegra.ph chặn IP
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_worker, daemon=True).start()
    threading.Thread(target=handle_telegram_updates, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

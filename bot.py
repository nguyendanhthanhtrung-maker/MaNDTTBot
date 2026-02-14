import requests
import time
import re
from datetime import datetime, timedelta, timezone
import threading
from flask import Flask
import os

# --- CẤU HÌNH CỨNG (Thử dán trực tiếp token vào đây nếu lấy từ os.getenv không được) ---
BOT_TOKEN = os.getenv("BOT_TOKEN") or "7880992388:AAHT3H8B6W3_j_U6NBy2H7eI4_4n19V01y0"
CHAT_ID = "7346983056" 
BASE_URL_PREFIX = "https://telegra.ph/NH%E1%BA%ACN-XU-BOT-DVK-"

def get_vn_time():
    return datetime.now(timezone.utc) + timedelta(hours=7)

status_info = {
    "current_index": 1,
    "current_date": get_vn_time().strftime("%m-%d"),
    "logs": "Bot đang khởi động..."
}

app = Flask(__name__)

def send_debug_tele(text):
    """Hàm gửi tin nhắn có báo lỗi chi tiết ra console"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
        print(f"[Telegram] Gửi tin: {r.status_code} - {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"[Telegram] Lỗi kết nối: {e}")
        return False

@app.route('/')
def home():
    return f"<h1>Bot Status</h1><p>{status_info['logs']}</p><p>Page: {status_info['current_date']}-{status_info['current_index']}</p>"

def bot_worker():
    sent_codes = set()
    # Thử gửi 1 tin kiểm tra ngay khi chạy
    send_debug_tele("🔔 **Bot bắt đầu quét mã nguồn...** Nếu bạn thấy tin này, Telegram đã OK!")
    
    while True:
        try:
            now_date = get_vn_time().strftime("%m-%d")
            if now_date != status_info["current_date"]:
                status_info["current_date"] = now_date
                status_info["current_index"] = 1
                sent_codes.clear()

            # DÒ TRANG: Quét từ trang hiện tại lên +10 trang nữa
            for check_idx in range(status_info["current_index"], status_info["current_index"] + 11):
                url = f"{BASE_URL_PREFIX}{status_info['current_date']}-{check_idx}"
                print(f"🔍 Đang soi mã nguồn: {url}")
                
                try:
                    res = requests.get(url, timeout=10)
                    if res.status_code == 200:
                        # Nếu tìm thấy trang mới cao hơn, cập nhật ngay
                        if check_idx > status_info["current_index"]:
                            status_info["current_index"] = check_idx
                            send_debug_tele(f"📂 Đã tự động nhảy sang trang: {check_idx}")

                        source = res.text
                        # Tìm mã /nhapxu
                        codes = re.findall(r'/nhapxu\s+([a-zA-Z0-9\-_]+)', source, re.IGNORECASE)
                        for c in codes:
                            cmd = f"/nhapxu {c}"
                            if cmd not in sent_codes:
                                if send_debug_tele(f"🎁 **Mã mới:**\n`{cmd}`"):
                                    sent_codes.add(cmd)
                        
                        status_info["logs"] = f"Đang quét trang {check_idx} thành công."
                    else:
                        # Nếu trang không tồn tại, bỏ qua dò trang này
                        continue
                except Exception as e:
                    print(f"Lỗi khi tải trang {check_idx}: {e}")

        except Exception as e:
            print(f"Lỗi worker: {e}")
        
        time.sleep(30) # Nghỉ 30 giây mỗi vòng lặp

if __name__ == "__main__":
    threading.Thread(target=bot_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

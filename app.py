#!/usr/bin/env python3
"""
柴師傅 - 機車維修估價 LINE 機器人
簡化版 - 直接處理所有請求
"""

import os
import json
import sqlite3
from flask import Flask, request
from linebot import LineBotApi
from linebot.models import TextSendMessage

app = Flask(__name__)

# 載入環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

print(f"[INIT] TOKEN長度: {len(LINE_CHANNEL_ACCESS_TOKEN)}")
print(f"[INIT] SECRET長度: {len(LINE_CHANNEL_SECRET)}")
print(f"[INIT] GEMINI長度: {len(GEMINI_API_KEY)}")

# 初始化 LINE Bot
line_bot_api = None
if LINE_CHANNEL_ACCESS_TOKEN:
    try:
        line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        print("[INIT] LINE Bot API 初始化成功")
    except Exception as e:
        print(f"[INIT] LINE Bot API 初始化失敗: {e}")

# 資料庫路徑
DB_PATH = os.path.join(os.path.dirname(__file__), 'moto_repair.db')

# ============ 資料庫 ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        symptom TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    print("[INIT] 資料庫初始化完成")

# ============ 診斷邏輯 ============
def diagnose(text):
    """簡易診斷"""
    text_lower = text.lower()
    
    if any(k in text_lower for k in ["價格", "多少錢", "費用"]):
        return """💰 常見維修參考價格

電系類：
• 電瓶更換：$800 - $1,500
• 啟動馬達：$1,500 - $3,000

傳動類：
• 普利珠：$800 - $1,500
• 離合器：$1,200 - $2,500

煞車類：
• 來令片：$300 - $800
• 煞車油：$200 - $400

引擎類：
• 換機油：$300 - $600
• 空濾更換：$200 - $500

⚠️ 以上為參考價，實際以維修廠報價為準"""

    elif any(k in text_lower for k in ["廠商", "推薦", "附近"]):
        return """🏍️ 推薦維修廠

✅ 順欣車業
   ⭐ 4.5 (128 則評價)
   📍 台北市中山區南京東路三段 100 號
   📞 02-25001234

✅ 大台北機車
   ⭐ 4.7 (256 則評價)
   📍 台北市大安區羅斯福路三段 50 號
   📞 02-23651234

✅ 老張機車
   ⭐ 4.8 (312 則評價)
   📍 新北市中和區中山路三段 120 號
   📞 02-29456789"""

    elif any(k in text_lower for k in ["幫助", "說明", "功能", "使用"]):
        return """🏍️ 柴師傅使用說明

【快速診斷】
直接描述您的機車問題，例如：
• 「發不動，有喀喀聲」
• 「起步有異音」
• 「煞車變很軟」

【功能選單】
🔧 症狀診斷 — AI 智能分析問題
💰 價格查詢 — 常見維修價目表
🏪 附近廠商 — 推薦合作維修廠
📋 維修紀錄 — 查看您的歷史紀錄
⭐ 評價回饋 — 給維修廠評分

⚠️ 以上為AI初步估價，實際價格以現場檢測為準"""

    elif any(k in text_lower for k in ["紀錄", "歷史"]):
        return "📋 您還沒有維修紀錄\n\n快去找柴師傅診斷吧！🔧"

    elif any(k in text_lower for k in ["評價", "打分", "回饋"]):
        return """⭐ 維修廠評價

請告訴我：
1. 您去了哪家維修廠？
2. 維修項目是什麼？
3. 實際花費多少？
4. 滿意度 1-5 星？

格式範例：
「大台北機車，換電瓶，1200元，5星」

小柴子會幫您記錄！📝"""

    else:
        # 預設診斷回覆
        return """🔧 柴師傅診斷報告

收到您的問題：「{text}」

💡 建議：
1. 請描述具體症狀（如：發不動、異音、漏油）
2. 告訴我您的車型和車齡
3. 我會給您初步估價和維修建議

【常用指令】
• 「價格查詢」— 查看參考價格
• 「附近廠商」— 推薦維修廠
• 「使用說明」— 查看功能列表

⚠️ 以上為AI初步估價，實際費用以維修廠報價為準""".format(text=text)

# ============ Webhook 路由 ============

@app.route("/", methods=['GET'])
def hello():
    return "柴師傅機車維修估價機器人運作中！🏍️"

@app.route("/webhook", methods=['POST', 'GET'])
def webhook():
    """處理 LINE Webhook"""
    if request.method == 'GET':
        return 'Webhook is running! 🏍️', 200
    
    # 取得請求內容
    body = request.get_data(as_text=True)
    signature = request.headers.get('X-Line-Signature', '')
    
    print(f"[WEBHOOK] 收到請求")
    print(f"[WEBHOOK] Body: {body[:200]}")
    print(f"[WEBHOOK] Signature存在: {bool(signature)}")
    
    try:
        # 解析 JSON
        data = json.loads(body)
        
        if 'events' in data and len(data['events']) > 0:
            event = data['events'][0]
            
            # 檢查是否為文字訊息
            if event.get('type') == 'message' and event.get('message', {}).get('type') == 'text':
                user_id = event['source']['userId']
                text = event['message']['text']
                reply_token = event['replyToken']
                
                print(f"[MSG] 用戶: {user_id}, 訊息: {text}")
                
                # 記錄對話
                try:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute('INSERT INTO conversations (user_id, symptom) VALUES (?, ?)', (user_id, text))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"[DB] 記錄失敗: {e}")
                
                # 產生回覆
                reply = diagnose(text)
                
                # 發送回覆
                if line_bot_api and reply_token:
                    try:
                        line_bot_api.reply_message(
                            reply_token,
                            TextSendMessage(text=reply)
                        )
                        print(f"[MSG] 回覆已發送")
                    except Exception as e:
                        print(f"[MSG] 發送回覆失敗: {e}")
                else:
                    print(f"[MSG] 無法發送: line_bot_api={line_bot_api is not None}, reply_token={reply_token}")
            else:
                print(f"[MSG] 非文字訊息或無訊息")
        else:
            print(f"[WEBHOOK] 無事件")
            
    except json.JSONDecodeError as e:
        print(f"[WEBHOOK] JSON解析失敗: {e}")
    except Exception as e:
        print(f"[WEBHOOK] 處理錯誤: {e}")
        import traceback
        traceback.print_exc()
    
    # 始終回傳 200
    return 'OK', 200

# ============ 啟動 ============
if __name__ == "__main__":
    print("🚀 啟動柴師傅機車維修估價機器人...")
    init_db()
    print("✅ 準備完成！")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

#!/usr/bin/env python3
"""
柴師傅 - 機車維修估價 LINE 機器人
老柴老師的創業項目 MVP
"""

import os
import json
import sqlite3
import google.generativeai as genai
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction,
    LocationMessage, LocationSendMessage,
    TemplateSendMessage, ButtonsTemplate, URITemplateAction,
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent,
    CarouselContainer
)
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# 關閉 Flask 自動 JSON 解析，避免 400 錯誤
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# LINE Bot 設定 - 從環境變數讀取
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')

# 檢查環境變數
print(f"[INIT] LINE_TOKEN 長度: {len(LINE_CHANNEL_ACCESS_TOKEN)}")
print(f"[INIT] LINE_SECRET 長度: {len(LINE_CHANNEL_SECRET)}")

# Gemini 設定
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
print(f"[INIT] GEMINI_KEY 長度: {len(GEMINI_API_KEY)}")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("[INIT] Gemini 已設定")
else:
    print("[INIT] ⚠️ 沒有 Gemini API Key")

# 初始化 LINE Bot
if LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET:
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    print("[INIT] LINE Bot 已初始化")
else:
    print("[INIT] ⚠️ LINE 環境變數未設定！")
    line_bot_api = None
    handler = None

# 資料庫路徑 - 使用相對路徑，避免 Render 上路徑問題
DB_PATH = os.path.join(os.path.dirname(__file__), 'moto_repair.db')
print(f"[INIT] 資料庫路徑: {DB_PATH}")

# ============ 資料庫操作 ============

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 症狀關鍵字表
    c.execute('''
        CREATE TABLE IF NOT EXISTS symptoms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            category TEXT,
            possible_issues TEXT,
            price_low INTEGER,
            price_high INTEGER,
            probability INTEGER,
            parts TEXT,
            notes TEXT
        )
    ''')
    
    # 維修廠表
    c.execute('''
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            lat REAL,
            lng REAL,
            rating REAL DEFAULT 0,
            review_count INTEGER DEFAULT 0,
            specialties TEXT,
            is_verified BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # 對話紀錄
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            symptom TEXT,
            diagnosis TEXT,
            price_estimate TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 價格回報
    c.execute('''
        CREATE TABLE IF NOT EXISTS price_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            shop_id INTEGER,
            service TEXT,
            actual_price INTEGER,
            satisfaction INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 資料庫初始化完成")

def init_sample_data():
    """載入初始資料"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 檢查是否已有資料
    c.execute("SELECT COUNT(*) FROM symptoms")
    if c.fetchone()[0] > 0:
        conn.close()
        return
    
    # 載入症狀資料
    symptoms_data = [
        ("發不動", "電系", json.dumps(["電瓶沒電", "啟動馬達故障", "點火系統問題"]), 800, 1500, 70, json.dumps(["電瓶", "啟動馬達"]), "檢查電瓶電壓是否低於 12V"),
        ("發不動", "電系", json.dumps(["啟動馬達故障"]), 1500, 3000, 20, json.dumps(["啟動馬達", "碳刷"]), "聽到喀喀聲但引擎不轉"),
        ("發不動", "電系", json.dumps(["點火系統問題"]), 500, 1200, 10, json.dumps(["火星塞", "高壓線圈"]), "完全沒有發動聲音"),
        ("漏油", "引擎", json.dumps(["油封老化", "墊片破損", "油管破裂"]), 500, 1000, 50, json.dumps(["油封", "墊片"]), "停車後地面有油漬"),
        ("異音", "傳動", json.dumps(["普利珠磨損", "離合器打滑", "皮帶老化"]), 800, 1500, 40, json.dumps(["普利珠", "離合器"]), "起步或加速時有怪聲"),
        ("異音", "傳動", json.dumps(["離合器打滑"]), 1200, 2500, 35, json.dumps(["離合器片", "離合器彈簧"]), "轉速拉高但車速不上去"),
        ("煞車軟", "煞車", json.dumps(["煞車油不足", "來令片磨損", "碟盤變形"]), 300, 1500, 60, json.dumps(["煞車油", "來令片"]), "煞車拉桿壓到底才有效"),
        ("耗油", "引擎", json.dumps(["空氣濾清器堵塞", "噴油嘴積碳", "火星塞老化"]), 500, 2000, 45, json.dumps(["空濾", "噴油嘴"]), "油耗比平常多 30% 以上"),
        ("抖動", "引擎", json.dumps(["引擎腳老化", "傳動系統不平衡", "輪胎變形"]), 800, 2000, 40, json.dumps(["引擎腳", "普利盤"]), "怠速或行駛中明顯震動"),
        ("儀表板燈亮", "電系", json.dumps(["引擎故障燈", "機油燈", "電瓶燈"]), 500, 3000, 50, json.dumps(["診斷器檢測"]), "不同燈號代表不同問題"),
        ("輪胎沒氣", "輪胎", json.dumps(["胎壓不足", "輪胎破洞", "氣嘴漏氣"]), 50, 800, 70, json.dumps(["補胎片", "氣嘴"]), "先檢查是否有異物刺入"),
        ("排氣管冒白煙", "引擎", json.dumps(["汽缸墊片燒毀", "活塞環磨損"]), 3000, 8000, 60, json.dumps(["墊片", "活塞環"]), "嚴重問題，需儘快檢修"),
        ("電門轉了沒反應", "電系", json.dumps(["電門線斷裂", "控制器故障"]), 500, 2500, 50, json.dumps(["電門線", "控制器"]), "電動車常見問題"),
        ("充電充不飽", "電系", json.dumps(["充電器故障", "電瓶老化", "充電座接觸不良"]), 500, 2000, 55, json.dumps(["充電器", "電瓶"]), "充電時間比平常久很多"),
        ("方向燈不亮", "電系", json.dumps(["燈泡燒掉", "繼電器故障", "線路短路"]), 50, 500, 70, json.dumps(["燈泡", "繼電器"]), "先換燈泡試試看"),
    ]
    
    c.executemany('''
        INSERT INTO symptoms (keyword, category, possible_issues, price_low, price_high, probability, parts, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', symptoms_data)
    
    # 載入維修廠資料 (範例)
    shops_data = [
        ("順欣車業", "台北市中山區南京東路三段 100 號", "02-25001234", 25.052, 121.538, 4.5, 128, json.dumps(["電系", "引擎"]), 1),
        ("永盛機車行", "新北市板橋區文化路二段 200 號", "02-22567890", 25.015, 121.468, 4.2, 85, json.dumps(["傳動", "煞車"]), 1),
        ("大台北機車", "台北市大安區羅斯福路三段 50 號", "02-23651234", 25.018, 121.533, 4.7, 256, json.dumps(["電系", "引擎", "傳動"]), 1),
        ("捷運機車維修", "台北市信義區忠孝東路五段 80 號", "02-23456789", 25.041, 121.565, 4.0, 42, json.dumps(["輪胎", "煞車"]), 0),
        ("老張機車", "新北市中和區中山路三段 120 號", "02-29456789", 24.998, 121.478, 4.8, 312, json.dumps(["引擎", "電系", "傳動", "煞車"]), 1),
    ]
    
    c.executemany('''
        INSERT INTO shops (name, address, phone, lat, lng, rating, review_count, specialties, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', shops_data)
    
    conn.commit()
    conn.close()
    print("✅ 初始資料載入完成")

# ============ AI 診斷引擎 ============

def diagnose_symptom(symptom_text, bike_model="", bike_age=""):
    """
    簡易診斷引擎：關鍵字匹配 + 價格估算
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 關鍵字匹配
    keywords = ["發不動", "漏油", "異音", "煞車", "耗油", "抖動", "儀表板", "輪胎", "排氣管", "電門", "充電", "方向燈"]
    matched_keyword = None
    
    for kw in keywords:
        if kw in symptom_text:
            matched_keyword = kw
            break
    
    if not matched_keyword:
        return {
            "found": False,
            "message": "抱歉，我還不太確定您的問題 🤔\n\n可以描述更具體一點嗎？例如：\n• 發不動、有異音、漏油\n• 煞車軟、耗油、抖動\n• 儀表板燈亮、輪胎沒氣\n\n或告訴我您的車型和車齡，我會更準確！"
        }
    
    # 查詢資料庫
    c.execute('''
        SELECT category, possible_issues, price_low, price_high, probability, parts, notes
        FROM symptoms WHERE keyword = ? ORDER BY probability DESC
    ''', (matched_keyword,))
    
    results = c.fetchall()
    conn.close()
    
    if not results:
        return {"found": False, "message": "找不到相關資料，請換個說法試試看"}
    
    # 組裝診斷結果
    issues = []
    for row in results[:3]:  # 最多顯示 3 個
        category, possible_issues_json, price_low, price_high, probability, parts_json, notes = row
        issues.append({
            "category": category,
            "problems": json.loads(possible_issues_json),
            "price_low": price_low,
            "price_high": price_high,
            "probability": probability,
            "parts": json.loads(parts_json),
            "notes": notes
        })
    
    return {
        "found": True,
        "keyword": matched_keyword,
        "issues": issues,
        "bike_model": bike_model,
        "bike_age": bike_age
    }

# ============ Gemini AI 診斷 ============

def gemini_diagnose(symptom_text, bike_model="", bike_age=""):
    """使用 Google Gemini 進行智能診斷"""
    if not GEMINI_API_KEY:
        return None
    
    try:
        bike_info = f"\n車型：{bike_model}" if bike_model else ""
        bike_info += f"\n車齡：{bike_age}" if bike_age else ""
        
        prompt = f"""你是一位專業的機車維修技師，有20年經驗。請根據用戶描述的症狀進行初步診斷。

用戶描述：{symptom_text}{bike_info}

請用繁體中文回答，格式如下：
🔍 **初步診斷**：
[簡短說明最可能的問題]

💰 **估價範圍**：
- 零件費：$XXX - $XXX
- 工資：$XXX - $XXX
- 總計約：$XXX - $XXX

⚠️ **建議**：
[是否需要立即維修，或可以觀察]

🛠️ **可能維修項目**：
1. [項目1]
2. [項目2]

請務必提醒：此為AI初步估價，實際價格以現場檢測為準。"""

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=800
            )
        )
        
        return response.text
    except Exception as e:
        print(f"[GEMINI] 診斷錯誤: {e}")
        return None

# ============ 訊息格式化 ============

def format_diagnosis_reply(diagnosis):
    """格式化診斷回覆訊息"""
    if not diagnosis["found"]:
        return diagnosis["message"]
    
    keyword = diagnosis["keyword"]
    issues = diagnosis["issues"]
    
    reply = f"🔧 柴師傅診斷報告\n"
    reply += f"症狀：{keyword}\n"
    reply += f"{'='*30}\n\n"
    
    for i, issue in enumerate(issues, 1):
        problems = "、".join(issue["problems"])
        parts = "、".join(issue["parts"])
        
        reply += f"【可能 {i}】{problems}\n"
        reply += f"   機率：{issue['probability']}%\n"
        reply += f"   估價：${issue['price_low']:,} - ${issue['price_high']:,}\n"
        reply += f"   零件：{parts}\n"
        reply += f"   💡 {issue['notes']}\n\n"
    
    reply += f"{'='*30}\n"
    reply += "📍 想找附近維修廠？\n"
    reply += "輸入『附近廠商』或分享您的位置！\n\n"
    reply += "⚠️ 以上為參考價格，實際費用以維修廠報價為準"
    
    return reply

def get_nearby_shops(lat=25.033, lng=121.565, limit=3):
    """取得附近維修廠"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT name, address, phone, rating, review_count, specialties, is_verified
        FROM shops WHERE is_active = 1
        ORDER BY rating DESC, review_count DESC
        LIMIT ?
    ''', (limit,))
    
    shops = c.fetchall()
    conn.close()
    
    if not shops:
        return "目前暫無合作維修廠資料 😅"
    
    reply = "🏍️ 推薦維修廠\n"
    reply += f"{'='*30}\n\n"
    
    for shop in shops:
        name, address, phone, rating, review_count, specialties_json, is_verified = shop
        specialties = "、".join(json.loads(specialties_json))
        verified = "✅" if is_verified else ""
        
        reply += f"{verified} {name}\n"
        reply += f"   ⭐ {rating} ({review_count} 則評價)\n"
        reply += f"   📍 {address}\n"
        reply += f"   📞 {phone}\n"
        reply += f"   🔧 專長：{specialties}\n\n"
    
    return reply

def get_user_history(user_id):
    """取得用戶維修歷史"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT symptom, created_at FROM conversations 
        WHERE user_id = ? ORDER BY created_at DESC LIMIT 5
    ''', (user_id,))
    
    records = c.fetchall()
    conn.close()
    
    if not records:
        return "📋 您還沒有維修紀錄\n\n快去找柴師傅診斷吧！🔧"
    
    reply = "📋 您的維修紀錄\n"
    reply += f"{'='*30}\n\n"
    
    for i, (symptom, created_at) in enumerate(records, 1):
        reply += f"{i}. {symptom}\n"
        reply += f"   時間：{created_at}\n\n"
    
    return reply

# ============ LINE Bot 路由 ============

@app.route("/", methods=['GET', 'POST'])
def hello():
    if request.method == 'POST':
        return 'OK', 200
    return "柴師傅機車維修估價機器人運作中！🏍️"

@app.route("/test", methods=['GET', 'POST'])
def test():
    """測試端點"""
    return 'OK', 200

@app.route("/webhook", methods=['POST', 'GET'])
def webhook():
    """LINE Webhook 接收訊息"""
    if request.method == 'GET':
        return 'Webhook is running! 🏍️', 200
    
    # 手動取得 raw body，避免 Flask 自動解析 JSON
    body = request.get_data(as_text=True)
    signature = request.headers.get('X-Line-Signature', '')
    
    # 記錄請求以便除錯
    print(f"[WEBHOOK] Received request, body length: {len(body)}, signature present: {bool(signature)}")
    
    # 沒有 signature 也回 200（LINE 測試用）
    if not signature:
        print("[WEBHOOK] No signature, returning 200")
        return 'OK', 200
    
    # 如果 handler 沒初始化，直接回 200
    if not handler:
        print("[WEBHOOK] Handler not initialized, returning 200")
        return 'OK', 200
    
    try:
        handler.handle(body, signature)
        print("[WEBHOOK] Handler processed successfully")
    except InvalidSignatureError:
        # Signature 錯誤也回 200，但記錄下來
        print(f"[WEBHOOK] Invalid signature, but returning 200 to keep LINE connected")
    except Exception as e:
        print(f"[WEBHOOK] Error: {e}")
    
    # 始終回傳 200，避免 LINE 認為 Webhook 故障
    return 'OK', 200

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """處理文字訊息"""
    try:
        user_id = event.source.user_id
        text = event.message.text.strip()
        
        print(f"[MSG] User: {user_id}, Text: {text}")
        
        # 記錄對話
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('INSERT INTO conversations (user_id, symptom) VALUES (?, ?)', (user_id, text))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] 記錄對話失敗: {e}")
        
        # 指令判斷 - 支援模糊匹配（包含關鍵字即可）
        text_lower = text.lower().strip()
        
        # 預設回覆
        reply = None
        
        if any(k in text_lower for k in ["附近廠商", "維修廠", "推薦", "廠商"]):
            reply = get_nearby_shops()
        elif any(k in text_lower for k in ["幫助", "help", "說明", "使用", "功能", "指令"]):
            reply = """🏍️ 柴師傅使用說明

【快速診斷】
直接描述您的機車問題，例如：
• 「發不動，有喀喀聲」
• 「起步有異音」
• 「煞車變很軟」
• 「最近很耗油」

【功能選單】
🔧 症狀診斷 — AI 智能分析問題
💰 價格查詢 — 常見維修價目表
🏪 附近廠商 — 推薦合作維修廠
📋 維修紀錄 — 查看您的歷史紀錄
⭐ 評價回饋 — 給維修廠評分

【注意事項】
⚠️ 以上為AI初步估價，實際價格以現場檢測為準

有問題隨時問我！🔧"""
        elif any(k in text_lower for k in ["價格", "價錢", "多少錢", "費用", "報價"]):
            reply = """💰 常見維修參考價格

電系類：
• 電瓶更換：$800 - $1,500
• 啟動馬達：$1,500 - $3,000
• 火星塞：$200 - $500

傳動類：
• 普利珠：$800 - $1,500
• 離合器：$1,200 - $2,500
• 傳動皮帶：$400 - $800

煞車類：
• 來令片：$300 - $800
• 煞車油：$200 - $400
• 碟盤：$800 - $1,500

引擎類：
• 換機油：$300 - $600
• 空濾更換：$200 - $500
• 墊片維修：$500 - $2,000

⚠️ 以上為參考價，實際以維修廠報價為準"""
        elif any(k in text_lower for k in ["症狀", "診斷", "問題", "故障", "壞掉", "怎麼辦"]):
            # 使用關鍵字匹配診斷
            diagnosis = diagnose_symptom(text)
            reply = format_diagnosis_reply(diagnosis)
        elif any(k in text_lower for k in ["紀錄", "歷史", "我的紀錄", "維修紀錄"]):
            reply = get_user_history(user_id)
        elif any(k in text_lower for k in ["評價", "打分", "回饋", "滿意度", "評分"]):
            reply = """⭐ 維修廠評價

請告訴我：
1. 您去了哪家維修廠？
2. 維修項目是什麼？
3. 實際花費多少？
4. 滿意度 1-5 星？

格式範例：
「大台北機車，換電瓶，1200元，5星」

小柴子會幫您記錄，讓其他車友參考！📝"""
        else:
            # AI 診斷：先嘗試 Gemini，失敗則用關鍵字匹配
            gemini_result = gemini_diagnose(text)
            if gemini_result:
                reply = f"🤖 **Gemini AI 智能診斷**\n\n{gemini_result}\n\n---\n💡 也想看傳統診斷？輸入「傳統診斷」"
            else:
                diagnosis = diagnose_symptom(text)
                reply = format_diagnosis_reply(diagnosis)
        
        # 發送回覆
        if reply and line_bot_api:
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply)
                )
                print(f"[MSG] Reply sent successfully")
            except Exception as e:
                print(f"[MSG] Failed to send reply: {e}")
        else:
            print(f"[MSG] No reply or line_bot_api not available")
            
    except Exception as e:
        print(f"[MSG] Error in handle_text_message: {e}")

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    """處理位置訊息"""
    try:
        lat = event.message.latitude
        lng = event.message.longitude
        
        reply = get_nearby_shops(lat, lng)
        
        if line_bot_api:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )
    except Exception as e:
        print(f"[LOC] Error: {e}")

# ============ 啟動 ============

if __name__ == "__main__":
    print("🚀 初始化柴師傅機車維修估價機器人...")
    init_db()
    init_sample_data()
    print("✅ 準備完成！啟動伺服器...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# 🏍️ 柴師傅 - 機車維修估價 LINE 機器人

![柴師傅吉祥物](assets/chai-master-mascot-final.jpeg)

> 老柴老師的創業項目 MVP —— 讓機車維修估價透明化！

## 🤖 功能特色

- ✅ **AI 智能診斷** — GPT-4 專業技師級診斷
- ✅ **關鍵字診斷** — 快速匹配常見症狀
- ✅ **透明估價** — 零件費 + 工資明細
- ✅ **維修廠推薦** — 評分 + 評價數排序
- ✅ **對話紀錄** — SQLite 本地儲存

## 🚀 快速啟動

### 1. 安裝依賴
```bash
cd chai-moto-bot
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 設定環境變數
```bash
cp .env.example .env
# 編輯 .env：
# LINE_CHANNEL_ACCESS_TOKEN=xxx
# LINE_CHANNEL_SECRET=xxx
# OPENAI_API_KEY=xxx (選填，啟用 AI 診斷)
```

### 3. 啟動伺服器
```bash
python app.py
```

### 4. 設定 LINE Webhook
- 進入 [LINE Developers Console](https://developers.line.biz/)
- 設定 Webhook URL: `https://your-domain.com/webhook`
- 開啟「Use webhook」

## 📋 功能清單

| 功能 | 狀態 | 說明 |
|:---|:---|:---|
| 症狀關鍵字診斷 | ✅ | 15+ 常見問題匹配 |
| GPT AI 診斷 | ✅ | GPT-4 智能分析 |
| 價格區間估算 | ✅ | 低/中/高三檔 |
| 維修廠推薦 | ✅ | 評分排序 |
| 對話紀錄 | ✅ | SQLite 儲存 |
| 地圖定位 | 🔄 | Phase 2 |
| 預約系統 | 🔄 | Phase 3 |
| 支付整合 | 🔄 | Phase 4 |

## 🛠️ 技術架構

- **後端**: Flask + Python 3.11
- **LINE SDK**: line-bot-sdk
- **AI 引擎**: OpenAI GPT-4
- **資料庫**: SQLite3
- **部署**: Gunicorn

## 📁 專案結構

```
chai-moto-bot/
├── app.py              # 主程式
├── assets/             # 吉祥物圖片
├── moto_repair.db      # SQLite 資料庫
├── .env.example        # 環境變數範本
├── requirements.txt    # 依賴清單
└── README.md           # 本文件
```

## 🔧 使用方式

1. **直接描述問題**: 「發不動，有喀喀聲」→ AI 診斷
2. **查詢價格**: 輸入「價格查詢」→ 常見維修價目表
3. **找維修廠**: 輸入「附近廠商」→ 推薦列表
4. **切換模式**: 輸入「傳統診斷」→ 關鍵字匹配

## 📊 API 端點

| 端點 | 方法 | 說明 |
|:---|:---|:---|
| `/` | GET | 健康檢查 |
| `/webhook` | POST | LINE Webhook 接收 |

## 🐕 關於柴師傅

柴師傅是隻熱愛機車的柴犬，有 20 年維修經驗！
雖然是 AI 助手，但估價絕對透明公道 🏍️💨

---

**老柴老師的創業項目** | Made with ❤️ by 小柴子

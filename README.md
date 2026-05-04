# 柴師傅 - 機車維修估價 LINE 機器人

## 快速啟動

### 1. 安裝依賴
```bash
cd /home/wayn1210/chai-moto-bot
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 設定環境變數
```bash
cp .env.example .env
# 編輯 .env，填入 LINE Bot 憑證
```

### 3. 啟動伺服器
```bash
python app.py
```

### 4. 設定 LINE Webhook
- 進入 LINE Developers Console
- 設定 Webhook URL: `https://your-domain.com/webhook`
- 開啟「Use webhook」

## 功能清單

- [x] 症狀關鍵字診斷
- [x] 價格區間估算
- [x] 維修廠推薦
- [x] 對話紀錄
- [ ] GPT AI 診斷 (Phase 2)
- [ ] 地圖定位 (Phase 2)
- [ ] 預約系統 (Phase 3)
- [ ] 支付整合 (Phase 4)

## 資料庫結構

見 `app.py` 中的 `init_db()` 函數

## API 端點

| 端點 | 方法 | 說明 |
|:---|:---|:---|
| `/` | GET | 健康檢查 |
| `/webhook` | POST | LINE Webhook |

## 聯絡

老柴老師的創業項目 🏍️🔧

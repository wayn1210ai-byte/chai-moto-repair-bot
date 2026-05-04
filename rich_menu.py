#!/usr/bin/env python3
"""
柴師傅 - LINE Rich Menu 功能介面設定
"""

import requests
import json
import os

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

def create_rich_menu():
    """建立功能介面選單"""
    
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Rich Menu 設定
    rich_menu = {
        "size": {
            "width": 2500,
            "height": 1686
        },
        "selected": True,
        "name": "柴師傅主選單",
        "chatBarText": "🏍️ 柴師傅功能選單",
        "areas": [
            {
                "bounds": {
                    "x": 0,
                    "y": 0,
                    "width": 833,
                    "height": 843
                },
                "action": {
                    "type": "message",
                    "text": "🔧 症狀診斷"
                }
            },
            {
                "bounds": {
                    "x": 833,
                    "y": 0,
                    "width": 834,
                    "height": 843
                },
                "action": {
                    "type": "message",
                    "text": "💰 價格查詢"
                }
            },
            {
                "bounds": {
                    "x": 1667,
                    "y": 0,
                    "width": 833,
                    "height": 843
                },
                "action": {
                    "type": "message",
                    "text": "🏪 附近廠商"
                }
            },
            {
                "bounds": {
                    "x": 0,
                    "y": 843,
                    "width": 833,
                    "height": 843
                },
                "action": {
                    "type": "message",
                    "text": "📋 維修紀錄"
                }
            },
            {
                "bounds": {
                    "x": 833,
                    "y": 843,
                    "width": 834,
                    "height": 843
                },
                "action": {
                    "type": "message",
                    "text": "⭐ 評價回饋"
                }
            },
            {
                "bounds": {
                    "x": 1667,
                    "y": 843,
                    "width": 833,
                    "height": 843
                },
                "action": {
                    "type": "message",
                    "text": "❓ 使用說明"
                }
            }
        ]
    }
    
    # 建立 Rich Menu
    response = requests.post(
        "https://api.line.me/v2/bot/richmenu",
        headers=headers,
        json=rich_menu
    )
    
    if response.status_code == 200:
        rich_menu_id = response.json()["richMenuId"]
        print(f"✅ Rich Menu 建立成功！ID: {rich_menu_id}")
        return rich_menu_id
    else:
        print(f"❌ 建立失敗: {response.status_code} - {response.text}")
        return None

def upload_rich_menu_image(rich_menu_id, image_path):
    """上傳 Rich Menu 圖片"""
    
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "image/jpeg"
    }
    
    with open(image_path, 'rb') as f:
        response = requests.post(
            f"https://api.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            headers=headers,
            data=f
        )
    
    if response.status_code == 200:
        print("✅ Rich Menu 圖片上傳成功！")
        return True
    else:
        print(f"❌ 上傳失敗: {response.status_code} - {response.text}")
        return False

def set_default_rich_menu(rich_menu_id):
    """設定預設 Rich Menu"""
    
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    
    response = requests.post(
        f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ 預設 Rich Menu 設定成功！")
        return True
    else:
        print(f"❌ 設定失敗: {response.status_code} - {response.text}")
        return False

if __name__ == "__main__":
    print("🚀 建立柴師傅功能介面...")
    
    # 建立 Rich Menu
    rich_menu_id = create_rich_menu()
    
    if rich_menu_id:
        # 上傳圖片（如果有）
        # upload_rich_menu_image(rich_menu_id, "richmenu.jpg")
        
        # 設定為預設
        set_default_rich_menu(rich_menu_id)
        
        print("\n🎉 功能介面建立完成！")
        print("用戶現在可以在 LINE 看到選單按鈕了！")

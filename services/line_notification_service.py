"""
LINE通知サービス
services/line_notification_service.py
"""
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from core.database import fetch_dict_one, fetch_dict
from services.company_service import get_company_name

# LINE Bot SDK（オプション）
try:
    from linebot import LineBotApi, WebhookHandler
    from linebot.models import TextSendMessage
    HAS_LINEBOT_SDK = True
except ImportError:
    print("LINE Bot SDKがインストールされていません。直接APIを使用します。")
    HAS_LINEBOT_SDK = False

class LineNotificationService:
    def __init__(self):
        self.line_bot_api = None
        self.webhook_handler = None
        self._initialize_line_client()
    
    def _initialize_line_client(self):
        """LINE Bot APIクライアント初期化"""
        try:
            access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
            channel_secret = os.getenv('LINE_CHANNEL_SECRET')
            
            if access_token and channel_secret:
                if HAS_LINEBOT_SDK:
                    self.line_bot_api = LineBotApi(access_token)
                    self.webhook_handler = WebhookHandler(channel_secret)
                    print("LINE Bot API初期化成功")
                else:
                    # 直接API使用の場合
                    self.access_token = access_token
                    self.api_endpoint = "https://api.line.me/v2/bot/message/push"
                    print("LINE直接API初期化成功")
            else:
                print("LINE設定が見つかりません。通知機能は無効化されます。")
        except Exception as e:
            print(f"LINE Bot API初期化エラー: {e}")
    
    def notify_staff_unknown_query(
        self, 
        user_input: str, 
        company_id: str, 
        user_info: str, 
        context: Dict
    ) -> bool:
        """
        未回答質問を担当者にLINE通知
        
        Args:
            user_input: ユーザーの質問
            company_id: 会社ID
            user_info: ユーザー情報
            context: 追加コンテキスト情報
            
        Returns:
            bool: 通知送信成功の有無
        """
        if not (self.line_bot_api or hasattr(self, 'access_token')):
            print("LINE通知が設定されていません")
            return False
        
        try:
            # 担当者のLINE ID取得
            staff_line_ids = self._get_company_staff_line_ids(company_id)
            
            if not staff_line_ids:
                print(f"会社 {company_id} の担当者LINE IDが見つかりません")
                return False
            
            # 通知メッセージ作成
            message_text = self._create_notification_message_text(
                user_input, user_info, context, company_id
            )
            
            # 各担当者に通知送信
            success_count = 0
            for staff_id in staff_line_ids:
                try:
                    if HAS_LINEBOT_SDK and self.line_bot_api:
                        # SDK使用
                        message = TextSendMessage(text=message_text)
                        self.line_bot_api.push_message(staff_id, message)
                    else:
                        # 直接API使用
                        success = self._send_line_message_direct(staff_id, message_text)
                        if not success:
                            continue
                    
                    self._log_notification(staff_id, user_input, company_id)
                    success_count += 1
                    print(f"LINE通知送信成功: {staff_id}")
                except Exception as e:
                    print(f"LINE通知エラー ({staff_id}): {e}")
                    continue
            
            return success_count > 0
            
        except Exception as e:
            print(f"LINE通知処理エラー: {e}")
            return False
    
    def _get_company_staff_line_ids(self, company_id: str) -> List[str]:
        """会社の担当者LINE ID一覧取得"""
        try:
            # companies テーブルから LINE ID を取得
            from core.database import DB_TYPE
            param_format = "%s" if DB_TYPE == "postgresql" else "?"
            query = f"""
                SELECT line_notification_id 
                FROM companies 
                WHERE company_id = {param_format} AND line_notification_id IS NOT NULL
            """
            result = fetch_dict_one(query, (company_id,))
            
            if result and result['line_notification_id']:
                return [result['line_notification_id']]
            
            # デフォルト通知先（環境変数から）
            default_line_id = os.getenv('DEFAULT_STAFF_LINE_ID')
            if default_line_id:
                return [default_line_id]
                
            return []
            
        except Exception as e:
            print(f"担当者LINE ID取得エラー: {e}")
            return []
    
    def _create_notification_message_text(
        self, 
        user_input: str, 
        user_info: str, 
        context: Dict, 
        company_id: str
    ) -> str:
        """通知メッセージ作成"""
        timestamp = datetime.now().strftime("%Y/%m/%d %H:%M")
        company_name = get_company_name(company_id) or company_id
        
        # メッセージ本文作成
        message_text = f"""🤖 FAQ未回答通知

⏰ 時刻: {timestamp}
🏢 会社: {company_name}
👤 お客様情報: {user_info or '未記入'}

❓ 質問内容:
「{user_input}」

📊 詳細情報:
• 言語: {context.get('detected_language', 'ja')}
• 位置情報: {context.get('location', '取得できませんでした')}

💡 システム状況:
{context.get('suggested_response', '回答を見つけることができませんでした')}

🔧 対応方法:
管理画面からFAQを追加してください
{self._get_admin_url(company_id)}

📝 この通知は自動送信されています"""
        
        # メッセージ長制限（LINE制限: 5000文字）
        if len(message_text) > 4800:
            message_text = message_text[:4800] + "..."
        
        return message_text
    
    def _get_admin_url(self, company_id: str) -> str:
        """管理画面URLを生成"""
        base_url = os.getenv('APP_BASE_URL', 'http://localhost:8501')
        return f"{base_url}/?mode=admin&company={company_id}"
    
    def _send_line_message_direct(self, user_id: str, message_text: str) -> bool:
        """直接API経由でLINEメッセージ送信"""
        try:
            if not hasattr(self, 'access_token'):
                return False
                
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            
            data = {
                'to': user_id,
                'messages': [
                    {
                        'type': 'text',
                        'text': message_text
                    }
                ]
            }
            
            response = requests.post(self.api_endpoint, headers=headers, json=data)
            return response.status_code == 200
            
        except Exception as e:
            print(f"直接API送信エラー: {e}")
            return False
    
    def _log_notification(self, staff_id: str, user_input: str, company_id: str):
        """通知ログの記録"""
        try:
            # 通知履歴をDBに記録する場合の実装
            # 現在は簡易ログのみ
            print(f"LINE通知ログ: {company_id} -> {staff_id} | {user_input[:50]}...")
        except Exception as e:
            print(f"通知ログエラー: {e}")
    
    def test_notification(self, company_id: str) -> bool:
        """テスト通知送信"""
        test_context = {
            'detected_language': 'ja',
            'location': 'テスト',
            'suggested_response': 'テスト通知です'
        }
        
        return self.notify_staff_unknown_query(
            "テスト質問です", 
            company_id, 
            "テストユーザー", 
            test_context
        )
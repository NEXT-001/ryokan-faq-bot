"""
LINE メッセージング機能の統合サービス
LINE Bot SDK とダイレクト API 両方の実装をサポート
"""
import os
import requests
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime

# LINE Bot SDK のインポートを試みる（インストールされていない場合のエラーを防止）
try:
    from linebot import LineBotApi
    from linebot.exceptions import LineBotApiError
    from linebot.models import TextSendMessage
    LINE_SDK_AVAILABLE = True
except ImportError:
    LINE_SDK_AVAILABLE = False
    print("LINE Bot SDKがインストールされていません。直接APIを使用します。")

def load_line_credentials():
    """
    .envファイルまたはStreamlit SecretsからLINE APIの認証情報を読み込む
    """
    # Streamlit Cloudsでは環境変数からシークレットを取得
    channel_access_token = None
    channel_secret = None
    user_id = None

    try:
        if hasattr(st, 'secrets') and isinstance(st.secrets, dict):
            if 'LINE_CHANNEL_ACCESS_TOKEN' in st.secrets:
                channel_access_token = st.secrets['LINE_CHANNEL_ACCESS_TOKEN']
            if 'LINE_CHANNEL_SECRET' in st.secrets:
                channel_secret = st.secrets['LINE_CHANNEL_SECRET']
            if 'LINE_USER_ID' in st.secrets:
                user_id = st.secrets['LINE_USER_ID']
    except Exception as e:
        print(f"Streamlit Secretsの読み込みエラー: {e}")
    
    # Secretsから取得できなかった場合は.envファイルを確認
    if not channel_access_token or not channel_secret or not user_id:
        load_dotenv()
        channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        user_id = os.getenv("LINE_USER_ID")
    
    return channel_access_token, channel_secret, user_id

def send_line_message(question, answer=None, similarity_score=None, room_number=""):
    """
    LINEメッセージを送信する
    SDK利用可能な場合はSDKを使用し、なければ直接APIを呼び出す
    
    Parameters:
    question (str): ユーザーからの質問
    answer (str, optional): システムからの回答
    similarity_score (float, optional): 類似度スコア
    room_number (str, optional): 部屋番号
    """
    channel_access_token, channel_secret, user_id = load_line_credentials()
    
    if not channel_access_token or not user_id:
        print("LINE APIの認証情報が設定されていません")
        return False
    
    # 通知メッセージの作成
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_text = f"[対応確認依頼] {now}\n\n"
    
    # 部屋番号の情報があれば追加
    if room_number:
        message_text += f"■部屋番号: {room_number}\n\n"
        
    message_text += f"■質問:\n{question}\n\n"
    
    if answer:
        message_text += f"■システム回答:\n{answer}\n\n"
    
    if similarity_score is not None:
        message_text += f"■類似度スコア: {similarity_score:.2f}\n"
    
    message_text += "※このメッセージはFAQボットから自動送信されています。"
    
    try:
        # LINE Bot SDKが利用可能な場合はSDKを使用
        if LINE_SDK_AVAILABLE:
            try:
                # LineBotApiインスタンスを初期化
                line_bot_api = LineBotApi(channel_access_token)
                
                # LINE Bot SDKを使ってメッセージを送信
                line_bot_api.push_message(
                    user_id, 
                    TextSendMessage(text=message_text)
                )
                
                print("LINE Bot SDKを使用してメッセージが送信されました")
                return True
                
            except LineBotApiError as e:
                print(f"LINE Bot SDK エラー: {e}")
                # SDKエラーの場合、代替APIを試みる
                
        # SDK利用不可またはSDKエラーの場合、直接APIを呼び出す
        url = 'https://api.line.me/v2/bot/message/push'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {channel_access_token}'
        }
        data = {
            "to": user_id,
            "messages": [
                {
                    "type": "text",
                    "text": message_text
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print("LINE REST APIを使用してメッセージが送信されました")
            return True
        else:
            print(f"LINEメッセージの送信に失敗しました: {response.text}")
            return False
            
    except Exception as e:
        print(f"LINEメッセージの送信中にエラーが発生しました: {e}")
        return False
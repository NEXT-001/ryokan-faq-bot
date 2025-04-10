import os
import requests
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime

def load_line_credentials():
    """
    .envファイルまたはStreamlit SecretsからLINE Messaging APIの認証情報を読み込む
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

def send_line_message(question, answer=None, similarity_score=None):
    """
    LINE Messaging APIを使用してメッセージを送信する
    
    Parameters:
    question (str): ユーザーからの質問
    answer (str, optional): システムからの回答
    similarity_score (float, optional): 類似度スコア
    """
    channel_access_token, channel_secret, user_id = load_line_credentials()
    
    if not channel_access_token or not user_id:
        print("LINE Messaging API の認証情報が設定されていません")
        return False
    
    try:
        # 通知メッセージの作成
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_text = f"[対応確認依頼] {now}\n\n"
        message_text += f"■質問:\n{question}\n\n"
        
        if answer:
            message_text += f"■システム回答:\n{answer}\n\n"
        
        if similarity_score is not None:
            message_text += f"■類似度スコア: {similarity_score:.2f}\n"
        
        message_text += "※このメッセージはFAQボットから自動送信されています。"
        
        # LINE Messaging APIにリクエストを送信
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
            print("LINEメッセージが送信されました")
            return True
        else:
            print(f"LINEメッセージの送信に失敗しました: {response.text}")
            return False
            
    except Exception as e:
        print(f"LINEメッセージの送信中にエラーが発生しました: {e}")
        return False
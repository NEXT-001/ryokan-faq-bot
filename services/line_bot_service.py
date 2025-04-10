import os
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage

def load_line_credentials():
    """
    .envファイルまたはStreamlit SecretsからLINE Bot APIの認証情報を読み込む
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
    LINE Bot SDKを使用してメッセージを送信する
    
    Parameters:
    question (str): ユーザーからの質問
    answer (str, optional): システムからの回答
    similarity_score (float, optional): 類似度スコア
    """
    channel_access_token, _, user_id = load_line_credentials()
    
    if not channel_access_token or not user_id:
        print("LINE Bot APIの認証情報が設定されていません")
        return False
    
    try:
        # LineBotApiインスタンスを初期化
        line_bot_api = LineBotApi(channel_access_token)
        
        # 通知メッセージの作成
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_text = f"[対応確認依頼] {now}\n\n"
        message_text += f"■質問:\n{question}\n\n"
        
        if answer:
            message_text += f"■システム回答:\n{answer}\n\n"
        
        if similarity_score is not None:
            message_text += f"■類似度スコア: {similarity_score:.2f}\n"
        
        message_text += "※このメッセージはFAQボットから自動送信されています。"
        
        # LINE Bot SDKを使ってメッセージを送信
        line_bot_api.push_message(
            user_id, 
            TextSendMessage(text=message_text)
        )
        
        print("LINEメッセージが送信されました")
        return True
            
    except LineBotApiError as e:
        print(f"LINE Bot API エラー: {e}")
        return False
    except Exception as e:
        print(f"LINEメッセージの送信中にエラーが発生しました: {e}")
        return False
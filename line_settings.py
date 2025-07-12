# line_settings.py
import streamlit as st
import os
import json
from dotenv import load_dotenv
from services.line_service import send_line_message

def line_settings_page(company_id=None):
    """
    LINE設定ページ
    
    Args:
        company_id (str, optional): 会社ID
    """
    st.header("LINE通知設定")
    
    if not company_id:
        st.error("会社情報が見つかりません。ログインしてください。")
        return
    
    # 現在の設定値を取得
    settings_path = f"data/companies/{company_id}/settings.json"
    current_token = ""
    current_secret = ""
    current_user_id = ""
    current_threshold = 0.4
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            line_settings = settings.get('line_settings', {})
            current_token = line_settings.get('channel_access_token', "")
            current_secret = line_settings.get('channel_secret', "")
            current_user_id = line_settings.get('user_id', "")
            current_threshold = line_settings.get('low_similarity_threshold', 0.4)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    # LINE設定フォーム
    with st.form("line_settings_form"):
        st.subheader("LINE通知設定")
        
        st.markdown("""
        LINE通知機能を設定すると、類似度の低い質問（適切な回答が見つからない場合）は
        自動的にLINE経由で担当者に通知されます。
        
        ### LINE Botの設定方法
        1. [LINE Developers](https://developers.line.biz/)でチャネルを作成
        2. Messaging APIのチャネルアクセストークンを発行
        3. 下記の情報を入力して設定を保存
        """)
        
        # LINEチャネルアクセストークン
        channel_token = st.text_input(
            "LINEチャネルアクセストークン", 
            value=current_token,
            type="password"
        )
        
        # LINEチャネルシークレット
        channel_secret = st.text_input(
            "LINEチャネルシークレット", 
            value=current_secret,
            type="password"
        )
        
        # LINEユーザーID
        user_id = st.text_input(
            "LINE通知先ユーザーID", 
            value=current_user_id
        )
        
        # 類似度しきい値
        low_similarity_threshold = st.slider(
            "LINE通知を送信する類似度しきい値", 
            min_value=0.0, 
            max_value=0.6, 
            value=current_threshold,
            step=0.05,
            help="この値より低い類似度の場合、LINE通知が送信されます"
        )
        
        # 保存ボタン
        submit = st.form_submit_button("設定を保存")
        
        if submit:
            try:
                # 既存のsettings.jsonを読み込む
                settings = {}
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
                
                # LINE設定を更新
                settings['line_settings'] = {
                    'channel_access_token': channel_token,
                    'channel_secret': channel_secret,
                    'user_id': user_id,
                    'low_similarity_threshold': low_similarity_threshold
                }
                
                # settings.jsonに保存
                os.makedirs(os.path.dirname(settings_path), exist_ok=True)
                with open(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                st.success("LINE設定を保存しました")
            except Exception as e:
                st.error(f"設定の保存に失敗しました: {e}")
    
    # テスト通知セクション
    st.subheader("LINE通知テスト")
    
    test_col1, test_col2 = st.columns(2)
    
    with test_col1:
        test_message = st.text_input("テストメッセージ", value="これはFAQボットからのテスト通知です。")
    
    with test_col2:
        test_room = st.text_input("テスト部屋番号", value="101")
    
    if st.button("テスト通知を送信"):
        with st.spinner("通知を送信中..."):
            success = send_line_message(
                question=test_message,
                answer="これはテスト通知です。",
                similarity_score=0.3,
                room_number=test_room,
                company_id=company_id
            )
            
            if success:
                st.success("テスト通知を送信しました")
            else:
                st.error("通知の送信に失敗しました。LINE設定を確認してください。")
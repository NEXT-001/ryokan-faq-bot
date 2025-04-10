import streamlit as st
import os
from services.line_bot_service import send_line_message

def line_settings_page():
    """
    LINE設定ページ
    """
    st.header("LINE通知設定")
    
    # 現在の設定値を取得
    current_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    current_secret = os.getenv("LINE_CHANNEL_SECRET", "")
    current_user_id = os.getenv("LINE_USER_ID", "")
    current_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.6"))
    
    # LINE設定フォーム
    with st.form("line_settings_form"):
        st.subheader("LINE通知設定")
        
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
        similarity_threshold = st.slider(
            "類似度しきい値（この値以下の場合にLINE通知）", 
            min_value=0.0, 
            max_value=1.0, 
            value=current_threshold,
            step=0.05
        )
        
        # 保存ボタン
        submit = st.form_submit_button("設定を保存")
        
        if submit:
            # .envファイルの既存の内容を読み込む
            env_content = {}
            try:
                with open(".env", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip() and not line.startswith("#"):
                            key, value = line.strip().split("=", 1)
                            env_content[key] = value
            except FileNotFoundError:
                pass  # .envファイルがない場合は新規作成
            
            # 更新する値を設定
            env_content["LINE_CHANNEL_ACCESS_TOKEN"] = f"'{channel_token}'"
            env_content["LINE_CHANNEL_SECRET"] = f"'{channel_secret}'"
            env_content["LINE_USER_ID"] = f"'{user_id}'"
            env_content["SIMILARITY_THRESHOLD"] = f"'{similarity_threshold}'"
            
            # 環境変数も更新
            os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = channel_token
            os.environ["LINE_CHANNEL_SECRET"] = channel_secret
            os.environ["LINE_USER_ID"] = user_id
            os.environ["SIMILARITY_THRESHOLD"] = str(similarity_threshold)
            
            # .envファイルに書き込む
            with open(".env", "w", encoding="utf-8") as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            
            st.success("LINE設定を保存しました")
    
    # テスト通知セクション
    st.subheader("LINE通知テスト")
    test_message = st.text_input("テストメッセージ", value="これはFAQボットからのテスト通知です。")
    
    if st.button("テスト通知を送信"):
        success = send_line_message(
            question=test_message,
            answer="これはテスト通知です。",
            similarity_score=0.5
        )
        
        if success:
            st.success("テスト通知を送信しました")
        else:
            st.error("通知の送信に失敗しました。LINE設定を確認してください。")
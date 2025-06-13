# services/email_service.py - メール送信機能（デバッグ強化版）
import os
import smtplib
import streamlit as st
import traceback
from email.mime.text import MIMEText
from utils.constants import VERIFICATION_URL

def send_verification_email(email, token):
    """認証メールを送信（デバッグ強化版）"""
    try:
        print(f"[EMAIL] メール送信開始")
        print(f"  - 宛先: {email}")
        print(f"  - トークン: {token}")
        
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        
        print(f"[EMAIL] SMTP設定確認")
        print(f"  - SMTP_USER: {smtp_user is not None and len(smtp_user) > 0}")
        print(f"  - SMTP_PASS: {smtp_pass is not None and len(smtp_pass) > 0}")
        
        if not smtp_user or not smtp_pass:
            print(f"[EMAIL] SMTP設定が不完全")
            st.warning("メール設定が不完全です。管理者にお問い合わせください。")
            return False
        
        # メール本文作成
        verification_link = f"{VERIFICATION_URL}?token={token}"
        print(f"[EMAIL] 認証リンク: {verification_link}")
        
        msg = MIMEText(f"以下のリンクをクリックして登録を完了してください:\n{verification_link}")
        msg["Subject"] = "【FAQシステム】メールアドレス認証のお願い"
        msg["From"] = smtp_user
        msg["To"] = email
        
        print(f"[EMAIL] メールヘッダー設定完了")
        print(f"  - From: {smtp_user}")
        print(f"  - To: {email}")
        print(f"  - Subject: {msg['Subject']}")

        # SMTP接続・送信
        print(f"[EMAIL] SMTP接続中...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            print(f"[EMAIL] ログイン中...")
            server.login(smtp_user, smtp_pass)
            print(f"[EMAIL] メール送信中...")
            server.send_message(msg)
            print(f"[EMAIL] メール送信完了")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL] SMTP認証エラー: {e}")
        st.error("メールの認証に失敗しました。SMTP設定を確認してください。")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL] SMTPエラー: {e}")
        st.error(f"メール送信エラー: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL] 予期しないエラー: {e}")
        print(f"[EMAIL TRACEBACK] {traceback.format_exc()}")
        st.error(f"メール送信エラー: {e}")
        return False

def test_email_configuration():
    """メール設定をテストする（デバッグ用）"""
    try:
        print(f"[EMAIL TEST] メール設定テスト開始")
        
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        
        print(f"[EMAIL TEST] 環境変数チェック:")
        print(f"  - SMTP_USER: {smtp_user if smtp_user else 'Not set'}")
        print(f"  - SMTP_PASS: {'Set' if smtp_pass else 'Not set'}")
        
        if not smtp_user or not smtp_pass:
            print(f"[EMAIL TEST] SMTP設定が不完全")
            return False
        
        # SMTP接続テスト
        print(f"[EMAIL TEST] SMTP接続テスト中...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            print(f"[EMAIL TEST] ログインテスト中...")
            server.login(smtp_user, smtp_pass)
            print(f"[EMAIL TEST] ログイン成功")
        
        print(f"[EMAIL TEST] メール設定テスト完了")
        return True
        
    except Exception as e:
        print(f"[EMAIL TEST ERROR] {e}")
        print(f"[EMAIL TEST TRACEBACK] {traceback.format_exc()}")
        return False
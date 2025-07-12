"""
会社管理に関するサービス
services/company_service.py
"""
import os
import json
import pandas as pd
from datetime import datetime
from utils.constants import get_data_path
from utils.auth_utils import hash_password
from core.database import (
    save_company_to_db, get_company_from_db, save_company_admin_to_db,
    get_company_admins_from_db, get_all_companies_from_db, company_exists_in_db,
    update_company_faq_count_in_db, save_line_settings_to_db, get_line_settings_from_db
)

def get_settings_file_path(company_id):
    """会社IDに基づいてsettings.jsonのパスを取得"""
    if company_id:
        # 会社別のディレクトリからsettings.jsonを取得
        company_dir = get_data_path(company_id)
        return os.path.join(company_dir, "settings.json")
    else:
        # 共通ディレクトリからsettings.jsonを取得
        base_dir = get_data_path()
        return os.path.join(base_dir, "settings.json")

def load_company_settings(company_id):
    """会社設定を読み込む（SQLite + JSONファイル統合）"""
    try:
        # SQLiteから基本情報を取得
        company_info = get_company_from_db(company_id)
        
        if not company_info:
            # 会社が存在しない場合はデフォルト設定を作成
            return create_default_settings(company_id)
        
        # LINE設定をSQLiteから取得
        line_settings = get_line_settings_from_db(company_id)
        
        # 管理者情報をSQLiteから取得
        admins = get_company_admins_from_db(company_id)
        
        # 統合設定を作成
        settings = {
            "company_id": company_info["company_id"],
            "company_name": company_info["company_name"],
            "created_at": company_info["created_at"],
            "faq_count": company_info["faq_count"],
            "last_updated": company_info["last_updated"],
            "admins": admins
        }
        
        # LINE設定がある場合は追加
        if line_settings:
            settings["line_settings"] = line_settings
        
        return settings
        
    except Exception as e:
        print(f"[COMPANY_SERVICE] 設定読み込みエラー: {e}")
        return create_default_settings(company_id)

def create_default_settings(company_id):
    """デフォルトの設定を作成（SQLite中心）"""
    # 会社ディレクトリを確認・作成
    company_dir = get_data_path(company_id)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
    
    created_at = datetime.now().isoformat()
    
    # デフォルト設定
    if company_id == "demo-company":
        company_name = "デモ企業"
        faq_count = 5
        
        # 会社をSQLiteに保存
        save_company_to_db(company_id, company_name, created_at, faq_count)
        
        # 管理者をSQLiteに保存
        save_company_admin_to_db(
            company_id, "admin", hash_password("admin123"), 
            "admin@example.com", created_at
        )
        
        # サンプルFAQを作成
        create_sample_faq(company_id)
        
        # 設定を再読み込みして返す
        return load_company_settings(company_id)
    else:
        company_name = f"企業_{company_id}"
        
        # 会社をSQLiteに保存
        save_company_to_db(company_id, company_name, created_at, 0)
        
        # 設定を再読み込みして返す  
        return load_company_settings(company_id)

def create_sample_faq(company_id):
    """サンプルFAQを作成"""
    company_dir = get_data_path(company_id)
    faq_file = os.path.join(company_dir, "faq.csv")
    
    if not os.path.exists(faq_file):
        sample_faq = {
            "question": [
                "デモ企業のFAQシステムについて教えてください",
                "このシステムは何ができますか？",
                "FAQ管理はどうすれば良いですか？",
                "新しい質問を追加するには？",
                "ログインするにはどうすれば良いですか？"
            ],
            "answer": [
                "これはデモ企業用のFAQシステムです。顧客からのよくある質問に自動で回答できます。",
                "このシステムでは、FAQの管理（追加・編集・削除）、質問への自動回答、利用履歴の確認などができます。",
                "管理者としてログイン後、「FAQ管理」タブからFAQの追加・編集・削除ができます。",
                "管理者としてログイン後、「FAQ管理」タブから「FAQ追加」を選択し、質問と回答を入力して追加できます。",
                "トップページの「管理者ログイン」ボタンから、企業IDとユーザー名、パスワードを入力してログインできます。"
            ]
        }
        pd.DataFrame(sample_faq).to_csv(faq_file, index=False)

def save_company_settings(company_id, settings):
    """会社の設定を保存する（SQLite中心）"""
    print(f"[SAVE_COMPANY_SETTINGS] 設定保存開始: {company_id}")
    
    try:
        # 会社基本情報をSQLiteに保存
        company_name = settings.get("company_name", f"企業_{company_id}")
        created_at = settings.get("created_at", datetime.now().isoformat())
        faq_count = settings.get("faq_count", 0)
        
        save_company_to_db(company_id, company_name, created_at, faq_count)
        
        # 管理者情報をSQLiteに保存
        admins = settings.get("admins", {})
        for username, admin_info in admins.items():
            save_company_admin_to_db(
                company_id, username, admin_info["password"],
                admin_info.get("email", ""), admin_info.get("created_at", created_at)
            )
        
        # LINE設定をSQLiteに保存（存在する場合）
        line_settings = settings.get("line_settings")
        if line_settings:
            save_line_settings_to_db(
                company_id,
                line_settings.get("channel_access_token", ""),
                line_settings.get("channel_secret", ""),
                line_settings.get("user_id", ""),
                line_settings.get("low_similarity_threshold", 0.4)
            )
        
        print(f"[SAVE_COMPANY_SETTINGS] SQLite保存成功: {company_id}")
        return True
        
    except Exception as e:
        print(f"[SAVE_COMPANY_SETTINGS] 設定保存エラー: {e}")
        import traceback
        print(f"[SAVE_COMPANY_SETTINGS] エラー詳細: {traceback.format_exc()}")
        return False

def load_companies(company_id=None):
    """
    会社情報を読み込む（SQLite中心、後方互換性のため）
    
    Args:
        company_id (str, optional): 会社ID（使用されない - 後方互換性のため）
        
    Returns:
        dict: 全企業の情報を含む辞書
    """
    try:
        # SQLiteから全企業データを取得
        companies_data = get_all_companies_from_db()
        
        # 従来の形式に変換
        companies = {}
        for company_id, company_info in companies_data.items():
            companies[company_id] = {
                "name": company_info.get("name", company_id),
                "created_at": company_info.get("created_at", ""),
                "admins": company_info.get("admins", {})
            }
        
        # データがない場合はデモ企業データを作成
        if not companies:
            demo_settings = create_default_settings("demo-company")
            companies["demo-company"] = {
                "name": demo_settings.get("company_name", "デモ企業"),
                "created_at": demo_settings.get("created_at", ""),
                "admins": demo_settings.get("admins", {})
            }
        
        return companies
        
    except Exception as e:
        print(f"[COMPANY_SERVICE] 企業読み込みエラー: {e}")
        return {}

def save_companies(companies):
    """
    会社情報を保存する（後方互換性のため）
    
    Args:
        companies (dict): 企業情報の辞書
    
    Returns:
        bool: 全ての保存が成功した場合True、失敗した場合False
    """
    print(f"[SAVE_COMPANIES] 保存開始: {len(companies)}社")
    
    all_success = True
    
    # 各企業の設定を個別に保存
    for company_id, company_data in companies.items():
        print(f"[SAVE_COMPANIES] 会社ID: {company_id} の保存開始")
        
        settings = {
            "company_id": company_id,
            "company_name": company_data.get("name", company_id),
            "created_at": company_data.get("created_at", datetime.now().isoformat()),
            "faq_count": 0,
            "last_updated": datetime.now().isoformat(),
            "admins": company_data.get("admins", {})
        }
        
        print(f"[SAVE_COMPANIES] 管理者数: {len(settings['admins'])}")
        for admin_name, admin_info in settings['admins'].items():
            print(f"[SAVE_COMPANIES] 管理者: {admin_name}, パスワード: {admin_info.get('password', 'N/A')[:20]}...")
        
        success = save_company_settings(company_id, settings)
        print(f"[SAVE_COMPANIES] 会社ID: {company_id} の保存結果: {success}")
        
        if not success:
            all_success = False
    
    print(f"[SAVE_COMPANIES] 全体保存結果: {all_success}")
    return all_success

def verify_company_admin(company_id, username, password):
    """会社管理者の認証を行う（SQLite中心）"""
    try:
        # 会社の存在確認
        if not company_exists_in_db(company_id):
            return False, "企業が見つかりません"
        
        # 管理者情報をSQLiteから取得
        admins = get_company_admins_from_db(company_id)
        
        # 管理者情報が存在しない場合
        if not admins:
            return False, "管理者が設定されていません"
        
        # 管理者ユーザーの確認
        if username not in admins:
            return False, "ユーザー名が見つかりません"
        
        # パスワードの確認
        admin_info = admins[username]
        if admin_info["password"] != hash_password(password):
            return False, "パスワードが間違っています"
        
        # 会社名を取得
        company_info = get_company_from_db(company_id)
        company_name = company_info["company_name"] if company_info else "不明な企業"
        
        # 認証成功
        return True, company_name
        
    except Exception as e:
        print(f"[COMPANY_SERVICE] 認証エラー: {e}")
        return False, "認証エラーが発生しました"

def add_company(company_id, company_name, admin_username, admin_password, admin_email):
    """新しい会社を追加する（SQLite中心）"""
    if not company_id or not company_name or not admin_username or not admin_password:
        return False, "すべての項目を入力してください"
    
    try:
        # 既に会社が存在するかチェック
        if company_exists_in_db(company_id):
            return False, "この企業IDは既に使用されています"
        
        created_at = datetime.now().isoformat()
        
        # 会社をSQLiteに保存
        if not save_company_to_db(company_id, company_name, created_at, 0):
            return False, "企業の作成に失敗しました"
        
        # 管理者をSQLiteに保存
        if not save_company_admin_to_db(
            company_id, admin_username, hash_password(admin_password), 
            admin_email, created_at
        ):
            return False, "管理者の作成に失敗しました"
        
        # 会社ディレクトリを作成
        company_dir = get_data_path(company_id)
        if not os.path.exists(company_dir):
            os.makedirs(company_dir)
        
        return True, "企業と管理者アカウントを作成しました"
        
    except Exception as e:
        print(f"[COMPANY_SERVICE] 企業追加エラー: {e}")
        return False, "企業の作成に失敗しました"

def add_admin(company_id, username, password, email=""):
    """会社に管理者を追加する（SQLite中心）"""
    if not username or not password:
        return False, "ユーザー名とパスワードを入力してください"
    
    try:
        # 会社の存在確認
        if not company_exists_in_db(company_id):
            return False, "企業が見つかりません"
        
        # 既存管理者の確認
        existing_admins = get_company_admins_from_db(company_id)
        if username in existing_admins:
            return False, "このユーザー名は既に使用されています"
        
        # 新しい管理者をSQLiteに追加
        created_at = datetime.now().isoformat()
        if save_company_admin_to_db(company_id, username, hash_password(password), email, created_at):
            return True, "管理者を追加しました"
        else:
            return False, "管理者の追加に失敗しました"
            
    except Exception as e:
        print(f"[COMPANY_SERVICE] 管理者追加エラー: {e}")
        return False, "管理者の追加に失敗しました"

def get_company_name(company_id):
    """会社IDから会社名を取得する（SQLite中心）"""
    try:
        company_info = get_company_from_db(company_id)
        return company_info["company_name"] if company_info else None
    except Exception as e:
        print(f"[COMPANY_SERVICE] 会社名取得エラー: {e}")
        return None

def get_company_info(company_id):
    """会社の詳細情報を取得する（SQLite中心）"""
    try:
        company_info = get_company_from_db(company_id)
        
        if not company_info:
            return None
        
        # 管理者数を計算
        admins = get_company_admins_from_db(company_id)
        admin_count = len(admins)
        
        return {
            "id": company_info["company_id"],
            "name": company_info["company_name"],
            "admin_count": admin_count,
            "faq_count": company_info["faq_count"],
            "created_at": company_info["created_at"],
            "last_updated": company_info["last_updated"]
        }
        
    except Exception as e:
        print(f"[COMPANY_SERVICE] 会社情報取得エラー: {e}")
        return None

def update_faq_count(company_id, count):
    """FAQの数を更新する（SQLite中心）"""
    try:
        return update_company_faq_count_in_db(company_id, count)
    except Exception as e:
        print(f"[COMPANY_SERVICE] FAQ数更新エラー: {e}")
        return False

def get_company_list():
    """利用可能な会社の一覧を取得する（SQLite中心）"""
    try:
        companies_data = get_all_companies_from_db()
        
        company_list = []
        for company_id in companies_data.keys():
            company_info = get_company_info(company_id)
            if company_info:
                company_list.append(company_info)
        
        return company_list
        
    except Exception as e:
        print(f"[COMPANY_SERVICE] 会社一覧取得エラー: {e}")
        return []
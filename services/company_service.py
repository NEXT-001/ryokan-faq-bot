"""
会社管理に関するサービス
services/company_service.py
"""
import os
import json
import hashlib
import pandas as pd
from datetime import datetime
from utils.constants import get_data_path

def hash_password(password):
    """パスワードをハッシュ化する"""
    return hashlib.sha256(password.encode()).hexdigest()

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
    """会社のsettings.jsonを読み込む"""
    settings_file = get_settings_file_path(company_id)
    
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # settings.jsonが存在しない場合はデフォルト設定を作成
            return create_default_settings(company_id)
    except Exception as e:
        print(f"設定ファイルの読み込みエラー: {e}")
        return create_default_settings(company_id)

def create_default_settings(company_id):
    """デフォルトの設定を作成"""
    # 会社ディレクトリを確認・作成
    company_dir = get_data_path(company_id)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
    
    # デフォルト設定
    if company_id == "demo-company":
        default_settings = {
            "company_id": "demo-company",
            "company_name": "デモ企業",
            "created_at": datetime.now().isoformat(),
            "faq_count": 5,
            "last_updated": datetime.now().isoformat(),
            "admins": {
                "admin": {
                    "password": hash_password("admin123"),
                    "email": "admin@example.com",
                    "created_at": datetime.now().isoformat()
                }
            }
        }
        
        # サンプルFAQを作成
        create_sample_faq(company_id)
    else:
        default_settings = {
            "company_id": company_id,
            "company_name": f"企業_{company_id}",
            "created_at": datetime.now().isoformat(),
            "faq_count": 0,
            "last_updated": datetime.now().isoformat(),
            "admins": {}
        }
    
    # 設定ファイルを保存
    save_company_settings(company_id, default_settings)
    return default_settings

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
    """会社の設定を保存する"""
    settings_file = get_settings_file_path(company_id)
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    
    # last_updatedを更新
    settings["last_updated"] = datetime.now().isoformat()
    
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"設定ファイルの保存エラー: {e}")
        return False

def load_companies(company_id=None):
    """
    会社情報を読み込む（後方互換性のため）
    
    Args:
        company_id (str, optional): 会社ID（使用されない - 後方互換性のため）
        
    Returns:
        dict: 全企業の情報を含む辞書
    """
    # 従来の複数企業対応形式で返すため、全企業の設定を収集
    companies = {}
    
    # companiesディレクトリをスキャン
    base_dir = get_data_path()
    companies_dir = os.path.join(base_dir, "companies")
    
    if os.path.exists(companies_dir):
        for company_dir in os.listdir(companies_dir):
            company_path = os.path.join(companies_dir, company_dir)
            if os.path.isdir(company_path):
                # 各企業の設定を読み込み
                settings = load_company_settings(company_dir)
                if settings:
                    # 従来の形式に変換
                    companies[company_dir] = {
                        "name": settings.get("company_name", company_dir),
                        "created_at": settings.get("created_at", ""),
                        "admins": settings.get("admins", {})
                    }
    
    # デモ企業がない場合は作成
    if not companies:
        demo_settings = create_default_settings("demo-company")
        companies["demo-company"] = {
            "name": demo_settings.get("company_name", "デモ企業"),
            "created_at": demo_settings.get("created_at", ""),
            "admins": demo_settings.get("admins", {})
        }
    
    return companies

def save_companies(companies):
    """
    会社情報を保存する（後方互換性のため）
    
    Args:
        companies (dict): 企業情報の辞書
    """
    # 各企業の設定を個別に保存
    for company_id, company_data in companies.items():
        settings = {
            "company_id": company_id,
            "company_name": company_data.get("name", company_id),
            "created_at": company_data.get("created_at", datetime.now().isoformat()),
            "faq_count": 0,
            "last_updated": datetime.now().isoformat(),
            "admins": company_data.get("admins", {})
        }
        save_company_settings(company_id, settings)

def verify_company_admin(company_id, username, password):
    """会社管理者の認証を行う"""
    settings = load_company_settings(company_id)
    
    # 設定が読み込めない場合
    if not settings:
        return False, "企業設定が見つかりません"
    
    # 会社IDの確認
    if settings.get("company_id") != company_id:
        return False, "企業IDが一致しません"
    
    # 管理者情報が存在しない場合
    if "admins" not in settings or not settings["admins"]:
        return False, "管理者が設定されていません"
    
    # 管理者ユーザーの確認
    if username not in settings["admins"]:
        return False, "ユーザー名が見つかりません"
    
    # パスワードの確認
    admin_info = settings["admins"][username]
    if admin_info["password"] != hash_password(password):
        return False, "パスワードが間違っています"
    
    # 認証成功
    return True, settings.get("company_name", "不明な企業")

def add_company(company_id, company_name, admin_username, admin_password, admin_email):
    """新しい会社を追加する"""
    if not company_id or not company_name or not admin_username or not admin_password:
        return False, "すべての項目を入力してください"
    
    # 既に会社設定が存在するかチェック
    settings_file = get_settings_file_path(company_id)
    if os.path.exists(settings_file):
        return False, "この企業IDは既に使用されています"
    
    # 新しい会社設定を作成
    new_settings = {
        "company_id": company_id,
        "company_name": company_name,
        "created_at": datetime.now().isoformat(),
        "faq_count": 0,
        "last_updated": datetime.now().isoformat(),
        "admins": {
            admin_username: {
                "password": hash_password(admin_password),
                "email": admin_email,
                "created_at": datetime.now().isoformat()
            }
        }
    }
    
    # 会社設定を保存
    if save_company_settings(company_id, new_settings):
        return True, "企業と管理者アカウントを作成しました"
    else:
        return False, "企業の作成に失敗しました"

def add_admin(company_id, username, password, email=""):
    """会社に管理者を追加する"""
    if not username or not password:
        return False, "ユーザー名とパスワードを入力してください"
    
    # 会社設定を読み込み
    settings = load_company_settings(company_id)
    
    # 会社設定が存在しない場合
    if not settings or settings.get("company_id") != company_id:
        return False, "企業が見つかりません"
    
    # adminsキーが存在しない場合は作成
    if "admins" not in settings:
        settings["admins"] = {}
    
    # ユーザー名の重複チェック
    if username in settings["admins"]:
        return False, "このユーザー名は既に使用されています"
    
    # 新しい管理者を追加
    settings["admins"][username] = {
        "password": hash_password(password),
        "email": email,
        "created_at": datetime.now().isoformat()
    }
    
    # 設定を保存
    if save_company_settings(company_id, settings):
        return True, "管理者を追加しました"
    else:
        return False, "管理者の追加に失敗しました"

def get_company_name(company_id):
    """会社IDから会社名を取得する"""
    settings = load_company_settings(company_id)
    
    if settings and "company_name" in settings:
        return settings["company_name"]
    
    return None

def get_company_info(company_id):
    """会社の詳細情報を取得する"""
    settings = load_company_settings(company_id)
    
    if not settings:
        return None
    
    # 管理者数を計算
    admin_count = len(settings.get("admins", {}))
    
    return {
        "id": settings.get("company_id"),
        "name": settings.get("company_name"),
        "admin_count": admin_count,
        "faq_count": settings.get("faq_count", 0),
        "created_at": settings.get("created_at"),
        "last_updated": settings.get("last_updated")
    }

def update_faq_count(company_id, count):
    """FAQの数を更新する"""
    settings = load_company_settings(company_id)
    
    if settings:
        settings["faq_count"] = count
        return save_company_settings(company_id, settings)
    
    return False

def get_company_list():
    """利用可能な会社の一覧を取得する（companiesディレクトリをスキャン）"""
    base_dir = get_data_path()
    companies_dir = os.path.join(base_dir, "companies")
    
    company_list = []
    
    if os.path.exists(companies_dir):
        for company_dir in os.listdir(companies_dir):
            company_path = os.path.join(companies_dir, company_dir)
            if os.path.isdir(company_path):
                # 各会社の設定を読み込み
                company_info = get_company_info(company_dir)
                if company_info:
                    company_list.append(company_info)
    
    return company_list
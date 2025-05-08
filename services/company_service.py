"""
会社管理に関するサービス
company_service.py
"""
import os
import json
import hashlib
import pandas as pd
from datetime import datetime
from config.settings import get_data_path

# 会社情報ファイルのパス
COMPANIES_FILE = os.path.join(get_data_path(), "companies.json")

def hash_password(password):
    """パスワードをハッシュ化する"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_companies():
    """会社情報を読み込む"""
    # データディレクトリの確認
    base_dir = get_data_path()
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    # 会社フォルダの確認
    companies_dir = os.path.join(base_dir, "companies")
    if not os.path.exists(companies_dir):
        os.makedirs(companies_dir)
    
    # 会社ファイルの確認
    if not os.path.exists(COMPANIES_FILE):
        # デフォルト会社とユーザーを作成
        default_companies = {
            "demo-company": {
                "name": "デモ企業",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "admins": {
                    "admin": {
                        "password": hash_password("admin123"),
                        "email": "admin@example.com",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            }
        }
        
        # デモ企業のフォルダを作成
        demo_dir = os.path.join(companies_dir, "demo-company")
        if not os.path.exists(demo_dir):
            os.makedirs(demo_dir)
            
            # サンプルFAQを作成
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
            pd.DataFrame(sample_faq).to_csv(os.path.join(demo_dir, "faq.csv"), index=False)
        
        with open(COMPANIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_companies, f, ensure_ascii=False, indent=2)
    
    try:
        with open(COMPANIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"会社情報の読み込みエラー: {e}")
        return {}

def save_companies(companies):
    """会社情報を保存する"""
    with open(COMPANIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(companies, f, ensure_ascii=False, indent=2)

def verify_company_admin(company_id, username, password):
    """会社管理者の認証を行う"""
    companies = load_companies()
    
    # 会社IDの確認
    if company_id not in companies:
        return False, "企業IDが見つかりません"
    
    # 管理者ユーザーの確認
    if username not in companies[company_id]["admins"]:
        return False, "ユーザー名が見つかりません"
    
    # パスワードの確認
    admin_info = companies[company_id]["admins"][username]
    if admin_info["password"] != hash_password(password):
        return False, "パスワードが間違っています"
    
    # 認証成功
    return True, companies[company_id]["name"]

def add_company(company_id, company_name, admin_username, admin_password, admin_email):
    """新しい会社を追加する"""
    if not company_id or not company_name or not admin_username or not admin_password:
        return False, "すべての項目を入力してください"
    
    # 会社情報の読み込み
    companies = load_companies()
    
    # 会社IDの重複チェック
    if company_id in companies:
        return False, "この企業IDは既に使用されています"
    
    # 新しい会社情報を追加
    companies[company_id] = {
        "name": company_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admins": {
            admin_username: {
                "password": hash_password(admin_password),
                "email": admin_email,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    }
    
    # 会社フォルダを作成
    company_dir = os.path.join(get_data_path(), "companies", company_id)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
    
    # 会社情報を保存
    save_companies(companies)
    
    return True, "企業と管理者アカウントを作成しました"

def add_admin(company_id, username, password, email=""):
    """会社に管理者を追加する"""
    if not username or not password:
        return False, "ユーザー名とパスワードを入力してください"
    
    # 会社情報の読み込み
    companies = load_companies()
    
    # 会社IDの確認
    if company_id not in companies:
        return False, "企業IDが見つかりません"
    
    # ユーザー名の重複チェック
    if username in companies[company_id]["admins"]:
        return False, "このユーザー名は既に使用されています"
    
    # 新しい管理者を追加
    companies[company_id]["admins"][username] = {
        "password": hash_password(password),
        "email": email,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 会社情報を保存
    save_companies(companies)
    
    return True, "管理者を追加しました"

def get_company_name(company_id):
    """会社IDから会社名を取得する"""
    companies = load_companies()
    
    if company_id in companies:
        return companies[company_id]["name"]
    
    return None

def get_company_list():
    """会社の一覧を取得する"""
    companies = load_companies()
    
    company_list = []
    for company_id, company_info in companies.items():
        company_list.append({
            "id": company_id,
            "name": company_info["name"],
            "admin_count": len(company_info["admins"]),
            "created_at": company_info["created_at"]
        })
    
    return company_list
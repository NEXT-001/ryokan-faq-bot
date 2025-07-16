#!/usr/bin/env python3
"""
依存関係検証スクリプト
Dependency Validation Script

このスクリプトは requirements.txt と requirements-dev.txt の整合性を確認します。
This script validates the consistency between requirements.txt and requirements-dev.txt.
"""

import os
import sys
import subprocess
from pathlib import Path

def parse_requirements(file_path):
    """requirements ファイルを解析して依存関係のリストを返す"""
    requirements = []
    
    if not os.path.exists(file_path):
        print(f"❌ ファイルが見つかりません: {file_path}")
        return requirements
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # コメント行や空行をスキップ
            if line and not line.startswith('#') and not line.startswith('-r'):
                # パッケージ名を抽出（バージョン指定を除く）
                package_name = line.split('>=')[0].split('==')[0].split('<')[0].strip()
                if package_name:
                    requirements.append(package_name)
    
    return requirements

def check_file_structure():
    """ファイル構造をチェック"""
    print("📁 ファイル構造チェック...")
    
    required_files = [
        'requirements.txt',
        'requirements-dev.txt',
        'DEPENDENCY_MANAGEMENT.md'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
        else:
            print(f"✅ {file}")
    
    if missing_files:
        print(f"❌ 不足ファイル: {', '.join(missing_files)}")
        return False
    
    # requirements-minimal.txt が削除されているかチェック
    if os.path.exists('requirements-minimal.txt'):
        print("⚠️  requirements-minimal.txt が残っています（削除推奨）")
    else:
        print("✅ requirements-minimal.txt は正常に削除されています")
    
    return True

def validate_requirements():
    """requirements ファイルの内容を検証"""
    print("\n📋 依存関係検証...")
    
    # requirements.txt の解析
    prod_requirements = parse_requirements('requirements.txt')
    print(f"✅ requirements.txt: {len(prod_requirements)} パッケージ")
    
    # requirements-dev.txt の解析
    dev_requirements = parse_requirements('requirements-dev.txt')
    print(f"✅ requirements-dev.txt: {len(dev_requirements)} パッケージ")
    
    # 重複チェック
    duplicates = set(prod_requirements) & set(dev_requirements)
    if duplicates:
        print(f"⚠️  重複パッケージ: {', '.join(duplicates)}")
        print("   注意: requirements-dev.txt は requirements.txt を継承するため、")
        print("   重複は -r requirements.txt により解決されます")
    
    # 必須パッケージの存在確認
    essential_packages = ['streamlit', 'pandas', 'numpy', 'anthropic', 'voyageai']
    missing_essential = []
    
    for package in essential_packages:
        if package not in prod_requirements:
            missing_essential.append(package)
    
    if missing_essential:
        print(f"❌ 必須パッケージが不足: {', '.join(missing_essential)}")
        return False
    else:
        print("✅ 必須パッケージは全て含まれています")
    
    return True

def test_installation():
    """インストールテスト（ドライラン）"""
    print("\n🧪 インストールテスト...")
    
    try:
        # requirements.txt のドライラン
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '--dry-run', '-r', 'requirements.txt'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ requirements.txt: インストール可能")
        else:
            print(f"❌ requirements.txt: インストールエラー\n{result.stderr}")
            return False
        
        # requirements-dev.txt のドライラン
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '--dry-run', '-r', 'requirements-dev.txt'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ requirements-dev.txt: インストール可能")
        else:
            print(f"❌ requirements-dev.txt: インストールエラー\n{result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  インストールテストがタイムアウトしました")
        return False
    except Exception as e:
        print(f"⚠️  インストールテストでエラー: {e}")
        return False
    
    return True

def main():
    """メイン実行関数"""
    print("🔍 Ryokan FAQ Bot - 依存関係検証")
    print("=" * 50)
    
    # プロジェクトルートに移動
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"📂 作業ディレクトリ: {os.getcwd()}")
    
    success = True
    
    # 1. ファイル構造チェック
    if not check_file_structure():
        success = False
    
    # 2. 依存関係検証
    if not validate_requirements():
        success = False
    
    # 3. インストールテスト
    if not test_installation():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 全ての検証が成功しました！")
        print("\n📖 使用方法:")
        print("   本番環境: pip install -r requirements.txt")
        print("   開発環境: pip install -r requirements-dev.txt")
        print("   詳細: DEPENDENCY_MANAGEMENT.md を参照")
    else:
        print("❌ 検証に失敗しました。上記のエラーを確認してください。")
        sys.exit(1)

if __name__ == "__main__":
    main()

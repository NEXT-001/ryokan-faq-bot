"""
詳細フォーム解析ツール
tests/detailed_form_analysis.py

登録フォームの詳細な構造分析とStreamlitコンポーネント検証
"""
import sys
import os
import requests
from bs4 import BeautifulSoup
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.unified_config import UnifiedConfig


def analyze_streamlit_app_structure(base_url="http://localhost:8502"):
    """Streamlitアプリケーションの構造分析"""
    
    print(f"🔍 Streamlitアプリケーション構造分析開始")
    print(f"対象URL: {base_url}")
    print("=" * 50)
    
    # テストするページとその期待要素
    pages_to_test = {
        "登録ページ": {
            "url": "/?mode=reg",
            "expected_elements": [
                "会社名", "担当者名", "メールアドレス", "パスワード", 
                "郵便番号", "都道府県", "市区町村", "番地・建物名", "登録"
            ],
            "expected_form_fields": ["company", "name", "email", "password"]
        },
        "ユーザーページ": {
            "url": "/?mode=user&company=demo-company",
            "expected_elements": ["FAQチャットボット", "質問", "送信"],
            "expected_form_fields": []
        },
        "管理者ページ": {
            "url": "/?mode=admin&company=demo-company",
            "expected_elements": ["管理者", "ログイン"],
            "expected_form_fields": []
        }
    }
    
    results = {}
    
    for page_name, config in pages_to_test.items():
        print(f"\n📄 {page_name} の分析")
        print(f"URL: {config['url']}")
        
        try:
            # ページの取得
            response = requests.get(f"{base_url}{config['url']}", timeout=15)
            
            if response.status_code != 200:
                print(f"❌ HTTPエラー: {response.status_code}")
                results[page_name] = {"error": f"HTTP {response.status_code}"}
                continue
            
            content = response.text
            
            # 基本的なStreamlit要素の確認
            streamlit_indicators = [
                "streamlit",
                "st-",
                "data-testid",
                "stApp",
                "stForm",
                "stTextInput",
                "stButton"
            ]
            
            found_indicators = []
            for indicator in streamlit_indicators:
                if indicator.lower() in content.lower():
                    found_indicators.append(indicator)
            
            print(f"✅ Streamlit要素検出: {len(found_indicators)}/7")
            
            # HTMLフォーム要素の検出
            soup = BeautifulSoup(content, 'html.parser')
            
            # フォームの検出
            forms = soup.find_all('form')
            inputs = soup.find_all('input')
            buttons = soup.find_all('button')
            textareas = soup.find_all('textarea')
            
            print(f"📝 HTMLフォーム要素:")
            print(f"  - フォーム: {len(forms)}")
            print(f"  - 入力フィールド: {len(inputs)}")
            print(f"  - ボタン: {len(buttons)}")
            print(f"  - テキストエリア: {len(textareas)}")
            
            # 期待される要素の検出
            missing_elements = []
            found_elements = []
            
            for expected in config['expected_elements']:
                if expected in content:
                    found_elements.append(expected)
                else:
                    missing_elements.append(expected)
            
            print(f"🎯 期待要素の検出:")
            print(f"  - 発見: {len(found_elements)}/{len(config['expected_elements'])}")
            if found_elements:
                print(f"  - 発見された要素: {', '.join(found_elements)}")
            if missing_elements:
                print(f"  - ❌ 未発見の要素: {', '.join(missing_elements)}")
            
            # Streamlit特有の要素分析
            streamlit_elements = analyze_streamlit_specific_elements(content)
            print(f"🔧 Streamlit特有要素:")
            for element_type, count in streamlit_elements.items():
                print(f"  - {element_type}: {count}")
            
            # JavaScript/React要素の検出
            js_react_indicators = [
                "React", "reactjs", "useState", "useEffect",
                "window.streamlit", "streamlitApi"
            ]
            
            found_js_react = []
            for indicator in js_react_indicators:
                if indicator in content:
                    found_js_react.append(indicator)
            
            if found_js_react:
                print(f"⚛️  React/JS要素: {', '.join(found_js_react)}")
            
            # 分析結果の保存
            results[page_name] = {
                "status_code": response.status_code,
                "content_length": len(content),
                "streamlit_indicators": found_indicators,
                "html_elements": {
                    "forms": len(forms),
                    "inputs": len(inputs),
                    "buttons": len(buttons),
                    "textareas": len(textareas)
                },
                "expected_elements": {
                    "found": found_elements,
                    "missing": missing_elements,
                    "detection_rate": len(found_elements) / len(config['expected_elements']) * 100
                },
                "streamlit_elements": streamlit_elements,
                "js_react_elements": found_js_react
            }
            
            print(f"✅ {page_name} 分析完了")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 接続エラー: {e}")
            results[page_name] = {"error": f"Connection error: {e}"}
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            results[page_name] = {"error": f"Unexpected error: {e}"}
    
    return results


def analyze_streamlit_specific_elements(content):
    """Streamlit特有の要素を分析"""
    elements = {}
    
    # Streamlit要素のパターン
    patterns = {
        "text_input": r'data-testid="stTextInput"',
        "button": r'data-testid="stButton"',
        "form": r'data-testid="stForm"',
        "markdown": r'data-testid="stMarkdown"',
        "columns": r'data-testid="column"',
        "sidebar": r'data-testid="stSidebar"',
        "selectbox": r'data-testid="stSelectbox"',
        "checkbox": r'data-testid="stCheckbox"'
    }
    
    for element_name, pattern in patterns.items():
        matches = re.findall(pattern, content, re.IGNORECASE)
        elements[element_name] = len(matches)
    
    return elements


def generate_form_analysis_report(results):
    """フォーム分析レポートの生成"""
    
    print("\n" + "="*60)
    print("📊 STREAMLIT フォーム分析レポート")
    print("="*60)
    
    total_pages = len(results)
    successful_pages = len([r for r in results.values() if "error" not in r])
    
    print(f"\n🎯 概要:")
    print(f"  - 分析対象ページ数: {total_pages}")
    print(f"  - 成功分析: {successful_pages}")
    print(f"  - エラー: {total_pages - successful_pages}")
    
    print(f"\n📄 ページ別詳細結果:")
    
    for page_name, result in results.items():
        print(f"\n### {page_name}")
        
        if "error" in result:
            print(f"  ❌ エラー: {result['error']}")
            continue
        
        detection_rate = result['expected_elements']['detection_rate']
        status = "✅" if detection_rate == 100 else "⚠️" if detection_rate >= 50 else "❌"
        
        print(f"  {status} 要素検出率: {detection_rate:.1f}%")
        print(f"  📝 HTMLフォーム要素: {result['html_elements']['forms']} forms, {result['html_elements']['inputs']} inputs")
        print(f"  🔧 Streamlit要素: {sum(result['streamlit_elements'].values())} 個")
        
        if result['expected_elements']['missing']:
            print(f"  ❌ 未検出要素: {', '.join(result['expected_elements']['missing'])}")
    
    # 改善提案
    print(f"\n💡 改善提案:")
    
    registration_result = results.get("登録ページ", {})
    if "error" not in registration_result:
        detection_rate = registration_result['expected_elements']['detection_rate']
        if detection_rate < 100:
            print(f"  1. 登録ページの要素検出率が {detection_rate:.1f}% です")
            print(f"     → Streamlitフォーム要素の表示確認が必要")
            
            missing = registration_result['expected_elements']['missing']
            if missing:
                print(f"     → 未検出要素を確認: {', '.join(missing)}")
    
    # テスト環境の確認
    print(f"\n🔧 テスト環境確認:")
    print(f"  - Streamlitサーバーが正常に稼働していることを確認")
    print(f"  - ブラウザでの直接アクセステストを推奨")
    print(f"  - JavaScript無効環境でのテストも検討")
    
    return results


def check_server_accessibility(base_url="http://localhost:8502"):
    """サーバーアクセシビリティの確認"""
    
    print(f"\n🔍 サーバーアクセシビリティ確認")
    print(f"対象URL: {base_url}")
    
    try:
        # ヘルスチェック
        response = requests.get(base_url, timeout=10)
        print(f"✅ サーバーステータス: HTTP {response.status_code}")
        print(f"✅ レスポンスサイズ: {len(response.text)} bytes")
        
        # レスポンスヘッダーの確認
        print(f"📋 重要なレスポンスヘッダー:")
        important_headers = ['content-type', 'server', 'x-frame-options']
        for header in important_headers:
            value = response.headers.get(header, 'Not set')
            print(f"  - {header}: {value}")
        
        # Streamlitサーバーかどうかの確認
        if 'streamlit' in response.text.lower():
            print(f"✅ Streamlitサーバーを確認")
        else:
            print(f"⚠️  Streamlitの兆候が見つかりません")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ 接続エラー: サーバーが起動していない可能性があります")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ タイムアウト: サーバーの応答が遅すぎます")
        return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False


def main():
    """メイン実行関数"""
    
    base_url = "http://localhost:8502"
    
    print("🚀 Streamlit アプリケーション フォーム分析ツール")
    print(f"バージョン: 1.0.0")
    print(f"対象: {base_url}")
    
    # サーバーアクセシビリティチェック
    if not check_server_accessibility(base_url):
        print("\n❌ サーバーにアクセスできません。")
        print("💡 対処方法:")
        print("  1. Streamlitサーバーが起動していることを確認")
        print("  2. ポート番号が正しいことを確認")
        print("  3. ファイアウォール設定を確認")
        return
    
    # 構造分析の実行
    results = analyze_streamlit_app_structure(base_url)
    
    # レポート生成
    generate_form_analysis_report(results)
    
    # 結果の保存
    import json
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"streamlit_form_analysis_{timestamp}.json"
    filepath = os.path.join(UnifiedConfig.LOGS_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 分析結果を保存: {filepath}")
    except Exception as e:
        print(f"⚠️  ファイル保存エラー: {e}")
    
    print(f"\n🎉 フォーム分析完了!")


if __name__ == "__main__":
    main()
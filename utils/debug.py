# utils/debug.py - デバッグ機能
import streamlit as st
import os
from config.settings import is_test_mode
from core.auth import is_logged_in
from core.database import get_all_registered_users
from core.company_manager import get_company_folder_info

def show_debug_info():
    """デバッグ情報を表示する（テストモード時のみ）"""
    try:
        if is_test_mode():
            with st.expander("🔧 デバッグ情報"):
                # セッション状態
                st.write("セッション状態:")
                for key, value in st.session_state.items():
                    if key not in ["conversation_history"]:
                        st.write(f"- {key}: {value}")
                
                # ログイン状態のチェック
                st.write(f"is_logged_in()の結果: {is_logged_in()}")
                
                # 環境変数の状態
                st.write("環境変数:")
                st.write(f"- TEST_MODE: {os.getenv('TEST_MODE', 'false')}")
                
                # モード切替リンク
                test_company = "demo-company"
                st.write("モード切替リンク:")
                st.markdown(f"- [ユーザーモード](?mode=user&company_id={test_company})")
                st.markdown(f"- [管理者モード](?mode=admin&company_id={test_company})")
                st.markdown(f"- [登録モード](?mode=reg)")
                
                # セッションリセットボタン
                if st.button("セッションをリセット"):
                    # セッションだけクリアして、URLはそのまま
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.success("セッションをリセットしました。")
    except:
        pass

def show_company_info_debug():
    """登録された会社情報をデバッグ表示する（テストモード時のみ）"""
    try:
        if is_test_mode():
            with st.expander("🔧 登録済み会社情報（デバッグ用）"):
                try:
                    users = get_all_registered_users()
                    
                    if users:
                        st.write("SQLiteデータベースの登録情報:")
                        for user in users:
                            company_id, company_name, name, email, verified, created = user
                            status = "✅ 認証済み" if verified else "⏳ 認証待ち"
                            st.write(f"- 会社ID: `{company_id}` | 会社名: {company_name}")
                            st.write(f"  担当者: {name} | メール: {email} | {status}")
                            
                            # フォルダ情報を取得
                            folder_info = get_company_folder_info(company_id)
                            if folder_info["folder_exists"]:
                                st.write(f"  📁 フォルダ: 作成済み ({folder_info['folder_path']})")
                                
                                # ファイル存在チェック
                                for file_name, file_info in folder_info["files"].items():
                                    if file_info["exists"]:
                                        st.write(f"    ✅ {file_name} ({file_info['size']} bytes)")
                                    else:
                                        st.write(f"    ❌ {file_name}")
                            else:
                                st.write(f"  📁 フォルダ: 未作成")
                            st.write("---")
                    else:
                        st.write("登録されたユーザーはありません")
                except Exception as e:
                    st.write(f"エラー: {e}")
    except:
        pass
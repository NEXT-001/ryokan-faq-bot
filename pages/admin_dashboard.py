"""
管理者ダッシュボード（main.py対応版）
pages/admin_dashboard.py
"""
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json
import io
import zipfile
from utils.constants import get_data_path
from services.company_service import (
    load_company_settings, 
    verify_company_admin_by_email,
    get_company_info,
    update_faq_count
)

def verify_admin_session():
    """管理者セッションの検証"""
    if 'admin_logged_in' not in st.session_state or not st.session_state.admin_logged_in:
        st.error("❌ 管理者としてログインしてください")
        return False
    
    required_keys = ['company_id', 'company_name', 'admin_email']
    if not all(key in st.session_state for key in required_keys):
        st.error("❌ セッション情報が不完全です。再度ログインしてください")
        return False
    
    return True

def load_faq_data(company_id):
    """FAQデータを読み込む"""
    try:
        faq_file = os.path.join(get_data_path(company_id), "faq.csv")
        if os.path.exists(faq_file):
            return pd.read_csv(faq_file)
        else:
            return pd.DataFrame(columns=["question", "answer"])
    except Exception as e:
        st.error(f"FAQデータの読み込みエラー: {e}")
        return pd.DataFrame(columns=["question", "answer"])

def save_faq_data(company_id, df):
    """FAQデータを保存する"""
    try:
        company_dir = get_data_path(company_id)
        os.makedirs(company_dir, exist_ok=True)
        faq_file = os.path.join(company_dir, "faq.csv")
        df.to_csv(faq_file, index=False)
        
        # FAQ数を更新
        update_faq_count(company_id, len(df))
        return True
    except Exception as e:
        st.error(f"FAQデータの保存エラー: {e}")
        return False

def load_search_history(company_id):
    """検索履歴を読み込む"""
    try:
        history_file = os.path.join(get_data_path(company_id), "search_history.json")
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        st.error(f"検索履歴の読み込みエラー: {e}")
        return []

def dashboard_overview():
    """ダッシュボード概要"""
    st.header("📊 ダッシュボード概要")
    
    company_id = st.session_state.company_id
    company_info = get_company_info(company_id)
    faq_df = load_faq_data(company_id)
    search_history = load_search_history(company_id)
    
    # メトリクス表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📚 FAQ総数",
            value=len(faq_df),
            delta=f"前回更新: {company_info.get('last_updated', 'N/A')[:10] if company_info else 'N/A'}"
        )
    
    with col2:
        st.metric(
            label="🔍 検索履歴数",
            value=len(search_history),
            delta="過去30日間"
        )
    
    with col3:
        st.metric(
            label="👥 管理者数",
            value=company_info.get('admin_count', 0) if company_info else 0
        )
    
    with col4:
        st.metric(
            label="📅 作成日",
            value=company_info.get('created_at', 'N/A')[:10] if company_info else 'N/A'
        )
    
    # 最近のアクティビティ
    st.subheader("🕒 最近のアクティビティ")
    
    if len(search_history) > 0:
        recent_searches = sorted(search_history, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
        
        activity_data = []
        for search in recent_searches:
            activity_data.append({
                "時刻": search.get('timestamp', 'N/A'),
                "検索クエリ": search.get('query', 'N/A'),
                "マッチしたFAQ": search.get('matched_faq', 'なし'),
                "スコア": f"{search.get('score', 0):.2f}"
            })
        
        st.dataframe(pd.DataFrame(activity_data), use_container_width=True)
    else:
        st.info("まだ検索履歴がありません")

def faq_management():
    """FAQ管理"""
    st.header("📝 FAQ管理")
    
    company_id = st.session_state.company_id
    faq_df = load_faq_data(company_id)
    
    # タブで機能分割
    tab1, tab2, tab3, tab4 = st.tabs(["FAQ一覧", "FAQ追加", "FAQ編集", "FAQ削除"])
    
    with tab1:
        st.subheader("📋 FAQ一覧")
        
        if len(faq_df) > 0:
            # 検索機能
            search_query = st.text_input("🔍 FAQを検索:", placeholder="質問または回答で検索...")
            
            if search_query:
                mask = (faq_df['question'].str.contains(search_query, case=False, na=False) | 
                       faq_df['answer'].str.contains(search_query, case=False, na=False))
                filtered_df = faq_df[mask]
            else:
                filtered_df = faq_df
            
            # FAQ表示
            for idx, row in filtered_df.iterrows():
                with st.expander(f"FAQ #{idx + 1}: {row['question'][:50]}..."):
                    st.write("**質問:**")
                    st.write(row['question'])
                    st.write("**回答:**")
                    st.write(row['answer'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"編集 #{idx + 1}", key=f"edit_{idx}"):
                            st.session_state.edit_faq_index = idx
                            st.rerun()
                    
                    with col2:
                        if st.button(f"削除 #{idx + 1}", key=f"delete_{idx}"):
                            st.session_state.delete_faq_index = idx
                            st.rerun()
        else:
            st.info("FAQがまだ登録されていません。「FAQ追加」タブから追加してください。")
    
    with tab2:
        st.subheader("➕ FAQ追加")
        
        with st.form("add_faq_form"):
            new_question = st.text_area("質問:", height=100, placeholder="顧客からの質問を入力してください...")
            new_answer = st.text_area("回答:", height=150, placeholder="回答を入力してください...")
            
            submitted = st.form_submit_button("📝 FAQ追加", type="primary")
            
            if submitted:
                if new_question.strip() and new_answer.strip():
                    new_faq = pd.DataFrame({
                        'question': [new_question.strip()],
                        'answer': [new_answer.strip()]
                    })
                    
                    updated_df = pd.concat([faq_df, new_faq], ignore_index=True)
                    
                    if save_faq_data(company_id, updated_df):
                        st.success("✅ FAQを追加しました！")
                        st.rerun()
                    else:
                        st.error("❌ FAQの追加に失敗しました")
                else:
                    st.error("❌ 質問と回答の両方を入力してください")
    
    with tab3:
        st.subheader("✏️ FAQ編集")
        
        if len(faq_df) > 0:
            edit_index = st.selectbox(
                "編集するFAQを選択:",
                range(len(faq_df)),
                format_func=lambda x: f"FAQ #{x + 1}: {faq_df.iloc[x]['question'][:50]}..."
            )
            
            if edit_index is not None:
                with st.form("edit_faq_form"):
                    current_question = faq_df.iloc[edit_index]['question']
                    current_answer = faq_df.iloc[edit_index]['answer']
                    
                    edited_question = st.text_area("質問:", value=current_question, height=100)
                    edited_answer = st.text_area("回答:", value=current_answer, height=150)
                    
                    submitted = st.form_submit_button("💾 更新", type="primary")
                    
                    if submitted:
                        if edited_question.strip() and edited_answer.strip():
                            faq_df.iloc[edit_index, faq_df.columns.get_loc('question')] = edited_question.strip()
                            faq_df.iloc[edit_index, faq_df.columns.get_loc('answer')] = edited_answer.strip()
                            
                            if save_faq_data(company_id, faq_df):
                                st.success("✅ FAQを更新しました！")
                                st.rerun()
                            else:
                                st.error("❌ FAQの更新に失敗しました")
                        else:
                            st.error("❌ 質問と回答の両方を入力してください")
        else:
            st.info("編集可能なFAQがありません")
    
    with tab4:
        st.subheader("🗑️ FAQ削除")
        
        if len(faq_df) > 0:
            delete_indices = st.multiselect(
                "削除するFAQを選択:",
                range(len(faq_df)),
                format_func=lambda x: f"FAQ #{x + 1}: {faq_df.iloc[x]['question'][:50]}..."
            )
            
            if delete_indices:
                st.warning(f"⚠️ {len(delete_indices)}個のFAQを削除しようとしています")
                
                for idx in delete_indices:
                    with st.expander(f"削除予定 FAQ #{idx + 1}"):
                        st.write("**質問:**", faq_df.iloc[idx]['question'])
                        st.write("**回答:**", faq_df.iloc[idx]['answer'])
                
                if st.button("🗑️ 選択したFAQを削除", type="secondary"):
                    updated_df = faq_df.drop(delete_indices).reset_index(drop=True)
                    
                    if save_faq_data(company_id, updated_df):
                        st.success(f"✅ {len(delete_indices)}個のFAQを削除しました！")
                        st.rerun()
                    else:
                        st.error("❌ FAQの削除に失敗しました")
        else:
            st.info("削除可能なFAQがありません")

def bulk_faq_upload():
    """FAQ一括登録"""
    st.header("📁 FAQ一括登録")
    
    company_id = st.session_state.company_id
    
    st.info("💡 CSVファイルまたはExcelファイルからFAQを一括で登録できます")
    
    # サンプルファイルダウンロード
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 サンプルファイル")
        sample_data = pd.DataFrame({
            'question': [
                'サンプル質問1',
                'サンプル質問2',
                'サンプル質問3'
            ],
            'answer': [
                'サンプル回答1',
                'サンプル回答2', 
                'サンプル回答3'
            ]
        })
        
        # CSVダウンロード
        csv_data = sample_data.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 サンプルCSVダウンロード",
            data=csv_data,
            file_name="faq_sample.csv",
            mime="text/csv"
        )
        
        # Excelダウンロード
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            sample_data.to_excel(writer, index=False, sheet_name='FAQ')
        excel_data = excel_buffer.getvalue()
        
        st.download_button(
            label="📥 サンプルExcelダウンロード",
            data=excel_data,
            file_name="faq_sample.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        st.subheader("📤 ファイルアップロード")
        
        uploaded_file = st.file_uploader(
            "FAQファイルを選択:",
            type=['csv', 'xlsx', 'xls'],
            help="CSV、Excel形式のファイルをアップロードしてください"
        )
        
        if uploaded_file is not None:
            try:
                # ファイル形式に応じて読み込み
                if uploaded_file.name.endswith('.csv'):
                    upload_df = pd.read_csv(uploaded_file)
                else:
                    upload_df = pd.read_excel(uploaded_file)
                
                # データ検証
                required_columns = ['question', 'answer']
                if all(col in upload_df.columns for col in required_columns):
                    st.success(f"✅ ファイル読み込み成功: {len(upload_df)}件のFAQ")
                    
                    # プレビュー表示
                    st.subheader("📋 アップロード予定のFAQ（プレビュー）")
                    st.dataframe(upload_df, use_container_width=True)
                    
                    # アップロード方法選択
                    upload_mode = st.radio(
                        "アップロード方法:",
                        ["既存FAQに追加", "既存FAQを置き換え"],
                        help="追加: 既存のFAQを保持して新しいFAQを追加\n置き換え: 既存のFAQをすべて削除して新しいFAQのみにする"
                    )
                    
                    if st.button("📝 FAQを一括登録", type="primary"):
                        current_faq_df = load_faq_data(company_id)
                        
                        if upload_mode == "既存FAQに追加":
                            final_df = pd.concat([current_faq_df, upload_df], ignore_index=True)
                        else:
                            final_df = upload_df.copy()
                        
                        # 重複除去
                        final_df = final_df.drop_duplicates(subset=['question'], keep='last')
                        
                        if save_faq_data(company_id, final_df):
                            st.success(f"✅ {len(upload_df)}件のFAQを一括登録しました！")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ FAQの一括登録に失敗しました")
                
                else:
                    st.error(f"❌ 必要な列が不足しています: {required_columns}")
                    st.write("アップロードファイルの列:", list(upload_df.columns))
                    
            except Exception as e:
                st.error(f"❌ ファイル読み込みエラー: {e}")

def search_history():
    """検索履歴"""
    st.header("🔍 検索履歴")
    
    company_id = st.session_state.company_id
    history = load_search_history(company_id)
    
    if history:
        # フィルター機能
        col1, col2 = st.columns(2)
        
        with col1:
            date_filter = st.date_input("📅 日付でフィルター:")
        
        with col2:
            query_filter = st.text_input("🔍 クエリでフィルター:")
        
        # データ処理
        df = pd.DataFrame(history)
        
        if date_filter:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            df = df[df['date'] == date_filter]
        
        if query_filter:
            df = df[df['query'].str.contains(query_filter, case=False, na=False)]
        
        # 統計情報
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 総検索数", len(history))
        
        with col2:
            successful_searches = len([h for h in history if h.get('matched_faq')])
            st.metric("✅ 成功した検索", successful_searches)
        
        with col3:
            if len(history) > 0:
                success_rate = (successful_searches / len(history)) * 100
                st.metric("📈 成功率", f"{success_rate:.1f}%")
        
        # 履歴表示
        st.subheader("📋 検索履歴詳細")
        
        if len(df) > 0:
            # ページネーション
            items_per_page = 20
            total_pages = (len(df) - 1) // items_per_page + 1
            
            if total_pages > 1:
                page = st.selectbox("ページ:", range(1, total_pages + 1)) - 1
                start_idx = page * items_per_page
                end_idx = min(start_idx + items_per_page, len(df))
                display_df = df.iloc[start_idx:end_idx]
            else:
                display_df = df
            
            for idx, row in display_df.iterrows():
                with st.expander(f"🔍 {row['query']} - {row['timestamp'][:16]}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**検索クエリ:**", row['query'])
                        st.write("**検索時刻:**", row['timestamp'])
                        st.write("**スコア:**", f"{row.get('score', 0):.3f}")
                    
                    with col2:
                        if row.get('matched_faq'):
                            st.write("**マッチしたFAQ:**", row['matched_faq'])
                        else:
                            st.write("**結果:**", "マッチするFAQなし")
        else:
            st.info("指定した条件に該当する検索履歴がありません")
        
        # 履歴クリア
        st.subheader("🗑️ 履歴管理")
        if st.button("🗑️ 検索履歴をクリア", type="secondary"):
            try:
                history_file = os.path.join(get_data_path(company_id), "search_history.json")
                if os.path.exists(history_file):
                    os.remove(history_file)
                st.success("✅ 検索履歴をクリアしました")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 履歴クリアエラー: {e}")
    
    else:
        st.info("まだ検索履歴がありません")

def export_data():
    """データエクスポート"""
    st.header("📤 データエクスポート")
    
    company_id = st.session_state.company_id
    faq_df = load_faq_data(company_id)
    search_history = load_search_history(company_id)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 FAQデータエクスポート")
        
        if len(faq_df) > 0:
            # CSV形式
            csv_data = faq_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 FAQをCSVでダウンロード",
                data=csv_data,
                file_name=f"faq_{company_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            # Excel形式
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                faq_df.to_excel(writer, index=False, sheet_name='FAQ')
            excel_data = excel_buffer.getvalue()
            
            st.download_button(
                label="📥 FAQをExcelでダウンロード",
                data=excel_data,
                file_name=f"faq_{company_id}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("エクスポートするFAQがありません")
    
    with col2:
        st.subheader("🔍 検索履歴エクスポート")
        
        if search_history:
            # JSON形式
            json_data = json.dumps(search_history, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 検索履歴をJSONでダウンロード",
                data=json_data,
                file_name=f"search_history_{company_id}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
            
            # CSV形式
            history_df = pd.DataFrame(search_history)
            csv_data = history_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 検索履歴をCSVでダウンロード",
                data=csv_data,
                file_name=f"search_history_{company_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("エクスポートする検索履歴がありません")
    
    # 全データ一括エクスポート
    st.subheader("📦 全データ一括エクスポート")
    
    if st.button("📦 全データをZIPでダウンロード", type="primary"):
        try:
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # FAQデータ
                if len(faq_df) > 0:
                    csv_data = faq_df.to_csv(index=False, encoding='utf-8-sig')
                    zip_file.writestr("faq.csv", csv_data)
                
                # 検索履歴
                if search_history:
                    json_data = json.dumps(search_history, ensure_ascii=False, indent=2)
                    zip_file.writestr("search_history.json", json_data)
                
                # メタデータ
                metadata = {
                    "company_id": company_id,
                    "company_name": st.session_state.company_name,
                    "export_date": datetime.now().isoformat(),
                    "faq_count": len(faq_df),
                    "search_history_count": len(search_history)
                }
                zip_file.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
            
            zip_data = zip_buffer.getvalue()
            
            st.download_button(
                label="📥 ZIPファイルをダウンロード",
                data=zip_data,
                file_name=f"all_data_{company_id}_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip"
            )
            
        except Exception as e:
            st.error(f"❌ ZIPファイル作成エラー: {e}")

def settings():
    """設定"""
    st.header("⚙️ 設定")
    
    company_id = st.session_state.company_id
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 企業情報")
        st.info(f"企業ID: {company_id}")
        st.info(f"企業名: {st.session_state.company_name}")
        st.info(f"管理者メール: {st.session_state.admin_email}")
    
    with col2:
        st.subheader("🔧 システム設定")
        
        # ダミー設定（実際のシステムに応じて調整）
        auto_backup = st.checkbox("自動バックアップ", value=True)
        email_notifications = st.checkbox("メール通知", value=False)
        search_logging = st.checkbox("検索ログ記録", value=True)
        
        if st.button("💾 設定を保存"):
            st.success("✅ 設定を保存しました")
    
    # ログアウト
    st.subheader("🚪 ログアウト")
    if st.button("🚪 ログアウト", type="secondary"):
        # セッション状態をクリア
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("✅ ログアウトしました")
        st.rerun()

def admin_page(company_id=None):
    """管理者ページのメイン関数（main.py用）"""
    # company_idが渡された場合はセッションに保存
    if company_id and 'company_id' not in st.session_state:
        st.session_state.company_id = company_id
    # 管理者セッション検証
    if not verify_admin_session():
        st.error("❌ 管理者としてログインしてください")
        if st.button("🔐 管理者ログインに移動"):
            st.session_state.page = "admin_login"
            st.rerun()
        return
    
    # ヘッダー
    st.title(f"⚙️ 管理者ダッシュボード - {st.session_state.company_name}")
    
    # サイドバーメニュー
    with st.sidebar:
        st.title("📋 メニュー")
        
        # 企業情報表示
        st.info(f"🏢 {st.session_state.company_name}")
        st.info(f"👤 {st.session_state.admin_email}")
        
        # メニュー選択
        menu_options = [
            "📊 ダッシュボード",
            "📝 FAQ管理", 
            "📁 FAQ一括登録",
            "🔍 検索履歴",
            "📤 データエクスポート",
            "⚙️ 設定"
        ]
        
        selected_menu = st.radio("機能を選択:", menu_options)
    
    # 選択されたメニューに応じて画面を表示
    if selected_menu == "📊 ダッシュボード":
        dashboard_overview()
    elif selected_menu == "📝 FAQ管理":
        faq_management()
    elif selected_menu == "📁 FAQ一括登録":
        bulk_faq_upload()
    elif selected_menu == "🔍 検索履歴":
        search_history()
    elif selected_menu == "📤 データエクスポート":
        export_data()
    elif selected_menu == "⚙️ 設定":
        settings()
"""
FAQ管理機能 - 管理者がFAQを追加・編集・削除するための機能
admin_faq_management.py
"""
import os
import pandas as pd
import streamlit as st
from datetime import datetime
import time
from services.embedding_service import create_embeddings
from services.login_service import get_current_company_id
from config.unified_config import UnifiedConfig
from core.database import execute_query, fetch_dict, fetch_dict_one

def load_faq_data(company_id):
    """
    指定された会社のFAQデータをデータベースから読み込む
    
    Args:
        company_id (str): 会社ID
        
    Returns:
        pd.DataFrame: FAQデータフレーム
    """
    try:
        # データベースからFAQデータを取得
        query = "SELECT question, answer FROM faq_data WHERE company_id = ? ORDER BY created_at"
        results = fetch_dict(query, (company_id,))
        
        if results:
            # データベースから取得したデータをDataFrameに変換
            df = pd.DataFrame(results)
        else:
            # データがない場合は空のDataFrameを作成
            df = pd.DataFrame(columns=["question", "answer"])
            st.info("FAQデータがデータベースに見つかりません。")
        
        return df
        
    except Exception as e:
        st.error(f"FAQデータの読み込み中にエラーが発生しました: {e}")
        # エラーの場合は空のDataFrameを返す
        return pd.DataFrame(columns=["question", "answer"])

    """
    FAQデータをデータベースに保存し、エンベディングを更新する
    
    Args:
        df (pd.DataFrame): 保存するFAQデータフレーム
        company_id (str): 会社ID
        
    Returns:
        bool: 保存に成功したかどうか
    """
    try:
        # 既存のFAQデータを削除
        delete_query = "DELETE FROM faq_data WHERE company_id = ?"
        execute_query(delete_query, (company_id,))
        
        # 新しいFAQデータを挿入
        insert_query = """
            INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        
        current_time = datetime.now().isoformat()
        for _, row in df.iterrows():
            execute_query(insert_query, (
                company_id, 
                row['question'], 
                row['answer'], 
                current_time, 
                current_time
            ))
        
        # エンベディングを更新
        with st.spinner("エンベディングを生成中..."):
            create_embeddings(company_id)
        
        st.success("FAQデータとエンベディングを更新しました。")
        return True
        
    except Exception as e:
        st.error(f"保存エラー: {str(e)}")
        return False

def add_faq(question, answer, company_id):
    """
    FAQを追加する
    
    Args:
        question (str): 質問
        answer (str): 回答
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    if not question or not answer:
        return False, "質問と回答を入力してください。"
    
    try:
        # 重複チェック
        check_query = "SELECT COUNT(*) as count FROM faq_data WHERE company_id = ? AND question = ?"
        result = fetch_dict_one(check_query, (company_id, question))
        if result and result['count'] > 0:
            return False, "同じ質問が既に登録されています。"
        
        # 新しいFAQを追加
        insert_query = """
            INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        current_time = datetime.now().isoformat()
        execute_query(insert_query, (company_id, question, answer, current_time, current_time))
        
        # エンベディングを更新
        with st.spinner("エンベディングを生成中..."):
            create_embeddings(company_id)
        
        return True, "FAQを追加しました。"
        
    except Exception as e:
        st.error(f"FAQ追加エラー: {str(e)}")
        return False, "FAQの追加に失敗しました。"

def update_faq(index, question, answer, company_id):
    """
    指定されたインデックスのFAQを更新する
    
    Args:
        index (int): 更新するFAQのインデックス（表示順序）
        question (str): 新しい質問
        answer (str): 新しい回答
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    if not question or not answer:
        return False, "質問と回答を入力してください。"
    
    try:
        # 指定されたインデックスのFAQ IDを取得
        query = "SELECT id FROM faq_data WHERE company_id = ? ORDER BY created_at LIMIT 1 OFFSET ?"
        result = fetch_dict_one(query, (company_id, index))
        
        if not result:
            return False, "無効なインデックスです。"
        
        faq_id = result['id']
        
        # FAQを更新
        update_query = """
            UPDATE faq_data 
            SET question = ?, answer = ?, updated_at = ?
            WHERE id = ?
        """
        current_time = datetime.now().isoformat()
        execute_query(update_query, (question, answer, current_time, faq_id))
        
        # エンベディングを更新
        with st.spinner("エンベディングを生成中..."):
            create_embeddings(company_id)
        
        return True, "FAQを更新しました。"
        
    except Exception as e:
        st.error(f"FAQ更新エラー: {str(e)}")
        return False, "FAQの更新に失敗しました。"

def delete_faq(index, company_id):
    """
    指定されたインデックスのFAQを削除する
    
    Args:
        index (int): 削除するFAQのインデックス（表示順序）
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    try:
        # 指定されたインデックスのFAQ IDを取得
        query = "SELECT id FROM faq_data WHERE company_id = ? ORDER BY created_at LIMIT 1 OFFSET ?"
        result = fetch_dict_one(query, (company_id, index))
        
        if not result:
            return False, "無効なインデックスです。"
        
        faq_id = result['id']
        
        # FAQを削除（外部キー制約により関連するエンベディングも自動削除される）
        delete_query = "DELETE FROM faq_data WHERE id = ?"
        execute_query(delete_query, (faq_id,))
        
        # エンベディングを更新
        with st.spinner("エンベディングを生成中..."):
            create_embeddings(company_id)
        
        return True, "FAQを削除しました。"
        
    except Exception as e:
        st.error(f"FAQ削除エラー: {str(e)}")
        return False, "FAQの削除に失敗しました。"

def import_faq_from_csv(uploaded_file, company_id):
    """
    アップロードされたCSVファイルからFAQをインポートする
    
    Args:
        uploaded_file: アップロードされたCSVファイル
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    try:
        # アップロードされたファイルを読み込む
        imported_df = pd.read_csv(uploaded_file)
        
        # 必要なカラムがあるか確認
        if "question" not in imported_df.columns or "answer" not in imported_df.columns:
            return False, "CSVファイルには 'question' と 'answer' の列が必要です。"
        
        # 必要な列だけ取得
        imported_df = imported_df[["question", "answer"]].dropna()
        
        # 既存の質問を取得（重複チェック用）
        existing_questions_query = "SELECT question FROM faq_data WHERE company_id = ?"
        existing_questions = fetch_dict(existing_questions_query, (company_id,))
        existing_question_set = {row['question'] for row in existing_questions}
        
        # 新しいエントリのみを抽出
        new_entries = []
        duplicate_count = 0
        
        for _, row in imported_df.iterrows():
            question = row['question']
            answer = row['answer']
            
            if question in existing_question_set:
                duplicate_count += 1
            else:
                new_entries.append((question, answer))
                existing_question_set.add(question)  # 同一ファイル内の重複も防ぐ
        
        # 新しいエントリをデータベースに追加
        if new_entries:
            insert_query = """
                INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """
            current_time = datetime.now().isoformat()
            
            for question, answer in new_entries:
                execute_query(insert_query, (company_id, question, answer, current_time, current_time))
            
            # エンベディングを更新
            with st.spinner("エンベディングを生成中..."):
                create_embeddings(company_id)
        
        # 結果メッセージを作成
        message = f"{len(new_entries)}件のFAQを追加しました。"
        if duplicate_count > 0:
            message += f" {duplicate_count}件の重複エントリはスキップされました。"
        
        return True, message
        
    except Exception as e:
        return False, f"インポート中にエラーが発生しました: {str(e)}"

def export_faq_to_csv(company_id):
    """
    FAQデータをデータベースから取得してCSVファイルとしてエクスポートする
    
    Args:
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, ファイルパスまたはエラーメッセージ)
    """
    try:
        # データベースからFAQデータを読み込む
        df = load_faq_data(company_id)
        
        if df.empty:
            return False, "エクスポートするFAQデータがありません"
        
        # 会社のデータディレクトリを取得
        company_dir = UnifiedConfig.get_data_path(company_id)
        
        # ファイル名を生成（タイムスタンプ付き）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"faq_export_{timestamp}.csv"
        export_path = os.path.join(company_dir, export_filename)
        
        # CSVとしてエクスポート
        df.to_csv(export_path, index=False, encoding='utf-8-sig')
        
        # ファイルが正常に作成されたか確認
        if os.path.exists(export_path) and os.path.getsize(export_path) > 0:
            return True, export_path
        else:
            return False, "ファイルの作成に失敗しました"
            
    except Exception as e:
        return False, f"エクスポート中にエラーが発生しました: {str(e)}"

def faq_management_page():
    """
    FAQ管理ページのUIを表示する
    """
    st.title("FAQ管理")
    
    # 現在の会社IDを取得
    company_id = get_current_company_id()
    if not company_id:
        st.error("会社情報が見つかりません。ログインしてください。")
        return
    
    # タブを作成
    tab1, tab2, tab3 = st.tabs(["FAQ一覧・編集", "FAQ追加", "一括管理"])
    
    # FAQ一覧タブ
    with tab1:
        st.subheader("FAQ一覧・編集")
        
        # データの読み込み
        df = load_faq_data(company_id)
        
        if len(df) == 0:
            st.info("FAQデータがありません。")
        else:
            # 各FAQを表示
            for i, row in df.iterrows():
                with st.expander(f"Q: {row['question']}"):
                    st.write(f"A: {row['answer']}")
                    
                    # 編集フォーム
                    with st.form(key=f"edit_form_{i}"):
                        st.subheader("FAQ編集")
                        new_question = st.text_area("質問", row["question"], key=f"q_{i}")
                        new_answer = st.text_area("回答", row["answer"], key=f"a_{i}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            submit = st.form_submit_button("更新")
                        with col2:
                            delete = st.form_submit_button("削除", type="primary")
                        
                        if submit:
                            success, message = update_faq(i, new_question, new_answer, company_id)
                            if success:
                                st.success(message)
                                time.sleep(1)  # 成功メッセージを表示する時間を確保
                                st.rerun()
                            else:
                                st.error(message)
                        
                        if delete:
                            success, message = delete_faq(i, company_id)
                            if success:
                                st.success(message)
                                time.sleep(1)  # 成功メッセージを表示する時間を確保
                                st.rerun()
                            else:
                                st.error(message)
    
    # FAQ追加タブ
    with tab2:
        st.subheader("新しいFAQを追加")
        
        with st.form(key="add_faq_form"):
            new_question = st.text_area("質問")
            new_answer = st.text_area("回答")
            submit = st.form_submit_button("追加")
            
            if submit:
                success, message = add_faq(new_question, new_answer, company_id)
                if success:
                    st.success(message)
                    time.sleep(1)  # 成功メッセージを表示する時間を確保
                    # フォームをクリア
                    st.rerun()
                else:
                    st.error(message)
    
    # 一括管理タブ
    with tab3:
        st.subheader("一括管理")
        
        # インポート
        st.write("#### FAQをCSVからインポート")
        uploaded_file = st.file_uploader("CSVファイルをアップロード", type=["csv"])
        
        if uploaded_file is not None:
            if st.button("インポート実行"):
                success, message = import_faq_from_csv(uploaded_file, company_id)
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        st.write("---")
        
        # エクスポート
        st.write("#### FAQをCSVにエクスポート")
        if st.button("エクスポート実行"):
            success, result = export_faq_to_csv(company_id)
            if success:
                export_path = result
                st.success(f"FAQデータをエクスポートしました")
                
                # ダウンロードリンクを提供
                try:
                    with open(export_path, "rb") as file:
                        st.download_button(
                            label="エクスポートしたCSVをダウンロード",
                            data=file,
                            file_name=os.path.basename(export_path),
                            mime="text/csv"
                        )
                except Exception as e:
                    st.error(f"ダウンロード準備中にエラーが発生しました: {str(e)}")
            else:
                st.error(f"エクスポートに失敗しました: {result}")
        
        st.write("---")
        
        # エンベディング再生成
        st.write("#### エンベディングを再生成")
        st.write("FAQデータのエンベディングを手動で再生成します。")
        
        if st.button("エンベディング再生成"):
            try:
                with st.spinner("エンベディングを生成中..."):
                    create_embeddings(company_id)
                st.success("エンベディングを再生成しました。")
            except Exception as e:
                st.error(f"エンベディングの再生成に失敗しました: {str(e)}")

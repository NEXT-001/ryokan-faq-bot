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
from config.settings import get_data_path

def load_faq_data(company_id):
    """
    指定された会社のFAQデータを読み込む
    
    Args:
        company_id (str): 会社ID
        
    Returns:
        pd.DataFrame: FAQデータフレーム
    """
    # 会社のデータディレクトリを取得
    company_dir = os.path.join(get_data_path(), "companies", company_id)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
    
    # CSVファイルのパス
    csv_path = os.path.join(company_dir, "faq.csv")
    
    # CSVファイルが存在するか確認
    if not os.path.exists(csv_path):
        # サンプルデータを作成
        sample_data = {
            "question": [
                "サンプル質問1",
                "サンプル質問2",
                "サンプル質問3"
            ],
            "answer": [
                "サンプル回答1",
                "サンプル回答2",
                "サンプル回答3"
            ]
        }
        df = pd.DataFrame(sample_data)
        df.to_csv(csv_path, index=False)
        st.success("サンプルFAQデータを作成しました。")
    else:
        # 既存のCSVファイルを読み込む
        df = pd.read_csv(csv_path)
    
    return df

def save_faq_data(df, company_id):
    """
    FAQデータをCSVファイルに保存し、エンベディングを更新する
    
    Args:
        df (pd.DataFrame): 保存するFAQデータフレーム
        company_id (str): 会社ID
        
    Returns:
        bool: 保存に成功したかどうか
    """
    # 会社のデータディレクトリを取得
    company_dir = os.path.join(get_data_path(), "companies", company_id)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
    
    # CSVファイルのパス
    csv_path = os.path.join(company_dir, "faq.csv")
    
    try:
        # CSVに保存
        df.to_csv(csv_path, index=False)
        
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
    
    # 既存のデータを読み込む
    df = load_faq_data(company_id)
    
    # 重複チェック
    if question in df["question"].values:
        return False, "同じ質問が既に登録されています。"
    
    # 新しい行を追加
    new_row = pd.DataFrame({"question": [question], "answer": [answer]})
    df = pd.concat([df, new_row], ignore_index=True)
    
    # 保存
    if save_faq_data(df, company_id):
        return True, "FAQを追加しました。"
    else:
        return False, "FAQの追加に失敗しました。"

def update_faq(index, question, answer, company_id):
    """
    指定されたインデックスのFAQを更新する
    
    Args:
        index (int): 更新するFAQのインデックス
        question (str): 新しい質問
        answer (str): 新しい回答
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    if not question or not answer:
        return False, "質問と回答を入力してください。"
    
    # 既存のデータを読み込む
    df = load_faq_data(company_id)
    
    # インデックスの検証
    if index < 0 or index >= len(df):
        return False, "無効なインデックスです。"
    
    # 更新
    df.at[index, "question"] = question
    df.at[index, "answer"] = answer
    
    # 保存
    if save_faq_data(df, company_id):
        return True, "FAQを更新しました。"
    else:
        return False, "FAQの更新に失敗しました。"

def delete_faq(index, company_id):
    """
    指定されたインデックスのFAQを削除する
    
    Args:
        index (int): 削除するFAQのインデックス
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    # 既存のデータを読み込む
    df = load_faq_data(company_id)
    
    # インデックスの検証
    if index < 0 or index >= len(df):
        return False, "無効なインデックスです。"
    
    # 削除
    df = df.drop(index)
    df = df.reset_index(drop=True)  # インデックスを振り直す
    
    # 保存
    if save_faq_data(df, company_id):
        return True, "FAQを削除しました。"
    else:
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
        
        # 既存のデータを読み込む
        current_df = load_faq_data(company_id)
        
        # 重複の確認と処理
        imported_df = imported_df[["question", "answer"]]  # 必要な列だけ取得
        
        # 重複する質問を検出
        duplicates = imported_df["question"].isin(current_df["question"])
        new_entries = imported_df[~duplicates]
        duplicate_count = duplicates.sum()
        
        # 新しいエントリを追加
        combined_df = pd.concat([current_df, new_entries], ignore_index=True)
        
        # 保存
        if save_faq_data(combined_df, company_id):
            message = f"{len(new_entries)}件のFAQを追加しました。"
            if duplicate_count > 0:
                message += f" {duplicate_count}件の重複エントリはスキップされました。"
            return True, message
        else:
            return False, "FAQのインポートに失敗しました。"
        
    except Exception as e:
        return False, f"インポート中にエラーが発生しました: {str(e)}"

def export_faq_to_csv(company_id):
    """
    FAQデータをCSVファイルとしてエクスポートする
    
    Args:
        company_id (str): 会社ID
        
    Returns:
        str: エクスポートしたファイルのパス
    """
    # 既存のデータを読み込む
    df = load_faq_data(company_id)
    
    # 会社のデータディレクトリを取得
    company_dir = os.path.join(get_data_path(), "companies", company_id)
    
    # ファイル名を生成（タイムスタンプ付き）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"faq_export_{timestamp}.csv"
    export_path = os.path.join(company_dir, export_filename)
    
    # CSVとしてエクスポート
    df.to_csv(export_path, index=False)
    
    return export_path

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
            export_path = export_faq_to_csv(company_id)
            st.success(f"FAQデータをエクスポートしました")
            
            # ダウンロードリンクを提供
            with open(export_path, "rb") as file:
                st.download_button(
                    label="エクスポートしたCSVをダウンロード",
                    data=file,
                    file_name=os.path.basename(export_path),
                    mime="text/csv"
                )
        
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
                
def faq_preview_page(company_id=None):
    """
    FAQ検索プレビュー
    
    Args:
        company_id (str, optional): 会社ID
    """
    st.header("FAQ検索テスト")
    
    if not company_id:
        st.error("会社情報が見つかりません。")
        return
    
    # 会社のデータディレクトリを取得
    company_dir = os.path.join(get_data_path(), "companies", company_id)
    faq_path = os.path.join(company_dir, "faq_with_embeddings.pkl")
    
    if not os.path.exists(faq_path):
        st.warning("エンベディングファイルが見つかりません。先にエンベディングを生成してください。")
        
        if st.button("エンベディングを生成"):
            with st.spinner("エンベディングを生成中..."):
                create_embeddings(company_id)
            st.success("エンベディングを生成しました。")
            st.rerun()
        return
    
    # 検索テスト
    st.write("FAQ検索機能をテストします。実際のユーザー体験を確認できます。")
    
    test_query = st.text_input("テスト質問を入力してください")
    
    if test_query:
        from services.chat_service import get_response
        
        with st.spinner("回答を検索中..."):
            answer, _, _ = get_response(test_query, company_id)
            
            st.write("#### 検索結果")
            st.info(answer)
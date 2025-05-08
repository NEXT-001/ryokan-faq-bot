"""
FAQ管理機能 - 管理者がFAQを追加・編集・削除するための機能
admin_faq_management.py
"""
import os
import pandas as pd
import streamlit as st
from datetime import datetime
from services.embedding_service import create_embeddings, get_embedding

# CSVファイルのパス
FAQ_CSV_PATH = "data/faq.csv"
FAQ_WITH_EMBEDDINGS_PATH = "data/faq_with_embeddings.pkl"

def load_faq_data():
    """CSVファイルからFAQデータを読み込む"""
    # データディレクトリの確認
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # CSVファイルが存在するか確認
    if not os.path.exists(FAQ_CSV_PATH):
        # サンプルデータを作成
        sample_data = {
            "question": [
                "チェックインの時間は何時ですか？",
                "駐車場はありますか？",
                "Wi-Fiは利用できますか？",
                "食事のアレルギー対応はできますか？",
                "部屋のタイプはどのようなものがありますか？"
            ],
            "answer": [
                "チェックインは15:00〜19:00です。事前にご連絡いただければ、遅いチェックインにも対応可能です。",
                "はい、無料の駐車場を提供しています。大型車の場合は事前にご連絡ください。",
                "全客室でWi-Fiを無料でご利用いただけます。接続情報はチェックイン時にお渡しします。",
                "はい、アレルギーがある場合は予約時にお知らせください。可能な限り対応いたします。",
                "和室と洋室の両方をご用意しています。和室は8畳・10畳・12畳、洋室はシングル・ツイン・ダブルがございます。"
            ]
        }
        df = pd.DataFrame(sample_data)
        df.to_csv(FAQ_CSV_PATH, index=False)
        st.success("サンプルFAQデータを作成しました。")
    else:
        # 既存のCSVファイルを読み込む
        df = pd.read_csv(FAQ_CSV_PATH)
    
    return df

def save_faq_data(df):
    """FAQデータをCSVファイルに保存する"""
    # データディレクトリの確認
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # CSVに保存
    df.to_csv(FAQ_CSV_PATH, index=False)
    
    # エンベディングを更新
    try:
        create_embeddings()
        st.success("FAQデータとエンベディングを更新しました。")
    except Exception as e:
        st.error(f"エンベディングの更新に失敗しました: {str(e)}")
        st.info("FAQデータは保存されましたが、エンベディングの更新に失敗したため、検索精度に影響が出る可能性があります。")

def add_faq(question, answer):
    """FAQを追加する"""
    if not question or not answer:
        return False, "質問と回答を入力してください。"
    
    # 既存のデータを読み込む
    df = load_faq_data()
    
    # 重複チェック
    if question in df["question"].values:
        return False, "同じ質問が既に登録されています。"
    
    # 新しい行を追加
    new_row = pd.DataFrame({"question": [question], "answer": [answer]})
    df = pd.concat([df, new_row], ignore_index=True)
    
    # 保存
    save_faq_data(df)
    return True, "FAQを追加しました。"

def update_faq(index, question, answer):
    """指定されたインデックスのFAQを更新する"""
    if not question or not answer:
        return False, "質問と回答を入力してください。"
    
    # 既存のデータを読み込む
    df = load_faq_data()
    
    # インデックスの検証
    if index < 0 or index >= len(df):
        return False, "無効なインデックスです。"
    
    # 更新
    df.at[index, "question"] = question
    df.at[index, "answer"] = answer
    
    # 保存
    save_faq_data(df)
    return True, "FAQを更新しました。"

def delete_faq(index):
    """指定されたインデックスのFAQを削除する"""
    # 既存のデータを読み込む
    df = load_faq_data()
    
    # インデックスの検証
    if index < 0 or index >= len(df):
        return False, "無効なインデックスです。"
    
    # 削除
    df = df.drop(index)
    df = df.reset_index(drop=True)  # インデックスを振り直す
    
    # 保存
    save_faq_data(df)
    return True, "FAQを削除しました。"

def import_faq_from_csv(uploaded_file):
    """アップロードされたCSVファイルからFAQをインポートする"""
    try:
        # アップロードされたファイルを読み込む
        imported_df = pd.read_csv(uploaded_file)
        
        # 必要なカラムがあるか確認
        if "question" not in imported_df.columns or "answer" not in imported_df.columns:
            return False, "CSVファイルには 'question' と 'answer' の列が必要です。"
        
        # 既存のデータを読み込む
        current_df = load_faq_data()
        
        # 重複の確認と処理
        imported_df = imported_df[["question", "answer"]]  # 必要な列だけ取得
        
        # 重複する質問を検出
        duplicates = imported_df["question"].isin(current_df["question"])
        new_entries = imported_df[~duplicates]
        duplicate_count = duplicates.sum()
        
        # 新しいエントリを追加
        combined_df = pd.concat([current_df, new_entries], ignore_index=True)
        
        # 保存
        save_faq_data(combined_df)
        
        message = f"{len(new_entries)}件のFAQを追加しました。"
        if duplicate_count > 0:
            message += f" {duplicate_count}件の重複エントリはスキップされました。"
        
        return True, message
        
    except Exception as e:
        return False, f"インポート中にエラーが発生しました: {str(e)}"

def export_faq_to_csv():
    """FAQデータをCSVファイルとしてエクスポートする"""
    # 既存のデータを読み込む
    df = load_faq_data()
    
    # ファイル名を生成（タイムスタンプ付き）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"faq_export_{timestamp}.csv"
    
    # CSVとしてエクスポート
    df.to_csv(f"data/{export_filename}", index=False)
    
    return export_filename

def faq_management_page():
    """FAQ管理ページのUIを表示する"""
    st.title("FAQ管理")
    
    # タブを作成
    tab1, tab2, tab3, tab4 = st.tabs(["FAQ一覧", "FAQ追加", "FAQ一括管理", "検索テスト"])
    
    # FAQ一覧タブ
    with tab1:
        st.subheader("FAQ一覧")
        
        # データの読み込み
        df = load_faq_data()
        
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
                            success, message = update_faq(i, new_question, new_answer)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                        
                        if delete:
                            success, message = delete_faq(i)
                            if success:
                                st.success(message)
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
                success, message = add_faq(new_question, new_answer)
                if success:
                    st.success(message)
                    # フォームをクリア
                    st.rerun()
                else:
                    st.error(message)
    
    # FAQ一括管理タブ
    with tab3:
        st.subheader("FAQ一括管理")
        
        # インポート
        st.write("#### FAQをCSVからインポート")
        uploaded_file = st.file_uploader("CSVファイルをアップロード", type=["csv"])
        
        if uploaded_file is not None:
            if st.button("インポート実行"):
                success, message = import_faq_from_csv(uploaded_file)
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        st.write("---")
        
        # エクスポート
        st.write("#### FAQをCSVにエクスポート")
        if st.button("エクスポート実行"):
            export_filename = export_faq_to_csv()
            st.success(f"FAQデータをエクスポートしました: {export_filename}")
            
            # ダウンロードリンクを提供
            with open(f"data/{export_filename}", "rb") as file:
                st.download_button(
                    label="エクスポートしたCSVをダウンロード",
                    data=file,
                    file_name=export_filename,
                    mime="text/csv"
                )
        
        st.write("---")
        
        # エンベディング再生成
        st.write("#### エンベディングを再生成")
        st.write("FAQデータのエンベディングを手動で再生成します。")
        
        if st.button("エンベディング再生成"):
            try:
                create_embeddings()
                st.success("エンベディングを再生成しました。")
            except Exception as e:
                st.error(f"エンベディングの再生成に失敗しました: {str(e)}")
    
    # 検索テストタブ
    with tab4:
        st.subheader("検索テスト")
        st.write("FAQ検索機能をテストします。実際のユーザー体験を確認できます。")
        
        test_query = st.text_input("テスト質問を入力してください")
        
        if test_query:
            if os.path.exists(FAQ_WITH_EMBEDDINGS_PATH):
                from services.chat_service import get_response
                answer, _, _ = get_response(test_query)
                
                st.write("#### 検索結果")
                st.info(answer)
            else:
                st.warning("エンベディングファイルが見つかりません。先にエンベディングを生成してください。")
                
                if st.button("エンベディングを生成"):
                    try:
                        create_embeddings()
                        st.success("エンベディングを生成しました。もう一度検索をお試しください。")
                    except Exception as e:
                        st.error(f"エンベディングの生成に失敗しました: {str(e)}")

if __name__ == "__main__":
    faq_management_page()
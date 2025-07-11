# history_service.py
import streamlit as st
import pandas as pd
from datetime import datetime
import os
from config.settings import get_data_path

def log_interaction(question, answer, input_tokens, output_tokens, company_id=None, user_info=""):
    """
    ユーザーとの対話をCSVファイルに記録する
    
    Args:
        question (str): ユーザーからの質問
        answer (str): システムからの回答
        input_tokens (int): 入力トークン数
        output_tokens (int): 出力トークン数
        company_id (str, optional): 会社ID（指定がない場合はデモ企業）
        user_info (str, optional): ユーザー情報（例: 部屋番号）
    """
    # 会社IDが指定されていない場合はデモ企業を使用
    if not company_id:
        company_id = "demo-company"
    
    # 会社のデータディレクトリを取得
    company_dir = os.path.join(get_data_path(), "companies", company_id)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
    
    # 履歴ファイルのパス
    history_file = os.path.join(company_dir, "history.csv")
    
    # 改行を含む可能性のあるテキストから改行を削除
    def sanitize_text(text):
        if isinstance(text, str):
            # 改行をスペースに置換
            return text.replace('\n', ' ').replace('\r', ' ')
        return text
    
    # 記録用のデータフレームを作成
    df = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_info": sanitize_text(user_info),
        "question": sanitize_text(question),
        "answer": sanitize_text(answer),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }])
    
    # CSVファイルに保存
    file_exists = os.path.exists(history_file)
    
    try:
        # 改行文字の削除に加えて、CSVライブラリを使って適切に引用符処理
        if not file_exists:
            df.to_csv(history_file, index=False, quoting=1)  # quoting=1 は csv.QUOTE_ALL と同等
        else:
            df.to_csv(history_file, mode='a', header=False, index=False, quoting=1)
        
        print(f"対話を記録しました: {history_file}")
    except Exception as e:
        print(f"対話記録エラー: {e}")

def show_history(company_id=None):
    """
    保存された対話履歴を表示する
    
    Args:
        company_id (str, optional): 会社ID（指定がない場合はデモ企業）
    """
    # 会社IDが指定されていない場合はデモ企業を使用
    if not company_id:
        company_id = "demo-company"
    
    # 会社の履歴ファイルのパス
    history_file = os.path.join(get_data_path(), "companies", company_id, "history.csv")
    
    if os.path.exists(history_file):
        try:
            # 履歴データを読み込む
            df = pd.read_csv(history_file)
            
            if len(df) > 0:
                st.subheader("FAQ利用履歴")
                
                # 履歴の表示（最新の20件まで）
                for i, row in df.tail(20).iterrows():
                    st.write(f"**日時:** {row['timestamp']}")
                    
                    # ユーザー情報があれば表示
                    if 'user_info' in row and pd.notna(row['user_info']) and row['user_info']:
                        st.write(f"**ユーザー情報:** {row['user_info']}")
                    
                    st.write(f"**質問:** {row['question']}")
                    st.write(f"**回答:** {row['answer']}")
                    
                    # トークン情報が存在する場合のみ表示
                    # if 'input_tokens' in row and 'output_tokens' in row:
                    #     st.write(f"**トークン:** 入力 {row['input_tokens']}、出力 {row['output_tokens']}")
                    
                    st.markdown("---")
            else:
                st.info("履歴は空です")
        except Exception as e:
            st.error(f"履歴の読み込みエラー: {str(e)}")
    else:
        st.info("まだ履歴がありません")
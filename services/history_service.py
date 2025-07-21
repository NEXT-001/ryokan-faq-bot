# history_service.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from config.unified_config import UnifiedConfig
from core.database import (
    save_search_history_to_db, 
    get_search_history_from_db, 
    cleanup_old_search_history,
    count_search_history
)

def cleanup_old_history(company_id=None):
    """
    1週間以上古い履歴データをデータベースから削除する
    
    Args:
        company_id (str, optional): 会社ID（指定がない場合はデモ企業）
    """
    # 会社IDが指定されていない場合はデモ企業を使用
    if not company_id:
        company_id = "demo-company"
    
    try:
        # データベースから古い履歴を削除
        success = cleanup_old_search_history(company_id, days=7)
        
        if success:
            print(f"[HISTORY_SERVICE] 古い履歴データをクリーンアップしました: {company_id}")
        else:
            print(f"[HISTORY_SERVICE] 履歴クリーンアップに失敗しました: {company_id}")
            
    except Exception as e:
        print(f"[HISTORY_SERVICE] 履歴クリーンアップエラー: {e}")

def log_interaction(question, answer, input_tokens, output_tokens, company_id=None, user_info=""):
    """
    ユーザーとの対話をデータベースに記録する
    
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
    
    # 改行を含む可能性のあるテキストから改行を削除
    def sanitize_text(text):
        if isinstance(text, str):
            # 改行をスペースに置換
            return text.replace('\n', ' ').replace('\r', ' ')
        return text
    
    try:
        # データベースに保存
        success = save_search_history_to_db(
            company_id=company_id,
            question=sanitize_text(question),
            answer=sanitize_text(answer),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            user_info=sanitize_text(user_info)
        )
        
        if success:
            print(f"[HISTORY_SERVICE] 対話を記録しました: {company_id}")
            
            # 新しい記録の後に古い履歴をクリーンアップ
            cleanup_old_history(company_id)
        else:
            print(f"[HISTORY_SERVICE] 対話記録に失敗しました: {company_id}")
        
    except Exception as e:
        print(f"[HISTORY_SERVICE] 対話記録エラー: {e}")

def show_history(company_id=None):
    """
    保存された対話履歴をデータベースから表示する
    
    Args:
        company_id (str, optional): 会社ID（指定がない場合はデモ企業）
    """
    # 会社IDが指定されていない場合はデモ企業を使用
    if not company_id:
        company_id = "demo-company"
    
    try:
        # データベースから履歴データを取得（最新20件）
        history_data = get_search_history_from_db(company_id, limit=20)
        
        if len(history_data) > 0:
            st.subheader("FAQ利用履歴")
            
            # 履歴件数を表示
            total_count = count_search_history(company_id)
            st.write(f"総履歴件数: {total_count}件（最新20件を表示）")
            
            # 履歴の表示
            for row in history_data:
                # 日時をフォーマット
                created_at = row['created_at']
                if 'T' in created_at:
                    # ISO形式の場合は読みやすい形式に変換
                    dt = datetime.fromisoformat(created_at)
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    formatted_time = created_at
                
                st.write(f"**日時:** {formatted_time}")
                
                # ユーザー情報があれば表示
                if row.get('user_info') and row['user_info'].strip():
                    st.write(f"**ユーザー情報:** {row['user_info']}")
                
                st.write(f"**質問:** {row['question']}")
                st.write(f"**回答:** {row['answer']}")
                
                # トークン情報が存在する場合のみ表示
                # if row.get('input_tokens') is not None and row.get('output_tokens') is not None:
                #     st.write(f"**トークン:** 入力 {row['input_tokens']}、出力 {row['output_tokens']}")
                
                st.markdown("---")
        else:
            st.info("履歴は空です")
            
    except Exception as e:
        st.error(f"履歴の読み込みエラー: {str(e)}")
        print(f"[HISTORY_SERVICE] 履歴表示エラー: {e}")

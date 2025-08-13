"""
FAQデータとエンベディングのSQLite移行サービス
services/faq_migration.py
"""
import os
import pandas as pd
import numpy as np
import pickle
import sqlite3
from datetime import datetime
from core.database import (
    get_db_connection, execute_query, fetch_dict, fetch_dict_one,
    initialize_database, table_exists, DB_TYPE
)
from config.unified_config import UnifiedConfig

def get_param_format():
    """データベースタイプに応じたパラメータフォーマットを取得"""
    return "%s" if DB_TYPE == "postgresql" else "?"

def create_faq_tables():
    """FAQとエンベディング用のテーブルを作成"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # データベース別のSQL文を準備
            if DB_TYPE == "postgresql":
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS faq_embeddings (
                        id SERIAL PRIMARY KEY,
                        faq_id INTEGER NOT NULL,
                        embedding_vector BYTEA NOT NULL,
                        vector_model TEXT DEFAULT 'voyage-3',
                        embedding_dim INTEGER DEFAULT 1024,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (faq_id) REFERENCES faq_data (id) ON DELETE CASCADE
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS faq_embeddings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        faq_id INTEGER NOT NULL,
                        embedding_vector BLOB NOT NULL,
                        vector_model TEXT DEFAULT 'voyage-3',
                        embedding_dim INTEGER DEFAULT 1024,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (faq_id) REFERENCES faq_data (id) ON DELETE CASCADE
                    )
                """)
            
            # インデックス作成
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_faq_embeddings_faq_id ON faq_embeddings(faq_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_faq_embeddings_model ON faq_embeddings(vector_model)")
            
            conn.commit()
            print("[MIGRATION] FAQ関連テーブル作成完了")
            return True
            
    except Exception as e:
        print(f"[MIGRATION] テーブル作成エラー: {e}")
        return False

def serialize_embedding(embedding_vector):
    """エンベディングベクトルをバイナリにシリアライズ"""
    try:
        if isinstance(embedding_vector, list):
            embedding_vector = np.array(embedding_vector, dtype=np.float32)
        elif isinstance(embedding_vector, np.ndarray):
            embedding_vector = embedding_vector.astype(np.float32)
        
        return embedding_vector.tobytes()
    except Exception as e:
        print(f"[MIGRATION] エンベディングシリアライズエラー: {e}")
        return None

def deserialize_embedding(binary_data):
    """バイナリデータからエンベディングベクトルをデシリアライズ"""
    try:
        return np.frombuffer(binary_data, dtype=np.float32).tolist()
    except Exception as e:
        print(f"[MIGRATION] エンベディングデシリアライズエラー: {e}")
        return None

def migrate_company_faq_data(company_id, show_progress=False):
    """指定された会社のFAQデータをDBに移行（廃止：フォルダ管理から移行済み）"""
    print(f"[MIGRATION] 会社 {company_id}: フォルダベースのファイル管理は廃止されました。データベース管理に移行済みです。")
    return True
        
        if show_progress:
            import streamlit as st
            st.info(f"📁 {company_id} のデータを移行中...")
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # データ読み込み
        if has_embeddings:
            try:
                df = pd.read_pickle(pkl_path)
                print(f"[MIGRATION] エンベディング付きデータを読み込み: {len(df)}件")
            except Exception as e:
                print(f"[MIGRATION] PKLファイル読み込みエラー: {e}")
                df = pd.read_csv(csv_path)
                has_embeddings = False
        else:
            df = pd.read_csv(csv_path)
            print(f"[MIGRATION] CSVデータを読み込み: {len(df)}件")
        
        # 必要なカラムの確認
        if 'question' not in df.columns or 'answer' not in df.columns:
            print("[MIGRATION] 必要なカラム(question, answer)が見つかりません")
            return False
        
        # 既存データの削除（再移行対応）
        param_format = get_param_format()
        execute_query(f"DELETE FROM faq_data WHERE company_id = {param_format}", (company_id,))
        print(f"[MIGRATION] 既存データを削除: {company_id}")
        
        # データ移行処理
        total_count = len(df)
        success_count = 0
        
        for i, row in df.iterrows():
            try:
                # FAQ基本データを挿入
                query = f"""
                    INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
                    VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                """
                current_time = datetime.now().isoformat()
                
                faq_cursor = get_db_connection().cursor()
                faq_cursor.execute(query, (
                    company_id,
                    row['question'],
                    row['answer'],
                    current_time,
                    current_time
                ))
                faq_id = faq_cursor.lastrowid
                faq_cursor.close()
                
                # エンベディングがある場合は保存
                if has_embeddings and 'embedding' in row and row['embedding'] is not None:
                    try:
                        serialized_embedding = serialize_embedding(row['embedding'])
                        if serialized_embedding:
                            embedding_query = f"""
                                INSERT INTO faq_embeddings 
                                (faq_id, embedding_vector, vector_model, embedding_dim, created_at, updated_at)
                                VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                            """
                            execute_query(embedding_query, (
                                faq_id,
                                serialized_embedding,
                                'voyage-3',  # デフォルトモデル
                                len(row['embedding']) if isinstance(row['embedding'], (list, np.ndarray)) else 1024,
                                current_time,
                                current_time
                            ))
                    except Exception as e:
                        print(f"[MIGRATION] エンベディング保存エラー (FAQ ID: {faq_id}): {e}")
                
                success_count += 1
                
                # 進行状況更新
                if show_progress:
                    progress = (i + 1) / total_count
                    progress_bar.progress(progress)
                    status_text.text(f"移行中: {i+1}/{total_count} 件")
                
            except Exception as e:
                print(f"[MIGRATION] FAQ移行エラー (行 {i}): {e}")
                continue
        
        # 会社のFAQ数を更新
        from core.database import update_company_faq_count_in_db
        update_company_faq_count_in_db(company_id, success_count)
        
        if show_progress:
            progress_bar.progress(1.0)
            status_text.success(f"✅ 移行完了: {success_count}/{total_count} 件")
        
        print(f"[MIGRATION] {company_id} の移行完了: {success_count}/{total_count} 件")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] 会社データ移行エラー: {e}")
        return False

def migrate_all_companies(show_progress=False):
    """全会社のFAQデータを移行（廃止：フォルダ管理から移行済み）"""
    print("[MIGRATION] フォルダベースの会社管理は廃止されました。データベース管理に移行済みです。")
    return True

def backup_original_data():
    """元のCSV/PKLファイルをバックアップ（廃止：フォルダ管理から移行済み）"""
    print("[MIGRATION] フォルダベースのファイル管理は廃止されました。データベース管理に移行済みです。")
    return True

def verify_migration(company_id):
    """移行結果を検証"""
    try:
        # DBからFAQデータを取得
        param_format = get_param_format()
        faq_query = f"SELECT COUNT(*) FROM faq_data WHERE company_id = {param_format}"
        faq_result = fetch_dict_one(faq_query, (company_id,))
        faq_count = faq_result['COUNT(*)'] if faq_result else 0
        
        # エンベディング数を取得
        embedding_query = f"""
            SELECT COUNT(*) FROM faq_embeddings fe 
            JOIN faq_data fd ON fe.faq_id = fd.id 
            WHERE fd.company_id = {param_format}
        """
        embedding_result = fetch_dict_one(embedding_query, (company_id,))
        embedding_count = embedding_result['COUNT(*)'] if embedding_result else 0
        
        # 元ファイルと比較
        company_dir = UnifiedConfig.get_data_path(company_id)
        csv_path = os.path.join(company_dir, "faq.csv")
        
        original_count = 0
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                original_count = len(df)
            except Exception as e:
                print(f"[MIGRATION] 元ファイル読み込みエラー: {e}")
        
        print(f"[MIGRATION] 検証結果 {company_id}:")
        print(f"  元ファイル: {original_count} 件")
        print(f"  DB FAQ: {faq_count} 件")
        print(f"  DB エンベディング: {embedding_count} 件")
        
        return {
            'company_id': company_id,
            'original_count': original_count,
            'faq_count': faq_count,
            'embedding_count': embedding_count,
            'migration_success': faq_count == original_count
        }
        
    except Exception as e:
        print(f"[MIGRATION] 検証エラー: {e}")
        return None

def get_faq_data_from_db(company_id):
    """DBからFAQデータを取得（エンベディング付き）"""
    try:
        param_format = get_param_format()
        query = f"""
            SELECT 
                fd.id,
                fd.question,
                fd.answer,
                fd.created_at,
                fd.updated_at,
                fe.embedding_vector,
                fe.vector_model,
                fe.embedding_dim
            FROM faq_data fd
            LEFT JOIN faq_embeddings fe ON fd.id = fe.faq_id
            WHERE fd.company_id = {param_format}
            ORDER BY fd.id
        """
        
        results = fetch_dict(query, (company_id,))
        
        # エンベディングをデシリアライズ
        for result in results:
            if result['embedding_vector']:
                result['embedding'] = deserialize_embedding(result['embedding_vector'])
            else:
                result['embedding'] = None
            # バイナリデータは除去
            del result['embedding_vector']
        
        return results
        
    except Exception as e:
        print(f"[MIGRATION] FAQ取得エラー: {e}")
        return []

def save_faq_to_db(company_id, question, answer, embedding=None):
    """新しいFAQをDBに保存"""
    try:
        # FAQ基本データを保存
        param_format = get_param_format()
        faq_query = f"""
            INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
            VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format})
        """
        current_time = datetime.now().isoformat()
        
        # PostgreSQL対応のID取得
        if DB_TYPE == "postgresql":
            # execute_queryを使ってRETURNING句で直接IDを取得
            id_query = f"""
                INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
                VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                RETURNING id
            """
            from core.database import fetch_dict_one
            result = fetch_dict_one(id_query, (company_id, question, answer, current_time, current_time))
            faq_id = result['id'] if result else None
        else:
            execute_query(faq_query, (company_id, question, answer, current_time, current_time))
            # 最後に挿入されたIDを取得
            from core.database import fetch_dict_one
            last_id_query = "SELECT last_insert_rowid() as id"
            result = fetch_dict_one(last_id_query)
            faq_id = result['id'] if result else None
        
        # エンベディングがある場合は保存
        if embedding is not None and faq_id:
            serialized_embedding = serialize_embedding(embedding)
            if serialized_embedding:
                embedding_query = f"""
                    INSERT INTO faq_embeddings 
                    (faq_id, embedding_vector, vector_model, embedding_dim, created_at, updated_at)
                    VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                """
                execute_query(embedding_query, (
                    faq_id,
                    serialized_embedding,
                    'voyage-3',
                    len(embedding) if isinstance(embedding, (list, np.ndarray)) else 1024,
                    current_time,
                    current_time
                ))
        
        # FAQ数を更新
        from core.database import update_company_faq_count_in_db
        current_count = len(get_faq_data_from_db(company_id))
        update_company_faq_count_in_db(company_id, current_count)
        
        print(f"[MIGRATION] FAQ保存完了 (ID: {faq_id}): {question[:30]}...")
        return faq_id
        
    except Exception as e:
        print(f"[MIGRATION] FAQ保存エラー: {e}")
        return None

def update_faq_in_db(faq_id, question=None, answer=None, embedding=None):
    """既存FAQを更新"""
    try:
        current_time = datetime.now().isoformat()
        
        # FAQ基本データを更新
        param_format = get_param_format()
        if question is not None or answer is not None:
            if question is not None and answer is not None:
                faq_query = f"UPDATE faq_data SET question = {param_format}, answer = {param_format}, updated_at = {param_format} WHERE id = {param_format}"
                execute_query(faq_query, (question, answer, current_time, faq_id))
            elif question is not None:
                faq_query = f"UPDATE faq_data SET question = {param_format}, updated_at = {param_format} WHERE id = {param_format}"
                execute_query(faq_query, (question, current_time, faq_id))
            else:
                faq_query = f"UPDATE faq_data SET answer = {param_format}, updated_at = {param_format} WHERE id = {param_format}"
                execute_query(faq_query, (answer, current_time, faq_id))
        
        # エンベディングを更新
        if embedding is not None:
            serialized_embedding = serialize_embedding(embedding)
            if serialized_embedding:
                # 既存エンベディングの確認
                check_query = f"SELECT id FROM faq_embeddings WHERE faq_id = {param_format}"
                existing = fetch_dict_one(check_query, (faq_id,))
                
                if existing:
                    # 更新
                    embedding_query = f"""
                        UPDATE faq_embeddings 
                        SET embedding_vector = {param_format}, embedding_dim = {param_format}, updated_at = {param_format}
                        WHERE faq_id = {param_format}
                    """
                    execute_query(embedding_query, (
                        serialized_embedding,
                        len(embedding) if isinstance(embedding, (list, np.ndarray)) else 1024,
                        current_time,
                        faq_id
                    ))
                else:
                    # 新規作成
                    embedding_query = f"""
                        INSERT INTO faq_embeddings 
                        (faq_id, embedding_vector, vector_model, embedding_dim, created_at, updated_at)
                        VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                    """
                    execute_query(embedding_query, (
                        faq_id,
                        serialized_embedding,
                        'voyage-3',
                        len(embedding) if isinstance(embedding, (list, np.ndarray)) else 1024,
                        current_time,
                        current_time
                    ))
        
        print(f"[MIGRATION] FAQ更新完了 (ID: {faq_id})")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] FAQ更新エラー: {e}")
        return False

def delete_faq_from_db(faq_id):
    """FAQをDBから削除（エンベディングも含む）"""
    try:
        # 外部キー制約により、faq_embeddingsは自動削除される
        param_format = get_param_format()
        execute_query(f"DELETE FROM faq_data WHERE id = {param_format}", (faq_id,))
        print(f"[MIGRATION] FAQ削除完了 (ID: {faq_id})")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] FAQ削除エラー: {e}")
        return False

# 初期化時にテーブル作成
def init_faq_migration():
    """FAQマイグレーション用の初期化"""
    try:
        # 基本データベースの初期化
        if not table_exists("companies"):
            initialize_database()
        
        # FAQ関連テーブルの作成
        create_faq_tables()
        
        print("[MIGRATION] FAQマイグレーション初期化完了")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] 初期化エラー: {e}")
        return False
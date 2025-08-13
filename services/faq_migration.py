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
                        vector_model VARCHAR(50) DEFAULT 'voyage-3',
                        embedding_dim INTEGER DEFAULT 1024,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (faq_id) REFERENCES faq_data(id) ON DELETE CASCADE
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS faq_data (
                        id SERIAL PRIMARY KEY,
                        company_id VARCHAR(100) NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS faq_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS faq_embeddings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        faq_id INTEGER NOT NULL,
                        embedding_vector BLOB NOT NULL,
                        vector_model TEXT DEFAULT 'voyage-3',
                        embedding_dim INTEGER DEFAULT 1024,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (faq_id) REFERENCES faq_data(id) ON DELETE CASCADE
                    )
                """)
            
            conn.commit()
            print("[MIGRATION] FAQテーブル作成完了")
            return True
            
    except Exception as e:
        print(f"[MIGRATION] テーブル作成エラー: {e}")
        return False

def serialize_embedding(embedding_data):
    """エンベディングをシリアライズ"""
    try:
        if isinstance(embedding_data, np.ndarray):
            return pickle.dumps(embedding_data.tolist())
        elif isinstance(embedding_data, list):
            return pickle.dumps(embedding_data)
        else:
            print(f"[MIGRATION] 未対応のエンベディング形式: {type(embedding_data)}")
            return None
    except Exception as e:
        print(f"[MIGRATION] エンベディングシリアライズエラー: {e}")
        return None

def deserialize_embedding(serialized_data):
    """シリアライズされたエンベディングを復元"""
    try:
        if isinstance(serialized_data, bytes):
            # まずpickleで試行
            try:
                return pickle.loads(serialized_data)
            except:
                # pickleで失敗した場合、numpy配列として直接解釈を試行
                try:
                    import numpy as np
                    # float32の配列として解釈（1024次元と仮定）
                    if len(serialized_data) == 1024 * 4:  # float32 = 4bytes
                        arr = np.frombuffer(serialized_data, dtype=np.float32)
                        return arr.tolist()
                    # float64の配列として解釈
                    elif len(serialized_data) == 1024 * 8:  # float64 = 8bytes
                        arr = np.frombuffer(serialized_data, dtype=np.float64)
                        return arr.tolist()
                    else:
                        print(f"[MIGRATION] 不明なバイナリ形式: サイズ {len(serialized_data)} bytes")
                        return None
                except Exception as np_error:
                    print(f"[MIGRATION] numpy解釈エラー: {np_error}")
                    return None
                    
        elif isinstance(serialized_data, str):
            # Base64でエンコードされた場合を想定
            import base64
            try:
                decoded = base64.b64decode(serialized_data)
                return pickle.loads(decoded)
            except:
                # JSONとして解釈を試行
                import json
                try:
                    return json.loads(serialized_data)
                except:
                    print(f"[MIGRATION] 文字列データの解釈に失敗: {serialized_data[:100]}...")
                    return None
        else:
            return serialized_data
            
    except Exception as e:
        print(f"[MIGRATION] エンベディングデシリアライズエラー: {e}")
        print(f"[MIGRATION] データ型: {type(serialized_data)}, サイズ: {len(serialized_data) if hasattr(serialized_data, '__len__') else 'Unknown'}")
        if isinstance(serialized_data, bytes) and len(serialized_data) > 0:
            print(f"[MIGRATION] 最初の16バイト: {serialized_data[:16].hex()}")
        return None

def migrate_company_faq_data(company_id, show_progress=False):
    """指定された会社のFAQデータをDBに移行（廃止：フォルダ管理から移行済み）"""
    print(f"[MIGRATION] 会社 {company_id}: フォルダベースのファイル管理は廃止されました。データベース管理に移行済みです。")
    return True

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
        
        print(f"[VERIFICATION] {company_id}: FAQ {faq_count}件, エンベディング {embedding_count}件")
        
        return {
            'company_id': company_id,
            'faq_count': faq_count,
            'embedding_count': embedding_count,
            'success': faq_count > 0
        }
        
    except Exception as e:
        print(f"[VERIFICATION] 検証エラー: {e}")
        return {
            'company_id': company_id,
            'faq_count': 0,
            'embedding_count': 0,
            'success': False,
            'error': str(e)
        }

def init_faq_migration():
    """FAQ移行システムの初期化"""
    try:
        # データベースの初期化
        initialize_database()
        
        # FAQテーブルの作成
        create_faq_tables()
        
        print("[MIGRATION] FAQ移行システム初期化完了")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] 初期化エラー: {e}")
        return False

def get_faq_data_from_db(company_id):
    """データベースからFAQデータを取得"""
    try:
        param_format = get_param_format()
        
        # FAQ データと埋め込みを結合して取得
        query = f"""
            SELECT 
                fd.id,
                fd.question,
                fd.answer,
                fe.embedding_vector as embedding
            FROM faq_data fd
            LEFT JOIN faq_embeddings fe ON fd.id = fe.faq_id
            WHERE fd.company_id = {param_format}
            ORDER BY fd.id
        """
        
        results = fetch_dict(query, (company_id,))
        
        # エンベディングデータの処理
        faq_list = []
        for row in results:
            faq_item = {
                'id': row['id'],
                'question': row['question'],
                'answer': row['answer'],
                'embedding': None
            }
            
            # エンベディングの復元
            if row['embedding']:
                try:
                    embedding_data = row['embedding']
                    
                    # データ型に応じた処理（統一的にバイナリデータとして扱う）
                    if isinstance(embedding_data, memoryview):
                        # memoryviewの場合はbytesに変換してからデシリアライズ
                        faq_item['embedding'] = deserialize_embedding(embedding_data.tobytes())
                    elif isinstance(embedding_data, (bytes, bytearray)):
                        # バイナリデータの場合はそのままデシリアライズ
                        faq_item['embedding'] = deserialize_embedding(embedding_data)
                    elif isinstance(embedding_data, str):
                        # レガシー：文字列の場合はJSONとして解析（旧データ対応）
                        import json
                        faq_item['embedding'] = json.loads(embedding_data)
                    else:
                        # その他の場合は直接使用
                        faq_item['embedding'] = embedding_data
                        
                except Exception as e:
                    print(f"[DB] エンベディング復元エラー (FAQ ID: {row['id']}): {e}")
                    print(f"[DB] データ型: {type(row['embedding'])}, データサイズ: {len(embedding_data) if hasattr(embedding_data, '__len__') else 'Unknown'}")
                    # エラーの場合はNoneを設定
                    faq_item['embedding'] = None
            
            faq_list.append(faq_item)
        
        print(f"[DB] {company_id}のFAQデータ取得: {len(faq_list)}件")
        return faq_list
        
    except Exception as e:
        print(f"[DB] FAQデータ取得エラー: {e}")
        return []

def save_faq_to_db(company_id, question, answer, embedding=None):
    """FAQデータをデータベースに保存"""
    try:
        param_format = get_param_format()
        current_time = datetime.now().isoformat()
        
        # FAQ データの挿入
        faq_query = f"""
            INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
            VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format})
        """
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(faq_query, (company_id, question, answer, current_time, current_time))
            
            # 最後に挿入されたIDを取得
            if DB_TYPE == "postgresql":
                cursor.execute("SELECT lastval()")
                faq_id = cursor.fetchone()[0]
            else:
                faq_id = cursor.lastrowid
            
            # エンベディングがある場合は保存
            if embedding is not None:
                try:
                    serialized_embedding = serialize_embedding(embedding)
                    if serialized_embedding:
                        embedding_query = f"""
                            INSERT INTO faq_embeddings 
                            (faq_id, embedding_vector, vector_model, embedding_dim, created_at, updated_at)
                            VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                        """
                        
                        embedding_dim = len(embedding) if isinstance(embedding, (list, np.ndarray)) else 1024
                        
                        # PostgreSQL、SQLite共にバイナリデータとして保存
                        cursor.execute(embedding_query, (
                            faq_id, serialized_embedding, 'voyage-3', embedding_dim, current_time, current_time
                        ))
                except Exception as e:
                    print(f"[DB] エンベディング保存エラー (FAQ ID: {faq_id}): {e}")
            
            conn.commit()
            print(f"[DB] FAQ保存完了: {company_id} - {question[:50]}...")
            return faq_id
            
    except Exception as e:
        print(f"[DB] FAQ保存エラー: {e}")
        return None

def update_faq_in_db(faq_id, question=None, answer=None, embedding=None):
    """FAQデータをデータベースで更新"""
    try:
        param_format = get_param_format()
        current_time = datetime.now().isoformat()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # FAQ データの更新
            if question is not None or answer is not None:
                update_parts = []
                update_values = []
                
                if question is not None:
                    update_parts.append(f"question = {param_format}")
                    update_values.append(question)
                
                if answer is not None:
                    update_parts.append(f"answer = {param_format}")
                    update_values.append(answer)
                
                update_parts.append(f"updated_at = {param_format}")
                update_values.append(current_time)
                update_values.append(faq_id)
                
                faq_query = f"UPDATE faq_data SET {', '.join(update_parts)} WHERE id = {param_format}"
                cursor.execute(faq_query, update_values)
            
            # エンベディングの更新
            if embedding is not None:
                try:
                    # 既存のエンベディングを削除
                    delete_query = f"DELETE FROM faq_embeddings WHERE faq_id = {param_format}"
                    cursor.execute(delete_query, (faq_id,))
                    
                    # 新しいエンベディングを挿入
                    serialized_embedding = serialize_embedding(embedding)
                    if serialized_embedding:
                        embedding_query = f"""
                            INSERT INTO faq_embeddings 
                            (faq_id, embedding_vector, vector_model, embedding_dim, created_at, updated_at)
                            VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                        """
                        
                        embedding_dim = len(embedding) if isinstance(embedding, (list, np.ndarray)) else 1024
                        
                        # PostgreSQL、SQLite共にバイナリデータとして保存
                        cursor.execute(embedding_query, (
                            faq_id, serialized_embedding, 'voyage-3', embedding_dim, current_time, current_time
                        ))
                except Exception as e:
                    print(f"[DB] エンベディング更新エラー (FAQ ID: {faq_id}): {e}")
            
            conn.commit()
            print(f"[DB] FAQ更新完了: ID {faq_id}")
            return True
            
    except Exception as e:
        print(f"[DB] FAQ更新エラー: {e}")
        return False

def cleanup_corrupted_embeddings(company_id=None):
    """破損したエンベディングデータをクリーンアップ"""
    try:
        param_format = get_param_format()
        
        if company_id:
            # 特定企業のエンベディングをクリーンアップ
            query = f"""
                DELETE FROM faq_embeddings 
                WHERE faq_id IN (
                    SELECT id FROM faq_data WHERE company_id = {param_format}
                )
            """
            params = (company_id,)
        else:
            # 全エンベディングをクリーンアップ
            query = "DELETE FROM faq_embeddings"
            params = ()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            deleted_count = cursor.rowcount
            conn.commit()
            
        print(f"[CLEANUP] 破損エンベディング削除完了: {deleted_count}件")
        return deleted_count
        
    except Exception as e:
        print(f"[CLEANUP] エンベディングクリーンアップエラー: {e}")
        return 0
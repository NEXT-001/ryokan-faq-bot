"""
FAQ管理機能 - 管理者がFAQを追加・編集・削除するための機能
admin_faq_management.py
"""
import os
import pandas as pd
import streamlit as st
from datetime import datetime
import time
from dotenv import load_dotenv
from services.embedding_service import create_embeddings, create_embeddings_for_specific_faqs
from services.login_service import get_current_company_id
from config.unified_config import UnifiedConfig
from core.database import execute_query, fetch_dict, fetch_dict_one, DB_TYPE

# 環境変数読み込み
load_dotenv()

# 翻訳サービスの初期化
try:
    from services.translation_service import TranslationService
    translation_service = TranslationService()
    HAS_TRANSLATION = True
    print("[FAQ_MANAGEMENT] TranslationServiceが利用可能です")
except ImportError as e:
    translation_service = None
    HAS_TRANSLATION = False
    print(f"[FAQ_MANAGEMENT] TranslationService利用不可: {e}")

def translate_faq_to_languages(question, answer):
    """
    FAQ質問と回答を多言語に翻訳
    
    Args:
        question (str): 日本語の質問
        answer (str): 日本語の回答
        
    Returns:
        dict: 翻訳結果 {"en": {"question": "...", "answer": "..."}, ...}
    """
    if not HAS_TRANSLATION or not translation_service:
        print("[TRANSLATION] TranslationServiceが利用できません。翻訳をスキップします。")
        return {}
    
    target_languages = {
        "en": "英語",
        "ko": "韓国語", 
        "zh": "中国語(簡体)",      # データベースと一致するコード
        "zh-tw": "中国語(繁体)"   # データベースと一致するコード
    }
    
    translations = {}
    
    for lang_code, lang_name in target_languages.items():
        try:
            # 質問の翻訳
            translated_question = translation_service.translate_text(
                question, 
                target_language=lang_code, 
                source_language='ja'
            )
            
            # 回答の翻訳
            translated_answer = translation_service.translate_text(
                answer, 
                target_language=lang_code, 
                source_language='ja'
            )
            
            translations[lang_code] = {
                "question": translated_question,
                "answer": translated_answer
            }
            
            print(f"[TRANSLATION] {lang_name}翻訳完了: {lang_code}")
            
        except Exception as e:
            print(f"[TRANSLATION] {lang_name}翻訳エラー: {e}")
            continue
    
    return translations

def load_faq_data(company_id, language_filter=None):
    """
    指定された会社のFAQデータをデータベースから読み込む - DEBUG強化版
    
    Args:
        company_id (str): 会社ID
        language_filter (str, optional): 言語フィルター（'ja', 'en', etc.）
        
    Returns:
        pd.DataFrame: FAQデータフレーム（言語情報を含む）
    """
    print(f"[DEBUG_LOAD] load_faq_data called with: company_id={company_id}, language_filter={language_filter}")
    
    try:
        # データベースからFAQデータを取得（新しいものが上に表示されるようにDESC順）
        from core.database import DB_TYPE
        if language_filter:
            if DB_TYPE == "postgresql":
                query = "SELECT id, question, answer, language, created_at FROM faq_data WHERE company_id = %s AND language = %s ORDER BY created_at DESC"
            else:
                query = "SELECT id, question, answer, language, created_at FROM faq_data WHERE company_id = ? AND language = ? ORDER BY created_at DESC"
            params = (company_id, language_filter)
            print(f"[DEBUG_LOAD] 実行するクエリ（フィルター付き）: {query}")
            print(f"[DEBUG_LOAD] クエリパラメータ: {params}")
            results = fetch_dict(query, params)
        else:
            if DB_TYPE == "postgresql":
                query = "SELECT id, question, answer, language, created_at FROM faq_data WHERE company_id = %s ORDER BY created_at DESC"
            else:
                query = "SELECT id, question, answer, language, created_at FROM faq_data WHERE company_id = ? ORDER BY created_at DESC"
            params = (company_id,)
            print(f"[DEBUG_LOAD] 実行するクエリ（全言語）: {query}")
            print(f"[DEBUG_LOAD] クエリパラメータ: {params}")
            results = fetch_dict(query, params)
        
        print(f"[DEBUG_LOAD] データベースから取得した結果数: {len(results) if results else 0}")
        
        if results:
            # 取得したデータの最初の数件をデバッグ表示
            for i, result in enumerate(results[:3]):
                print(f"[DEBUG_LOAD] データ {i+1}: ID={result['id']}, Language={result['language']}, Question={result['question'][:30]}...")
            
            # データベースから取得したデータをDataFrameに変換
            df = pd.DataFrame(results)
            print(f"[DEBUG_LOAD] DataFrame作成完了: shape={df.shape}")
            print(f"[DEBUG_LOAD] DataFrame columns: {list(df.columns)}")
            
            # 言語名をより分かりやすく表示（データベースの実際の言語コードに対応）
            language_names = {
                'ja': '🇯🇵 日本語',
                'en': '🇺🇸 英語', 
                'ko': '🇰🇷 韓国語',
                'zh': '🇨🇳 中国語(簡体)',        # データベースの実際のコード
                'zh-CN': '🇨🇳 中国語(簡体)',     # 後方互換性
                'zh-tw': '🇹🇼 中国語(繁体)',      # データベースの実際のコード
                'zh-TW': '🇹🇼 中国語(繁体)'      # 後方互換性
            }
            df['language_display'] = df['language'].map(lambda x: language_names.get(x, f"🌐 {x}"))
            print(f"[DEBUG_LOAD] language_display列追加完了")
        else:
            # データがない場合は空のDataFrameを作成
            df = pd.DataFrame(columns=["id", "question", "answer", "language", "language_display", "created_at"])
            if not language_filter:
                st.info("FAQデータがデータベースに見つかりません。")
        
        return df
        
    except Exception as e:
        st.error(f"FAQデータの読み込み中にエラーが発生しました: {e}")
        # エラーの場合は空のDataFrameを返す
        return pd.DataFrame(columns=["id", "question", "answer", "language", "language_display", "created_at"])

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
        param_format = "%s" if DB_TYPE == "postgresql" else "?"
        delete_query = f"DELETE FROM faq_data WHERE company_id = {param_format}"
        execute_query(delete_query, (company_id,))
        
        # 新しいFAQデータを挿入
        insert_query = f"""
            INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
            VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format})
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

def add_faq_with_translations(question, answer, company_id):
    """
    FAQを多言語翻訳付きで追加する
    
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
        from core.database import DB_TYPE
        if DB_TYPE == "postgresql":
            check_query = "SELECT COUNT(*) as count FROM faq_data WHERE company_id = %s AND question = %s"
        else:
            check_query = "SELECT COUNT(*) as count FROM faq_data WHERE company_id = ? AND question = ?"
        result = fetch_dict_one(check_query, (company_id, question))
        if result and result['count'] > 0:
            return False, "同じ質問が既に登録されています。"
        
        # 多言語翻訳を実行
        translations = translate_faq_to_languages(question, answer)
        
        current_time = datetime.now().isoformat()
        
        # 追加されたFAQのIDを記録
        added_faq_ids = []
        
        # 日本語版FAQを追加（PostgreSQL対応のID取得）
        param_format = "%s" if DB_TYPE == "postgresql" else "?"
        
        if DB_TYPE == "postgresql":
            # RETURNING句を使用してIDを直接取得
            id_insert_query = f"""
                INSERT INTO faq_data (company_id, question, answer, language, created_at, updated_at)
                VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                RETURNING id
            """
            result = fetch_dict_one(id_insert_query, (company_id, question, answer, "ja", current_time, current_time))
            if result:
                added_faq_ids.append(result['id'])
                print(f"[FAQ_ADD] 日本語版FAQ保存完了 (ID: {result['id']})")
        else:
            insert_query = f"""
                INSERT INTO faq_data (company_id, question, answer, language, created_at, updated_at)
                VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
            """
            execute_query(insert_query, (company_id, question, answer, "ja", current_time, current_time))
            
            # 最後に挿入されたIDを取得
            last_id_query = "SELECT last_insert_rowid() as id"
            result = fetch_dict_one(last_id_query)
            if result:
                added_faq_ids.append(result['id'])
                print(f"[FAQ_ADD] 日本語版FAQ保存完了 (ID: {result['id']})")
        
        # 翻訳版FAQを追加
        for lang_code, translation in translations.items():
            try:
                if DB_TYPE == "postgresql":
                    result = fetch_dict_one(id_insert_query, (
                        company_id, 
                        translation["question"], 
                        translation["answer"], 
                        lang_code, 
                        current_time, 
                        current_time
                    ))
                    if result:
                        added_faq_ids.append(result['id'])
                        print(f"[FAQ_ADD] {lang_code}版FAQ保存完了 (ID: {result['id']})")
                else:
                    execute_query(insert_query, (
                        company_id, 
                        translation["question"], 
                        translation["answer"], 
                        lang_code, 
                        current_time, 
                        current_time
                    ))
                    
                    # 翻訳版のIDも記録
                    result = fetch_dict_one(last_id_query)
                    if result:
                        added_faq_ids.append(result['id'])
                        print(f"[FAQ_ADD] {lang_code}版FAQ保存完了 (ID: {result['id']})")
                    
            except Exception as e:
                print(f"{lang_code}版FAQ保存エラー: {e}")
                continue
        
        # 新規追加されたFAQのみエンベディングを生成
        if added_faq_ids:
            create_embeddings_for_specific_faqs(company_id, added_faq_ids, show_progress=True)
        
        translation_count = len(translations)
        message = f"FAQが追加されました。（日本語 + {translation_count}言語の翻訳版）"
        return True, message
        
    except Exception as e:
        return False, f"FAQ追加エラー: {str(e)}"

def add_faq(question, answer, company_id):
    """
    FAQを追加する（従来版・後方互換性のため）
    
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
        from core.database import DB_TYPE
        if DB_TYPE == "postgresql":
            check_query = "SELECT COUNT(*) as count FROM faq_data WHERE company_id = %s AND question = %s"
        else:
            check_query = "SELECT COUNT(*) as count FROM faq_data WHERE company_id = ? AND question = ?"
        result = fetch_dict_one(check_query, (company_id, question))
        if result and result['count'] > 0:
            return False, "同じ質問が既に登録されています。"
        
        # 新しいFAQを追加（PostgreSQL対応のID取得）
        param_format = "%s" if DB_TYPE == "postgresql" else "?"
        current_time = datetime.now().isoformat()
        
        if DB_TYPE == "postgresql":
            # RETURNING句を使用してIDを直接取得
            id_insert_query = f"""
                INSERT INTO faq_data (company_id, question, answer, language, created_at, updated_at)
                VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                RETURNING id
            """
            result = fetch_dict_one(id_insert_query, (company_id, question, answer, "ja", current_time, current_time))
            if result:
                print(f"[FAQ_ADD] FAQ保存完了 (ID: {result['id']})")
                with st.spinner("エンベディングを生成中..."):
                    create_embeddings_for_specific_faqs(company_id, [result['id']], show_progress=True)
        else:
            insert_query = f"""
                INSERT INTO faq_data (company_id, question, answer, language, created_at, updated_at)
                VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
            """
            execute_query(insert_query, (company_id, question, answer, "ja", current_time, current_time))
            
            # 最後に挿入されたIDを取得してエンベディング生成
            last_id_query = "SELECT last_insert_rowid() as id"
            result = fetch_dict_one(last_id_query)
            if result:
                print(f"[FAQ_ADD] FAQ保存完了 (ID: {result['id']})")
                with st.spinner("エンベディングを生成中..."):
                    create_embeddings_for_specific_faqs(company_id, [result['id']], show_progress=True)
        
        return True, "FAQを追加しました。"
        
    except Exception as e:
        st.error(f"FAQ追加エラー: {str(e)}")
        return False, "FAQの追加に失敗しました。"

def update_faq_by_id(faq_id, question, answer, company_id):
    """
    指定されたIDのFAQを更新する（ID直接指定版）- DEBUG強化版
    
    Args:
        faq_id (int): 更新するFAQのID
        question (str): 新しい質問
        answer (str): 新しい回答
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    print(f"[DEBUG] update_faq_by_id called with: faq_id={faq_id}, company_id={company_id}")
    print(f"[DEBUG] New question: {question[:50]}...")
    print(f"[DEBUG] New answer: {answer[:50]}...")
    
    if not question or not answer:
        return False, "質問と回答を入力してください。"
    
    try:
        # 更新前のFAQ状態を取得
        from core.database import DB_TYPE
        param_format = "%s" if DB_TYPE == "postgresql" else "?"
        check_query = f"SELECT id, question, answer, language FROM faq_data WHERE id = {param_format} AND company_id = {param_format}"
        result = fetch_dict_one(check_query, (faq_id, company_id))
        
        if not result:
            error_msg = f"指定されたFAQ（ID: {faq_id}）が見つからないか、アクセス権限がありません。"
            print(f"[DEBUG] {error_msg}")
            return False, error_msg
        
        print(f"[DEBUG] 更新前のFAQ - ID: {result['id']}, Language: {result['language']}")
        print(f"[DEBUG] 更新前の質問: {result['question']}")
        print(f"[DEBUG] 更新前の回答: {result['answer'][:50]}...")
        
        # FAQを更新
        update_query = f"""
            UPDATE faq_data 
            SET question = {param_format}, answer = {param_format}, updated_at = {param_format}
            WHERE id = {param_format}
        """
        current_time = datetime.now().isoformat()
        
        print(f"[DEBUG] 実行するクエリ: {update_query}")
        print(f"[DEBUG] クエリパラメータ: question={question[:30]}..., answer={answer[:30]}..., time={current_time}, id={faq_id}")
        
        rows_affected = execute_query(update_query, (question, answer, current_time, faq_id))
        print(f"[DEBUG] 更新された行数: {rows_affected}")
        
        # 更新後のFAQ状態を確認
        result_after = fetch_dict_one(check_query, (faq_id, company_id))
        if result_after:
            print(f"[DEBUG] 更新後のFAQ - ID: {result_after['id']}, Language: {result_after['language']}")
            print(f"[DEBUG] 更新後の質問: {result_after['question']}")
            print(f"[DEBUG] 更新後の回答: {result_after['answer'][:50]}...")
        
        # エンベディングを更新（更新されたFAQのみ）
        with st.spinner("エンベディングを生成中..."):
            create_embeddings_for_specific_faqs(company_id, [faq_id], show_progress=True)
        
        success_msg = f"FAQ（ID: {faq_id}）を更新しました。"
        print(f"[DEBUG] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"FAQ更新エラー（ID: {faq_id}）: {str(e)}"
        print(f"[DEBUG] {error_msg}")
        st.error(error_msg)
        return False, "FAQの更新に失敗しました。"

def update_faq(index, question, answer, company_id):
    """
    指定されたインデックスのFAQを更新する（後方互換性のため）
    
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
        # 指定されたインデックスのFAQ IDを取得（新しいものから順番）
        from core.database import DB_TYPE
        if DB_TYPE == "postgresql":
            query = "SELECT id FROM faq_data WHERE company_id = %s ORDER BY created_at DESC LIMIT 1 OFFSET %s"
        else:
            query = "SELECT id FROM faq_data WHERE company_id = ? ORDER BY created_at DESC LIMIT 1 OFFSET ?"
        result = fetch_dict_one(query, (company_id, index))
        
        if not result:
            return False, "無効なインデックスです。"
        
        faq_id = result['id']
        
        # 新しいID指定関数を呼び出し
        return update_faq_by_id(faq_id, question, answer, company_id)
        
    except Exception as e:
        st.error(f"FAQ更新エラー: {str(e)}")
        return False, "FAQの更新に失敗しました。"

def delete_faq_by_id(faq_id, company_id):
    """
    指定されたIDのFAQを削除する（ID直接指定版）- DEBUG強化版
    
    Args:
        faq_id (int): 削除するFAQのID
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    print(f"[DEBUG] delete_faq_by_id called with: faq_id={faq_id}, company_id={company_id}")
    
    try:
        # FAQが存在し、指定された会社のものかを確認
        from core.database import DB_TYPE
        param_format = "%s" if DB_TYPE == "postgresql" else "?"
        check_query = f"SELECT id, question, answer, language FROM faq_data WHERE id = {param_format} AND company_id = {param_format}"
        result = fetch_dict_one(check_query, (faq_id, company_id))
        
        if not result:
            error_msg = f"指定されたFAQ（ID: {faq_id}）が見つからないか、アクセス権限がありません。"
            print(f"[DEBUG] {error_msg}")
            return False, error_msg
        
        print(f"[DEBUG] 削除対象のFAQ - ID: {result['id']}, Language: {result['language']}")
        print(f"[DEBUG] 削除対象の質問: {result['question']}")
        print(f"[DEBUG] 削除対象の回答: {result['answer'][:50]}...")
        
        question_preview = result['question'][:30] + "..." if len(result['question']) > 30 else result['question']
        
        # 削除前に同じ会社の総FAQ数を確認
        count_before_query = f"SELECT COUNT(*) as count FROM faq_data WHERE company_id = {param_format}"
        count_before = fetch_dict_one(count_before_query, (company_id,))
        print(f"[DEBUG] 削除前のFAQ総数: {count_before['count'] if count_before else 'Unknown'}")
        
        # FAQを削除（外部キー制約により関連するエンベディングも自動削除される）
        delete_query = f"DELETE FROM faq_data WHERE id = {param_format}"
        print(f"[DEBUG] 実行するクエリ: {delete_query}")
        print(f"[DEBUG] クエリパラメータ: id={faq_id}")
        
        rows_affected = execute_query(delete_query, (faq_id,))
        print(f"[DEBUG] 削除された行数: {rows_affected}")
        
        # 削除後のFAQ総数を確認
        count_after = fetch_dict_one(count_before_query, (company_id,))
        print(f"[DEBUG] 削除後のFAQ総数: {count_after['count'] if count_after else 'Unknown'}")
        
        success_msg = f"FAQ（ID: {faq_id}）「{question_preview}」を削除しました。"
        print(f"[DEBUG] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"FAQ削除エラー（ID: {faq_id}）: {str(e)}"
        print(f"[DEBUG] {error_msg}")
        st.error(error_msg)
        return False, "FAQの削除に失敗しました。"

def delete_faq(index, company_id):
    """
    指定されたインデックスのFAQを削除する（後方互換性のため）
    
    Args:
        index (int): 削除するFAQのインデックス（表示順序）
        company_id (str): 会社ID
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    try:
        # 指定されたインデックスのFAQ IDを取得（新しいものから順番）
        from core.database import DB_TYPE
        if DB_TYPE == "postgresql":
            query = "SELECT id FROM faq_data WHERE company_id = %s ORDER BY created_at DESC LIMIT 1 OFFSET %s"
        else:
            query = "SELECT id FROM faq_data WHERE company_id = ? ORDER BY created_at DESC LIMIT 1 OFFSET ?"
        result = fetch_dict_one(query, (company_id, index))
        
        if not result:
            return False, "無効なインデックスです。"
        
        faq_id = result['id']
        
        # 新しいID指定関数を呼び出し
        return delete_faq_by_id(faq_id, company_id)
        
    except Exception as e:
        st.error(f"FAQ削除エラー: {str(e)}")
        return False, "FAQの削除に失敗しました。"

def import_faq_from_csv(uploaded_file, company_id, enable_translation=True):
    """
    アップロードされたCSVファイルからFAQを多言語対応でインポートする
    
    Args:
        uploaded_file: アップロードされたCSVファイル
        company_id (str): 会社ID
        enable_translation (bool): 多言語翻訳を有効にするかどうか
        
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
        from core.database import DB_TYPE
        if DB_TYPE == "postgresql":
            existing_questions_query = "SELECT question FROM faq_data WHERE company_id = %s"
        else:
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
        
        if not new_entries:
            return True, f"新しいエントリはありませんでした。{duplicate_count}件の重複エントリがスキップされました。"
        
        # 新しいエントリを多言語対応でデータベースに追加
        param_format = "%s" if DB_TYPE == "postgresql" else "?"
        insert_query = f"""
            INSERT INTO faq_data (company_id, question, answer, language, created_at, updated_at)
            VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
        """
        current_time = datetime.now().isoformat()
        
        # 追加されたFAQのIDを記録
        added_faq_ids = []
        total_added_count = 0
        
        with st.spinner("FAQを多言語対応で追加中..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, (question, answer) in enumerate(new_entries):
                try:
                    status_text.text(f"処理中: {i+1}/{len(new_entries)} - {question[:30]}...")
                    
                    # 日本語版FAQを追加（PostgreSQL対応のID取得）
                    if DB_TYPE == "postgresql":
                        # RETURNING句を使用してIDを直接取得
                        id_insert_query = f"""
                            INSERT INTO faq_data (company_id, question, answer, language, created_at, updated_at)
                            VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                            RETURNING id
                        """
                        result = fetch_dict_one(id_insert_query, (company_id, question, answer, "ja", current_time, current_time))
                        if result:
                            added_faq_ids.append(result['id'])
                            total_added_count += 1
                    else:
                        execute_query(insert_query, (company_id, question, answer, "ja", current_time, current_time))
                        # SQLiteでの最後のID取得
                        last_id_query = "SELECT last_insert_rowid() as id"
                        result = fetch_dict_one(last_id_query)
                        if result:
                            added_faq_ids.append(result['id'])
                            total_added_count += 1
                    
                    # 多言語翻訳が有効な場合は翻訳版も追加
                    if enable_translation:
                        translations = translate_faq_to_languages(question, answer)
                        for lang_code, translation in translations.items():
                            try:
                                # 翻訳版も同様にPostgreSQL対応のID取得
                                if DB_TYPE == "postgresql":
                                    result = fetch_dict_one(id_insert_query, (
                                        company_id, 
                                        translation["question"], 
                                        translation["answer"], 
                                        lang_code, 
                                        current_time, 
                                        current_time
                                    ))
                                    if result:
                                        added_faq_ids.append(result['id'])
                                        total_added_count += 1
                                        print(f"[FAQ_IMPORT] {lang_code}版FAQ保存完了 (ID: {result['id']})")
                                else:
                                    execute_query(insert_query, (
                                        company_id, 
                                        translation["question"], 
                                        translation["answer"], 
                                        lang_code, 
                                        current_time, 
                                        current_time
                                    ))
                                    
                                    # 翻訳版のIDも記録
                                    result = fetch_dict_one(last_id_query)
                                    if result:
                                        added_faq_ids.append(result['id'])
                                        total_added_count += 1
                                        print(f"[FAQ_IMPORT] {lang_code}版FAQ保存完了 (ID: {result['id']})")
                                    
                            except Exception as e:
                                print(f"翻訳版FAQ保存エラー ({lang_code}): {e}")
                                continue
                    
                    # 進行状況を更新
                    progress = (i + 1) / len(new_entries)
                    progress_bar.progress(progress)
                    
                except Exception as e:
                    print(f"FAQ追加エラー: {e}")
                    continue
        
        # 新規追加されたFAQのみエンベディングを生成
        if added_faq_ids:
            status_text.text("エンベディングを生成中...")
            create_embeddings_for_specific_faqs(company_id, added_faq_ids, show_progress=True)
        
        # 結果メッセージを作成
        if enable_translation:
            languages = ["日本語", "英語", "韓国語", "中国語(簡体)", "中国語(繁体)"]
            message = f"{len(new_entries)}件のFAQを{len(languages)}言語で追加しました。（合計: {total_added_count}件）"
        else:
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
        
        # 言語フィルターを削除 - すべての言語のFAQを表示
        # FAQは日本語のみのため、言語フィルターは不要
        
        # データの読み込み（すべての言語）
        df = load_faq_data(company_id, None)
        
        if len(df) == 0:
            st.info("FAQデータがありません。")
        else:
            st.write(f"**{len(df)}件のFAQが見つかりました**")
            
            # 各FAQを表示
            for i, row in df.iterrows():
                # 言語表示付きのタイトル
                faq_id = row.get('id')
                title = f"[{row.get('language_display', row.get('language', 'Unknown'))}] Q: {row['question'][:50]}..."
                
                print(f"[DEBUG_UI] 表示中のFAQ - DataFrame Index: {i}, FAQ ID: {faq_id}, Language: {row.get('language')}")
                
                with st.expander(title):
                    st.write(f"**質問**: {row['question']}")
                    st.write(f"**回答**: {row['answer']}")
                    st.write(f"**言語**: {row.get('language_display', row.get('language', 'Unknown'))}（DB: {row.get('language')}）")
                    st.write(f"**作成日**: {row.get('created_at', 'Unknown')}")
                    st.write(f"**FAQ ID**: {faq_id}")  # デバッグ情報として表示
                    st.write(f"**DataFrame Index**: {i}")  # デバッグ情報として表示
                    
                    # 編集フォーム（FAQ ID直接使用）
                    with st.form(key=f"edit_form_{faq_id}"):
                        st.subheader("FAQ編集")
                        new_question = st.text_area("質問", row["question"], key=f"q_{faq_id}")
                        new_answer = st.text_area("回答", row["answer"], key=f"a_{faq_id}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            submit = st.form_submit_button("更新")
                        with col2:
                            delete = st.form_submit_button("削除", type="primary")
                        
                        if submit:
                            print(f"[DEBUG_UI] UPDATE button clicked for FAQ ID: {faq_id}")
                            print(f"[DEBUG_UI] DataFrame row data: {dict(row)}")
                            print(f"[DEBUG_UI] Form question: {new_question[:50]}...")
                            print(f"[DEBUG_UI] Form answer: {new_answer[:50]}...")
                            
                            if faq_id:
                                st.info(f"[DEBUG] 更新開始 - FAQ ID: {faq_id}")
                                success, message = update_faq_by_id(faq_id, new_question, new_answer, company_id)
                                if success:
                                    st.success(message)
                                    time.sleep(1)  # 成功メッセージを表示する時間を確保
                                    st.rerun()
                                else:
                                    st.error(message)
                            else:
                                error_msg = f"FAQ IDが取得できませんでした。Row data: {dict(row)}"
                                print(f"[DEBUG_UI] {error_msg}")
                                st.error(error_msg)
                        
                        if delete:
                            print(f"[DEBUG_UI] DELETE button clicked for FAQ ID: {faq_id}")
                            print(f"[DEBUG_UI] DataFrame row data: {dict(row)}")
                            
                            if faq_id:
                                st.warning(f"[DEBUG] 削除開始 - FAQ ID: {faq_id}")
                                success, message = delete_faq_by_id(faq_id, company_id)
                                if success:
                                    st.success(message)
                                    time.sleep(1)  # 成功メッセージを表示する時間を確保
                                    st.rerun()
                                else:
                                    st.error(message)
                            else:
                                error_msg = f"FAQ IDが取得できませんでした。Row data: {dict(row)}"
                                print(f"[DEBUG_UI] {error_msg}")
                                st.error(error_msg)
    
    # FAQ追加タブ
    with tab2:
        st.subheader("新しいFAQを追加")
        
        # 多言語翻訳オプションを削除（日本語のみ保存に変更）
        # enable_translation = st.checkbox(
        #     "多言語翻訳を有効にする（英語・韓国語・中国語(簡体/繁体)）", 
        #     value=True,
        #     help="チェックすると、追加したFAQを自動的に英語・韓国語・中国語(簡体/繁体)に翻訳してDBに保存し、各言語版のエンベディングも生成します"
        # )
        
        with st.form(key="add_faq_form"):
            new_question = st.text_area("質問（日本語）")
            new_answer = st.text_area("回答（日本語）")
            submit = st.form_submit_button("追加")
            
            if submit:
                # 多言語翻訳を削除、日本語のみで保存
                success, message = add_faq(new_question, new_answer, company_id)
                
                if success:
                    st.success(message)
                    time.sleep(2)  # 成功メッセージを表示する時間を確保
                    # フォームをクリア
                    st.rerun()
                else:
                    st.error(message)
    
    # 一括管理タブ
    with tab3:
        st.subheader("一括管理")
        
        # インポート
        st.write("#### FAQをCSVからインポート")
        
        # 多言語翻訳オプションを削除（日本語のみ保存に変更）
        # enable_import_translation = st.checkbox(
        #     "多言語翻訳を有効にする（英語・韓国語・中国語(簡体/繁体)）", 
        #     value=True,
        #     key="import_translation",
        #     help="チェックすると、インポートしたFAQを自動的に英語・韓国語・中国語(簡体/繁体)に翻訳してDBに保存します"
        # )
        
        uploaded_file = st.file_uploader("CSVファイルをアップロード", type=["csv"])
        
        if uploaded_file is not None:
            if st.button("インポート実行"):
                # 多言語翻訳を無効化、日本語のみで保存
                success, message = import_faq_from_csv(uploaded_file, company_id, enable_translation=False)
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

#!/usr/bin/env python3
"""
重複メソッド検出GUI（Streamlit版）
ブラウザでインタラクティブに重複メソッドを確認できます
"""

import streamlit as st
import os
import ast
import hashlib
import difflib
from collections import defaultdict
from typing import Dict, List, Tuple
import pandas as pd

# メインの検出ロジックは上記のスクリプトから再利用
class MethodInfo:
    """メソッド情報を格納するクラス"""
    def __init__(self, name: str, file_path: str, line_number: int, 
                 signature: str, body: str, docstring: str = ""):
        self.name = name
        self.file_path = file_path
        self.line_number = line_number
        self.signature = signature
        self.body = body
        self.docstring = docstring
        self.body_hash = hashlib.md5(self.normalize_body().encode()).hexdigest()
        
    def normalize_body(self) -> str:
        """メソッド本体を正規化（コメント、空白を除去）"""
        lines = []
        for line in self.body.split('\n'):
            if '#' in line:
                line = line[:line.index('#')]
            line = line.strip()
            if line:
                lines.append(line)
        return '\n'.join(lines)
    
    def similarity_score(self, other: 'MethodInfo') -> float:
        """他のメソッドとの類似度を計算（0.0-1.0）"""
        if self.body_hash == other.body_hash:
            return 1.0
        
        normalized_self = self.normalize_body()
        normalized_other = other.normalize_body()
        
        if not normalized_self or not normalized_other:
            return 0.0
        
        similarity = difflib.SequenceMatcher(None, normalized_self, normalized_other).ratio()
        return similarity

class MethodAnalyzer(ast.NodeVisitor):
    """ASTを使ってPythonファイルからメソッドを抽出"""
    
    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_lines = source_code.split('\n')
        self.methods = []
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """関数定義を訪問"""
        self._extract_method_info(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """非同期関数定義を訪問"""
        self._extract_method_info(node)
        self.generic_visit(node)
    
    def _extract_method_info(self, node):
        """メソッド情報を抽出"""
        name = node.name
        line_number = node.lineno
        signature = self._build_signature(node)
        
        start_line = node.lineno - 1
        end_line = node.end_lineno - 1 if node.end_lineno else start_line
        body_lines = self.source_lines[start_line:end_line + 1]
        body = '\n'.join(body_lines)
        
        docstring = ast.get_docstring(node) or ""
        
        method_info = MethodInfo(
            name=name,
            file_path=self.file_path,
            line_number=line_number,
            signature=signature,
            body=body,
            docstring=docstring
        )
        
        self.methods.append(method_info)
    
    def _build_signature(self, node) -> str:
        """メソッドシグネチャを構築"""
        args = []
        
        for arg in node.args.args:
            args.append(arg.arg)
        
        default_offset = len(node.args.args) - len(node.args.defaults)
        for i, default in enumerate(node.args.defaults):
            arg_index = default_offset + i
            if arg_index < len(node.args.args):
                args[arg_index] += "=default"
        
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        
        return f"{node.name}({', '.join(args)})"

class StreamlitDuplicateFinder:
    """Streamlit用の重複メソッド検出クラス"""
    
    def __init__(self):
        self.all_methods: List[MethodInfo] = []
        self.duplicates = {}
        
    def scan_directory(self, directory_path: str, exclude_patterns: List[str]):
        """ディレクトリをスキャンしてメソッドを収集"""
        self.all_methods = []
        
        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self._analyze_file(file_path)
        
        return len(self.all_methods)
    
    def _analyze_file(self, file_path: str):
        """単一ファイルを分析"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code)
            analyzer = MethodAnalyzer(file_path, source_code)
            analyzer.visit(tree)
            
            self.all_methods.extend(analyzer.methods)
            
        except Exception as e:
            st.warning(f"ファイル分析エラー {file_path}: {e}")
    
    def find_duplicates(self, similarity_threshold: float = 0.8):
        """重複・類似メソッドを検出"""
        methods_by_name = defaultdict(list)
        for method in self.all_methods:
            methods_by_name[method.name].append(method)
        
        self.duplicates = {}
        
        for method_name, methods in methods_by_name.items():
            if len(methods) > 1:
                similar_groups = self._group_similar_methods(methods, similarity_threshold)
                if similar_groups:
                    self.duplicates[method_name] = similar_groups
        
        return self.duplicates
    
    def _group_similar_methods(self, methods: List[MethodInfo], threshold: float):
        """メソッドを類似度でグループ化"""
        groups = []
        processed = set()
        
        for i, method1 in enumerate(methods):
            if i in processed:
                continue
                
            current_group = [method1]
            processed.add(i)
            
            for j, method2 in enumerate(methods):
                if j <= i or j in processed:
                    continue
                
                similarity = method1.similarity_score(method2)
                if similarity >= threshold:
                    current_group.append(method2)
                    processed.add(j)
            
            if len(current_group) > 1:
                groups.append(current_group)
        
        return groups

def main():
    """Streamlitアプリのメイン関数"""
    st.set_page_config(
        page_title="重複メソッド検出ツール",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 重複メソッド検出ツール")
    st.markdown("プロジェクト内の重複・類似メソッドを検出して統合の機会を見つけます")
    
    # サイドバーでの設定
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # プロジェクトディレクトリの選択
        project_path = st.text_input(
            "プロジェクトパス", 
            value=".",
            help="分析するプロジェクトのディレクトリパス"
        )
        
        # 類似度閾値
        similarity_threshold = st.slider(
            "類似度閾値",
            min_value=0.5,
            max_value=1.0,
            value=0.8,
            step=0.05,
            help="この値以上の類似度を持つメソッドを重複として検出"
        )
        
        # 除外パターン
        default_excludes = [
            '__pycache__', '.git', '.venv', 'venv', 'env',
            'node_modules', '.pytest_cache', 'build', 'dist'
        ]
        
        exclude_patterns = st.multiselect(
            "除外パターン",
            options=default_excludes + ['test', 'tests', 'migrations'],
            default=default_excludes,
            help="スキャンから除外するディレクトリパターン"
        )
        
        # スキャン実行ボタン
        scan_button = st.button("🔍 スキャン実行", type="primary")
    
    # メインエリア
    if scan_button:
        if not os.path.exists(project_path):
            st.error(f"指定されたパスが存在しません: {project_path}")
            return
        
        # スキャン実行
        finder = StreamlitDuplicateFinder()
        
        with st.spinner("プロジェクトをスキャン中..."):
            method_count = finder.scan_directory(project_path, exclude_patterns)
        
        st.success(f"✅ スキャン完了！ {method_count}個のメソッドを検出しました")
        
        # 重複検出
        with st.spinner("重複メソッドを検索中..."):
            duplicates = finder.find_duplicates(similarity_threshold)
        
        # 結果表示
        if not duplicates:
            st.info("🎉 重複メソッドは見つかりませんでした！")
            
            # 統計情報
            with st.expander("📊 統計情報"):
                st.metric("総メソッド数", method_count)
                st.metric("重複メソッド", 0)
                st.metric("重複率", "0%")
        else:
            # 重複メソッドの詳細表示
            total_duplicates = sum(len(groups) for groups in duplicates.values())
            duplicate_methods = sum(sum(len(group) for group in groups) for groups in duplicates.values())
            
            # サマリー
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("総メソッド数", method_count)
            with col2:
                st.metric("重複グループ数", total_duplicates)
            with col3:
                st.metric("重複メソッド数", duplicate_methods)
            with col4:
                duplicate_rate = (duplicate_methods / method_count * 100) if method_count > 0 else 0
                st.metric("重複率", f"{duplicate_rate:.1f}%")
            
            st.markdown("---")
            
            # 重複メソッドの詳細
            for method_name, groups in duplicates.items():
                st.subheader(f"🔄 メソッド名: `{method_name}`")
                
                for i, group in enumerate(groups, 1):
                    with st.expander(f"グループ {i} ({len(group)}個のメソッド)", expanded=True):
                        
                        # グループ内のメソッド一覧
                        method_data = []
                        for j, method in enumerate(group):
                            relative_path = os.path.relpath(method.file_path, project_path)
                            method_data.append({
                                "No.": j + 1,
                                "シグネチャ": method.signature,
                                "ファイル": relative_path,
                                "行番号": method.line_number,
                                "Docstring": method.docstring[:50] + "..." if len(method.docstring) > 50 else method.docstring
                            })
                        
                        # データフレームで表示
                        df = pd.DataFrame(method_data)
                        st.dataframe(df, use_container_width=True)
                        
                        # 類似度マトリックス
                        if len(group) > 1:
                            st.write("**類似度マトリックス:**")
                            similarity_data = []
                            for k, method1 in enumerate(group):
                                row = {}
                                for l, method2 in enumerate(group):
                                    if k == l:
                                        row[f"メソッド{l+1}"] = "100%"
                                    elif k < l:
                                        similarity = method1.similarity_score(method2)
                                        row[f"メソッド{l+1}"] = f"{similarity:.1%}"
                                    else:
                                        row[f"メソッド{l+1}"] = "-"
                                similarity_data.append(row)
                            
                            similarity_df = pd.DataFrame(similarity_data, 
                                                       index=[f"メソッド{i+1}" for i in range(len(group))])
                            st.dataframe(similarity_df, use_container_width=True)
                        
                        # 推奨アクション
                        st.write("**🎯 推奨アクション:**")
                        
                        # 完全一致の場合
                        if len(group) > 1:
                            max_similarity = max(
                                group[i].similarity_score(group[j]) 
                                for i in range(len(group)) 
                                for j in range(i+1, len(group))
                            )
                            
                            if max_similarity >= 0.98:
                                st.error("🚨 ほぼ完全一致: 1つを残して他を削除することを検討")
                            elif max_similarity >= 0.9:
                                st.warning("⚠️ 非常に高い類似度: 統合を強く推奨")
                            elif max_similarity >= similarity_threshold:
                                st.info("💡 類似度が高い: 共通化を検討")
                        
                        # 各メソッドのコード表示（オプション）
                        show_code = st.checkbox(f"コードを表示 (グループ {i})", key=f"show_code_{method_name}_{i}")
                        if show_code:
                            for j, method in enumerate(group):
                                st.write(f"**メソッド {j+1}: {method.signature}**")
                                st.code(method.body, language="python")
                                st.markdown("---")
            
            # 全体的な推奨事項
            st.markdown("---")
            st.subheader("📋 全体的な推奨事項")
            
            recommendations = []
            
            # 完全一致のメソッド数をカウント
            exact_matches = 0
            high_similarity = 0
            
            for groups in duplicates.values():
                for group in groups:
                    if len(group) > 1:
                        max_sim = max(
                            group[i].similarity_score(group[j]) 
                            for i in range(len(group)) 
                            for j in range(i+1, len(group))
                        )
                        if max_sim >= 0.98:
                            exact_matches += 1
                        elif max_sim >= 0.9:
                            high_similarity += 1
            
            if exact_matches > 0:
                recommendations.append(f"🚨 **緊急**: {exact_matches}個のグループで完全一致を検出。即座に統合を検討")
            
            if high_similarity > 0:
                recommendations.append(f"⚠️ **重要**: {high_similarity}個のグループで高い類似度を検出。統合を検討")
            
            if duplicate_rate > 20:
                recommendations.append("📊 **全体**: 重複率が20%を超えています。コードの整理を推奨")
            
            recommendations.extend([
                "🔍 **確認**: 各メソッドが本当に必要か検討",
                "🏗️ **リファクタリング**: 共通部分を抽出してユーティリティ関数化",
                "📝 **命名**: 類似機能のメソッドは統一的な命名規則を採用",
                "🧪 **テスト**: 統合前に既存のテストが通ることを確認"
            ])
            
            for rec in recommendations:
                st.markdown(f"- {rec}")
            
            # レポートのダウンロード
            st.markdown("---")
            st.subheader("📄 レポートのエクスポート")
            
            # レポート生成
            report_text = generate_text_report(duplicates, project_path, method_count, duplicate_rate)
            
            st.download_button(
                label="📋 テキストレポートをダウンロード",
                data=report_text,
                file_name=f"duplicate_methods_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
            
            # CSV形式でのエクスポート
            csv_data = generate_csv_report(duplicates, project_path)
            st.download_button(
                label="📊 CSVレポートをダウンロード",
                data=csv_data,
                file_name=f"duplicate_methods_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    else:
        # 初期画面
        st.info("""
        ### 🚀 使い方
        
        1. **サイドバー**でプロジェクトパスと設定を入力
        2. **類似度閾値**を調整（推奨: 0.8）
        3. **スキャン実行**ボタンをクリック
        4. 結果を確認して重複メソッドを統合
        
        ### 💡 ヒント
        
        - **類似度閾値 0.9以上**: ほぼ同一のメソッド
        - **類似度閾値 0.8-0.9**: 統合を検討すべきメソッド  
        - **類似度閾値 0.7-0.8**: 共通化の可能性があるメソッド
        """)

def generate_text_report(duplicates: Dict, project_path: str, total_methods: int, duplicate_rate: float) -> str:
    """テキスト形式のレポートを生成"""
    lines = []
    lines.append("=" * 80)
    lines.append("重複メソッド検出レポート")
    lines.append("=" * 80)
    lines.append(f"生成日時: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"プロジェクト: {project_path}")
    lines.append(f"総メソッド数: {total_methods}")
    lines.append(f"重複率: {duplicate_rate:.1f}%")
    lines.append("")
    
    if not duplicates:
        lines.append("✅ 重複メソッドは見つかりませんでした。")
        return '\n'.join(lines)
    
    for method_name, groups in duplicates.items():
        lines.append(f"## メソッド名: {method_name}")
        lines.append("-" * 40)
        
        for i, group in enumerate(groups, 1):
            lines.append(f"\n### グループ {i} ({len(group)}個)")
            
            for j, method in enumerate(group, 1):
                relative_path = os.path.relpath(method.file_path, project_path)
                lines.append(f"  {j}. {method.signature}")
                lines.append(f"     📁 {relative_path}:{method.line_number}")
                
                if method.docstring:
                    first_line = method.docstring.split('\n')[0].strip()
                    lines.append(f"     📝 {first_line}")
            
            # 類似度情報
            if len(group) > 1:
                lines.append("\n  類似度:")
                for k in range(len(group)):
                    for l in range(k + 1, len(group)):
                        similarity = group[k].similarity_score(group[l])
                        lines.append(f"    {k+1}↔{l+1}: {similarity:.1%}")
        
        lines.append("")
    
    return '\n'.join(lines)

def generate_csv_report(duplicates: Dict, project_path: str) -> str:
    """CSV形式のレポートを生成"""
    rows = []
    
    for method_name, groups in duplicates.items():
        for group_idx, group in enumerate(groups, 1):
            for method_idx, method in enumerate(group, 1):
                relative_path = os.path.relpath(method.file_path, project_path)
                
                # 最高類似度を計算
                max_similarity = 0
                if len(group) > 1:
                    similarities = [
                        method.similarity_score(other) 
                        for other in group if other != method
                    ]
                    max_similarity = max(similarities) if similarities else 0
                
                rows.append({
                    'メソッド名': method_name,
                    'グループ': group_idx,
                    'メソッド番号': method_idx,
                    'シグネチャ': method.signature,
                    'ファイルパス': relative_path,
                    '行番号': method.line_number,
                    '最高類似度': f"{max_similarity:.1%}",
                    'グループサイズ': len(group),
                    'Docstring': method.docstring.replace('\n', ' ').strip()[:100]
                })
    
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)

if __name__ == "__main__":
    main()
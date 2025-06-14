#!/usr/bin/env python3
"""
シンプル重複メソッドチェッカー
現在のディレクトリで素早く重複メソッドをチェック
"""

import os
import ast
import hashlib
from collections import defaultdict

def find_duplicate_methods(directory="."):
    """重複メソッドを検出する簡易版"""
    
    print(f"🔍 {directory} をスキャン中...")
    
    # メソッド情報を収集
    methods = defaultdict(list)
    
    for root, dirs, files in os.walk(directory):
        # 不要なディレクトリをスキップ
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                analyze_file(file_path, methods)
    
    # 重複を検出
    duplicates = {}
    exact_matches = {}
    
    for method_name, method_list in methods.items():
        if len(method_list) > 1:
            # 名前の重複
            duplicates[method_name] = method_list
            
            # 完全一致をチェック
            body_groups = defaultdict(list)
            for method in method_list:
                body_hash = hashlib.md5(normalize_code(method['body']).encode()).hexdigest()
                body_groups[body_hash].append(method)
            
            for body_hash, same_body_methods in body_groups.items():
                if len(same_body_methods) > 1:
                    exact_matches[f"{method_name}_{body_hash[:8]}"] = same_body_methods
    
    # 結果を表示
    print_results(duplicates, exact_matches)
    
    return duplicates, exact_matches

def analyze_file(file_path, methods):
    """単一ファイルを分析してメソッドを抽出"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = {
                    'name': node.name,
                    'file': file_path,
                    'line': node.lineno,
                    'body': get_method_body(content, node),
                    'args': get_method_args(node)
                }
                methods[node.name].append(method_info)
                
    except Exception as e:
        print(f"⚠️  ファイル分析エラー {file_path}: {e}")

def get_method_body(content, node):
    """メソッド本体を取得"""
    lines = content.split('\n')
    start = node.lineno - 1
    end = node.end_lineno if node.end_lineno else start + 1
    return '\n'.join(lines[start:end])

def get_method_args(node):
    """メソッドの引数を取得"""
    args = [arg.arg for arg in node.args.args]
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")
    return args

def normalize_code(code):
    """コードを正規化（空白、コメント除去）"""
    lines = []
    for line in code.split('\n'):
        # コメント除去
        if '#' in line:
            line = line[:line.index('#')]
        line = line.strip()
        if line:
            lines.append(line)
    return '\n'.join(lines)

def print_results(duplicates, exact_matches):
    """結果を表示"""
    print("\n" + "="*60)
    print("🔍 重複メソッド検出結果")
    print("="*60)
    
    if not duplicates:
        print("✅ 重複メソッドは見つかりませんでした！")
        return
    
    # 統計情報
    total_duplicate_methods = sum(len(methods) for methods in duplicates.values())
    print(f"📊 重複メソッド名: {len(duplicates)}個")
    print(f"📊 重複メソッド総数: {total_duplicate_methods}個")
    print(f"📊 完全一致グループ: {len(exact_matches)}個")
    print()
    
    # 完全一致（最優先）
    if exact_matches:
        print("🚨 完全一致メソッド（即座に統合推奨）:")
        print("-" * 40)
        for group_name, methods in exact_matches.items():
            method_name = methods[0]['name']
            print(f"\n'{method_name}' - {len(methods)}個の完全一致:")
            for method in methods:
                rel_path = os.path.relpath(method['file'])
                print(f"  📁 {rel_path}:{method['line']}")
        print()
    
    # 名前の重複（完全一致以外）
    print("🔄 同名メソッド:")
    print("-" * 40)
    
    for method_name, methods in duplicates.items():
        # 完全一致でないもののみ表示
        non_exact = []
        body_hashes = set()
        
        for method in methods:
            body_hash = hashlib.md5(normalize_code(method['body']).encode()).hexdigest()
            if body_hash not in body_hashes:
                non_exact.append(method)
                body_hashes.add(body_hash)
        
        if len(non_exact) > 1:  # 異なる実装がある場合のみ
            print(f"\n'{method_name}' - {len(methods)}個 (実装: {len(non_exact)}種類):")
            for method in methods:
                rel_path = os.path.relpath(method['file'])
                args_str = ', '.join(method['args'])
                print(f"  📁 {rel_path}:{method['line']} - {method_name}({args_str})")
    
    print("\n" + "="*60)
    print("🎯 推奨アクション:")
    print("="*60)
    
    actions = []
    
    if exact_matches:
        actions.append(f"🚨 {len(exact_matches)}個の完全一致を統合（最優先）")
    
    different_implementations = 0
    for methods in duplicates.values():
        if len(set(hashlib.md5(normalize_code(m['body']).encode()).hexdigest() for m in methods)) > 1:
            different_implementations += 1
    
    if different_implementations > 0:
        actions.append(f"🔍 {different_implementations}個の同名メソッドの実装差異を確認")
    
    actions.extend([
        "📝 メソッドの必要性を個別に検討",
        "🏗️ 共通部分をユーティリティ関数として抽出",
        "🧪 統合前にテストを実行して動作確認"
    ])
    
    for i, action in enumerate(actions, 1):
        print(f"{i}. {action}")
    
    print(f"\n💡 ヒント: 完全一致メソッドから優先的に統合することを推奨します")

def main():
    """メイン実行関数"""
    import sys
    
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    
    if not os.path.exists(directory):
        print(f"❌ ディレクトリが見つかりません: {directory}")
        return
    
    find_duplicate_methods(directory)

if __name__ == "__main__":
    main()
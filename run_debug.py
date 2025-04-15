# ファイル: run_debug.py (プロジェクトルートに配置)
from services.debug_functions import run_diagnostics

print("診断を実行中...")
results = run_diagnostics()
print("診断が完了しました。")
print(f"デバッグレポートが 'faq_debug_report.json' と 'embedding_debug_report.json' に保存されました。")

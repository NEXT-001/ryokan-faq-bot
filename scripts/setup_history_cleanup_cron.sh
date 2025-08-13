#!/bin/bash
"""
検索履歴クリーンアップの定期実行設定
scripts/setup_history_cleanup_cron.sh

crontabに履歴削除の定期実行を設定するためのスクリプト
"""

# プロジェクトのパスを設定（実際のパスに変更してください）
PROJECT_PATH="/mnt/c/Users/kangj/Documents/GitHub/ryokan-faq-bot"
PYTHON_PATH="python"  # または /usr/bin/python3 など
LOG_PATH="$PROJECT_PATH/logs/history_cleanup.log"

# ログディレクトリ作成
mkdir -p "$PROJECT_PATH/logs"

echo "🔧 検索履歴クリーンアップのcron設定"
echo "=" * 50

# 現在のcrontab設定を確認
echo "現在のcrontab設定:"
crontab -l 2>/dev/null || echo "crontabが設定されていません"

echo ""
echo "推奨設定例:"
echo ""

# 設定例1: 毎週日曜日午前2時に30日より古い履歴を削除
echo "# 毎週日曜日午前2時に30日より古い履歴を削除（バックアップ付き）"
echo "0 2 * * 0 cd $PROJECT_PATH && $PYTHON_PATH scripts/cleanup_search_history.py --days 30 --backup /tmp/history_backup_\$(date +\\%Y\\%m\\%d).csv --force >> $LOG_PATH 2>&1"
echo ""

# 設定例2: 毎日午前3時に90日より古い履歴を削除
echo "# 毎日午前3時に90日より古い履歴を削除"
echo "0 3 * * * cd $PROJECT_PATH && $PYTHON_PATH scripts/cleanup_search_history.py --days 90 --force >> $LOG_PATH 2>&1"
echo ""

# 設定例3: 毎月1日に180日より古い履歴を削除
echo "# 毎月1日午前1時に180日より古い履歴を削除（バックアップ付き）"
echo "0 1 1 * * cd $PROJECT_PATH && $PYTHON_PATH scripts/cleanup_search_history.py --days 180 --backup /var/backups/history_backup_\$(date +\\%Y\\%m).csv --force >> $LOG_PATH 2>&1"
echo ""

# インタラクティブ設定
echo "自動設定を行いますか？"
echo "1) 毎週日曜日午前2時に30日より古い履歴を削除"
echo "2) 毎日午前3時に90日より古い履歴を削除"
echo "3) 毎月1日に180日より古い履歴を削除"
echo "4) カスタム設定"
echo "5) 設定しない"

read -p "選択してください (1-5): " choice

case $choice in
    1)
        # 週次削除（30日）
        CRON_JOB="0 2 * * 0 cd $PROJECT_PATH && $PYTHON_PATH scripts/cleanup_search_history.py --days 30 --backup /tmp/history_backup_\$(date +%Y%m%d).csv --force >> $LOG_PATH 2>&1"
        ;;
    2)
        # 日次削除（90日）
        CRON_JOB="0 3 * * * cd $PROJECT_PATH && $PYTHON_PATH scripts/cleanup_search_history.py --days 90 --force >> $LOG_PATH 2>&1"
        ;;
    3)
        # 月次削除（180日）
        CRON_JOB="0 1 1 * * cd $PROJECT_PATH && $PYTHON_PATH scripts/cleanup_search_history.py --days 180 --backup /var/backups/history_backup_\$(date +%Y%m).csv --force >> $LOG_PATH 2>&1"
        ;;
    4)
        # カスタム設定
        read -p "削除対象日数を入力してください: " DAYS
        read -p "実行時間（時）を入力してください (0-23): " HOUR
        read -p "実行時間（分）を入力してください (0-59): " MINUTE
        read -p "バックアップファイルパス（省略可能）: " BACKUP_PATH
        
        if [ -n "$BACKUP_PATH" ]; then
            CRON_JOB="$MINUTE $HOUR * * * cd $PROJECT_PATH && $PYTHON_PATH scripts/cleanup_search_history.py --days $DAYS --backup $BACKUP_PATH --force >> $LOG_PATH 2>&1"
        else
            CRON_JOB="$MINUTE $HOUR * * * cd $PROJECT_PATH && $PYTHON_PATH scripts/cleanup_search_history.py --days $DAYS --force >> $LOG_PATH 2>&1"
        fi
        ;;
    5)
        echo "設定をスキップしました。"
        exit 0
        ;;
    *)
        echo "無効な選択です。"
        exit 1
        ;;
esac

# crontabに追加
echo "$CRON_JOB" | crontab -
echo ""
echo "✅ crontab設定完了!"
echo "設定内容: $CRON_JOB"
echo ""
echo "設定確認:"
crontab -l
echo ""
echo "ログファイル: $LOG_PATH"
echo ""
echo "手動実行例:"
echo "cd $PROJECT_PATH"
echo "python scripts/cleanup_search_history.py --stats-only"
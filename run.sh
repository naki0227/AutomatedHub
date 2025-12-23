#!/bin/bash
# Enludus Automation Hub Launcher
# Usage: ./run.sh [command]

cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"

case "$1" in
    morning)
        python scripts/daily_routine.py morning
        ;;
    afternoon)
        python scripts/daily_routine.py afternoon "${@:2}"
        ;;
    evening)
        python scripts/daily_routine.py evening
        ;;
    all)
        python scripts/daily_routine.py all "${@:2}"
        ;;
    gen|generate)
        python scripts/generate_content.py "${@:2}"
        ;;
    post)
        python scripts/post_to_x.py "${@:2}"
        ;;
    trends)
        python scripts/analyze_trends.py "${@:2}"
        ;;
    *)
        echo "🚀 Enludus Automation Hub"
        echo ""
        echo "Usage: ./run.sh [command]"
        echo ""
        echo "Commands:"
        echo "  morning     - 朝ルーティン（トレンド収集）"
        echo "  afternoon   - 昼ルーティン（コンテンツ生成・投稿）"
        echo "  evening     - 夜ルーティン（通知確認）"
        echo "  all         - 全ルーティン実行"
        echo "  gen         - コンテンツ生成 (--topic \"話題\")"
        echo "  post        - X投稿 (--list で下書き一覧)"
        echo "  trends      - トレンド分析"
        echo ""
        echo "Examples:"
        echo "  ./run.sh morning"
        echo "  ./run.sh gen --topic \"Encuraの新機能\""
        echo "  ./run.sh all --post    # 実際に投稿"
        ;;
esac

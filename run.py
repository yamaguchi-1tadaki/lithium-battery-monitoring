"""
リチウムイオンバッテリー監視システム起動スクリプト

本番・開発環境での起動を管理
"""

import os
import sys
import argparse
from datetime import datetime
import structlog

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app
from utils.db_manager import db_manager

# ログ設定
logger = structlog.get_logger()

def main():
    """メイン起動関数"""
    parser = argparse.ArgumentParser(description='バッテリー監視システム')
    parser.add_argument('--config', 
                       choices=['development', 'production', 'testing'],
                       default='development',
                       help='設定環境 (default: development)')
    parser.add_argument('--host', 
                       default='0.0.0.0',
                       help='バインドするホスト (default: 0.0.0.0)')
    parser.add_argument('--port', 
                       type=int, 
                       default=5000,
                       help='ポート番号 (default: 5000)')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='デバッグモードで起動')
    parser.add_argument('--init-db', 
                       action='store_true',
                       help='データベース初期化')
    parser.add_argument('--cleanup-db', 
                       action='store_true',
                       help='データベースクリーンアップ')
    parser.add_argument('--no-data-collection',
                       action='store_true',
                       help='データ収集を無効にする')
    
    args = parser.parse_args()
    
    try:
        # アプリケーション作成
        app, socketio = create_app(args.config)
        
        # データベース管理設定
        db_manager.app = app
        
        # データベース初期化
        if args.init_db:
            logger.info("データベース初期化開始")
            if db_manager.init_database():
                logger.info("データベース初期化完了")
            else:
                logger.error("データベース初期化失敗")
                return 1
        
        # データベースクリーンアップ
        if args.cleanup_db:
            logger.info("データベースクリーンアップ開始")
            deleted = db_manager.cleanup_old_data(days_to_keep=30)
            logger.info("データベースクリーンアップ完了", deleted_records=deleted)
        
        # データ収集開始
        if not args.no_data_collection:
            from services.data_collector import data_collector
            data_collector.start_collection()
            logger.info("データ収集開始")
        
        # システム情報出力
        print_system_info(app, args)
        
        # サーバー起動
        logger.info("バッテリー監視システム起動",
                   host=args.host,
                   port=args.port,
                   config=args.config,
                   debug=args.debug)
        
        socketio.run(app, 
                    host=args.host,
                    port=args.port,
                    debug=args.debug,
                    use_reloader=False)  # データ収集スレッドとの競合回避
        
    except KeyboardInterrupt:
        logger.info("システム停止中...")
        cleanup_and_exit()
    except Exception as e:
        logger.error("システム起動エラー", error=str(e))
        return 1
    
    return 0

def print_system_info(app, args):
    """システム情報表示"""
    print("\n" + "="*80)
    print("🔋 リチウムイオンバッテリー監視システム")
    print("   Battery Health Monitoring System (BHMS)")
    print("="*80)
    
    print(f"📅 起動時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚙️  環境設定: {args.config}")
    print(f"🌐 アクセスURL: http://{args.host}:{args.port}")
    print(f"🔧 デバッグモード: {'有効' if args.debug else '無効'}")
    
    with app.app_context():
        # データベース統計
        stats = db_manager.get_database_stats()
        if stats:
            print(f"💾 データベース統計:")
            print(f"   - バッテリー数: {stats['tables']['batteries']}")
            print(f"   - センサーデータ: {stats['tables']['sensor_data']:,}")
            print(f"   - アクティブアラート: {stats['alert_status']['active']}")
            print(f"   - 有効データ率: {calculate_data_validity_rate(stats):.1f}%")
    
    print("\n🚀 機能一覧:")
    print("   ✅ リアルタイムセンサーデータ収集")
    print("   ✅ AI機械学習による予兆検知")
    print("   ✅ WebSocketリアルタイム通信")
    print("   ✅ 異常アラート自動検出")
    print("   ✅ ダッシュボードによる可視化")
    print("   ✅ 管理者用システム制御")
    
    print("\n👤 ログイン情報:")
    print("   管理者: admin / admin123")
    print("   操作者: operator / operator123")
    print("   閲覧者: viewer / viewer123")
    
    print("\n📊 API エンドポイント:")
    print(f"   - システム状態: http://{args.host}:{args.port}/api/system/status")
    print(f"   - バッテリー一覧: http://{args.host}:{args.port}/api/batteries")
    print(f"   - アラート一覧: http://{args.host}:{args.port}/api/alerts")
    
    print("\n⚠️  注意事項:")
    print("   - 本システムはデモ用途です")
    print("   - 実際のセンサーはシミュレーションです")
    print("   - データはSQLiteに保存されます")
    
    print("="*80)

def calculate_data_validity_rate(stats):
    """データ有効性率計算"""
    valid = stats['data_quality']['valid_sensor_data']
    invalid = stats['data_quality']['invalid_sensor_data']
    total = valid + invalid
    
    if total == 0:
        return 100.0
    
    return (valid / total) * 100

def cleanup_and_exit():
    """終了時のクリーンアップ"""
    try:
        from services.data_collector import data_collector
        from services.sensor_simulator import sensor_system
        
        # データ収集停止
        data_collector.stop_collection()
        
        # センサーシミュレーション停止
        sensor_system.stop_simulation()
        
        logger.info("システム終了処理完了")
        
    except Exception as e:
        logger.error("終了処理エラー", error=str(e))

if __name__ == '__main__':
    sys.exit(main())
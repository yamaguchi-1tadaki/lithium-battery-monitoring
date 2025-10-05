"""
データベース管理ユーティリティ

データベースの初期化、メンテナンス、バックアップ機能を提供
"""

import os
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import pandas as pd
from flask import current_app
import structlog

from models.models import db, User, Battery, SensorData, Alert, Prediction, SystemLog
from services.sensor_simulator import sensor_system
from werkzeug.security import generate_password_hash

logger = structlog.get_logger()

class DatabaseManager:
    """データベース管理クラス"""
    
    def __init__(self, app=None):
        self.app = app
    
    def init_database(self) -> bool:
        """データベース初期化"""
        try:
            with self.app.app_context():
                # テーブル作成
                db.create_all()
                
                # 初期データ投入
                self._create_default_users()
                self._create_sample_batteries()
                
                logger.info("データベース初期化完了")
                return True
                
        except Exception as e:
            logger.error("データベース初期化エラー", error=str(e))
            return False
    
    def _create_default_users(self) -> None:
        """デフォルトユーザー作成"""
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@battery-monitor.com',
                'password': 'admin123',
                'is_admin': True
            },
            {
                'username': 'operator',
                'email': 'operator@battery-monitor.com',
                'password': 'operator123',
                'is_admin': False
            },
            {
                'username': 'viewer',
                'email': 'viewer@battery-monitor.com',
                'password': 'viewer123',
                'is_admin': False
            }
        ]
        
        for user_data in users_data:
            existing_user = User.query.filter_by(username=user_data['username']).first()
            if not existing_user:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=generate_password_hash(user_data['password']),
                    is_admin=user_data['is_admin']
                )
                db.session.add(user)
                logger.info("デフォルトユーザー作成", username=user_data['username'])
        
        db.session.commit()
    
    def _create_sample_batteries(self) -> None:
        """サンプルバッテリー作成"""
        batteries_data = [
            {
                'battery_id': 'BATTERY_001',
                'model': 'Li-ion 18650 Samsung INR18650-25R',
                'capacity_nominal': 2.5,
                'voltage_nominal': 3.7,
                'location': '製造ライン A-1',
                'installation_date': datetime.now().date()
            },
            {
                'battery_id': 'BATTERY_002',
                'model': 'Li-ion 18650 Panasonic NCR18650B',
                'capacity_nominal': 3.4,
                'voltage_nominal': 3.7,
                'location': '製造ライン A-2',
                'installation_date': datetime.now().date()
            },
            {
                'battery_id': 'BATTERY_003',
                'model': 'Li-ion Pouch LG Chem E63',
                'capacity_nominal': 63.0,
                'voltage_nominal': 3.8,
                'location': '蓄電システム B-1',
                'installation_date': datetime.now().date()
            },
            {
                'battery_id': 'BATTERY_004',
                'model': 'Li-ion Prismatic BYD Blade',
                'capacity_nominal': 202.0,
                'voltage_nominal': 3.2,
                'location': '蓄電システム B-2',
                'installation_date': datetime.now().date()
            },
            {
                'battery_id': 'BATTERY_005',
                'model': 'Li-ion 21700 Tesla Model Y',
                'capacity_nominal': 4.8,
                'voltage_nominal': 3.7,
                'location': '車載用テスト',
                'installation_date': datetime.now().date()
            }
        ]
        
        for battery_data in batteries_data:
            existing_battery = Battery.query.filter_by(
                battery_id=battery_data['battery_id']
            ).first()
            
            if not existing_battery:
                battery = Battery(**battery_data)
                db.session.add(battery)
                logger.info("サンプルバッテリー作成", battery_id=battery_data['battery_id'])
                
                # センサーシミュレーターにも追加
                if battery_data['battery_id'] not in sensor_system.simulators:
                    sensor_system.add_battery(
                        battery_data['battery_id'],
                        nominal_voltage=battery_data['voltage_nominal'],
                        nominal_capacity=battery_data['capacity_nominal']
                    )
        
        db.session.commit()
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """古いデータのクリーンアップ"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            with self.app.app_context():
                # 古いセンサーデータ削除
                deleted_sensor = SensorData.query.filter(
                    SensorData.timestamp < cutoff_date
                ).delete()
                
                # 古いシステムログ削除（エラーログは長期保持）
                deleted_logs = SystemLog.query.filter(
                    SystemLog.timestamp < cutoff_date,
                    SystemLog.level.in_(['DEBUG', 'INFO'])
                ).delete()
                
                # 解決済みアラートの古いものを削除
                deleted_alerts = Alert.query.filter(
                    Alert.created_at < cutoff_date,
                    Alert.status == 'resolved'
                ).delete()
                
                db.session.commit()
                
                total_deleted = deleted_sensor + deleted_logs + deleted_alerts
                logger.info("データクリーンアップ完了", 
                          deleted_sensor=deleted_sensor,
                          deleted_logs=deleted_logs,
                          deleted_alerts=deleted_alerts,
                          total=total_deleted)
                
                return total_deleted
                
        except Exception as e:
            logger.error("データクリーンアップエラー", error=str(e))
            db.session.rollback()
            return 0
    
    def backup_database(self, backup_path: str) -> bool:
        """データベースバックアップ"""
        try:
            # SQLiteの場合
            if 'sqlite' in current_app.config['SQLALCHEMY_DATABASE_URI']:
                db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                
                # バックアップディレクトリ作成
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                
                # SQLiteファイルをコピー
                import shutil
                shutil.copy2(db_path, backup_path)
                
                logger.info("データベースバックアップ完了", backup_path=backup_path)
                return True
            
            # PostgreSQLなどの場合は別の方法を実装
            else:
                logger.warning("SQLite以外のデータベースバックアップは未実装")
                return False
                
        except Exception as e:
            logger.error("データベースバックアップエラー", error=str(e))
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """データベース復元"""
        try:
            if not os.path.exists(backup_path):
                logger.error("バックアップファイルが存在しません", backup_path=backup_path)
                return False
            
            # SQLiteの場合
            if 'sqlite' in current_app.config['SQLALCHEMY_DATABASE_URI']:
                db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                
                # 現在のデータベースをバックアップ
                current_backup = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                import shutil
                shutil.copy2(db_path, current_backup)
                
                # バックアップファイルから復元
                shutil.copy2(backup_path, db_path)
                
                logger.info("データベース復元完了", 
                          backup_path=backup_path,
                          current_backup=current_backup)
                return True
            
            else:
                logger.warning("SQLite以外のデータベース復元は未実装")
                return False
                
        except Exception as e:
            logger.error("データベース復元エラー", error=str(e))
            return False
    
    def get_database_stats(self) -> Dict:
        """データベース統計情報取得"""
        try:
            with self.app.app_context():
                stats = {
                    'tables': {
                        'users': User.query.count(),
                        'batteries': Battery.query.count(),
                        'sensor_data': SensorData.query.count(),
                        'predictions': Prediction.query.count(),
                        'alerts': Alert.query.count(),
                        'system_logs': SystemLog.query.count()
                    },
                    'data_quality': {
                        'valid_sensor_data': SensorData.query.filter_by(is_valid=True).count(),
                        'invalid_sensor_data': SensorData.query.filter_by(is_valid=False).count()
                    },
                    'alert_status': {
                        'active': Alert.query.filter_by(status='active').count(),
                        'acknowledged': Alert.query.filter_by(status='acknowledged').count(),
                        'resolved': Alert.query.filter_by(status='resolved').count()
                    },
                    'time_range': {}
                }
                
                # データ時間範囲
                oldest_data = SensorData.query.order_by(SensorData.timestamp.asc()).first()
                newest_data = SensorData.query.order_by(SensorData.timestamp.desc()).first()
                
                if oldest_data and newest_data:
                    stats['time_range'] = {
                        'oldest': oldest_data.timestamp.isoformat(),
                        'newest': newest_data.timestamp.isoformat(),
                        'span_days': (newest_data.timestamp - oldest_data.timestamp).days
                    }
                
                return stats
                
        except Exception as e:
            logger.error("データベース統計取得エラー", error=str(e))
            return {}
    
    def export_data_to_csv(self, table_name: str, output_path: str, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> bool:
        """データをCSVエクスポート"""
        try:
            with self.app.app_context():
                # テーブル選択
                if table_name == 'sensor_data':
                    query = SensorData.query
                    if start_date:
                        query = query.filter(SensorData.timestamp >= start_date)
                    if end_date:
                        query = query.filter(SensorData.timestamp <= end_date)
                    
                    data = query.all()
                    
                    # DataFrame作成
                    df = pd.DataFrame([{
                        'battery_id': item.battery_id,
                        'timestamp': item.timestamp,
                        'voltage': item.voltage,
                        'current': item.current,
                        'temperature': item.temperature,
                        'capacity': item.capacity,
                        'power': item.power,
                        'internal_resistance': item.internal_resistance,
                        'cycle_count': item.cycle_count,
                        'is_valid': item.is_valid,
                        'quality_score': item.quality_score
                    } for item in data])
                    
                elif table_name == 'alerts':
                    data = Alert.query.all()
                    
                    df = pd.DataFrame([{
                        'id': item.id,
                        'battery_id': item.battery_id,
                        'created_at': item.created_at,
                        'alert_type': item.alert_type,
                        'severity': item.severity,
                        'title': item.title,
                        'message': item.message,
                        'status': item.status,
                        'sensor_value': item.sensor_value,
                        'threshold_value': item.threshold_value
                    } for item in data])
                    
                elif table_name == 'predictions':
                    data = Prediction.query.all()
                    
                    df = pd.DataFrame([{
                        'id': item.id,
                        'battery_id': item.battery_id,
                        'created_at': item.created_at,
                        'risk_level': item.risk_level,
                        'confidence_score': item.confidence_score,
                        'health_score': item.health_score,
                        'degradation_rate': item.degradation_rate,
                        'remaining_cycles': item.remaining_cycles,
                        'model_version': item.model_version
                    } for item in data])
                    
                else:
                    logger.error("サポートされていないテーブル", table_name=table_name)
                    return False
                
                # CSV出力
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                
                logger.info("CSVエクスポート完了",
                          table=table_name,
                          output_path=output_path,
                          records=len(df))
                return True
                
        except Exception as e:
            logger.error("CSVエクスポートエラー", error=str(e))
            return False
    
    def import_data_from_csv(self, table_name: str, csv_path: str) -> bool:
        """CSVからデータインポート"""
        try:
            if not os.path.exists(csv_path):
                logger.error("CSVファイルが存在しません", csv_path=csv_path)
                return False
            
            with self.app.app_context():
                df = pd.read_csv(csv_path)
                
                if table_name == 'sensor_data':
                    for _, row in df.iterrows():
                        # バッテリーIDから実際のバッテリーを検索
                        battery = Battery.query.filter_by(battery_id=row['battery_id']).first()
                        if not battery:
                            continue
                        
                        sensor_data = SensorData(
                            battery_id=battery.id,
                            timestamp=pd.to_datetime(row['timestamp']),
                            voltage=row['voltage'],
                            current=row['current'],
                            temperature=row['temperature'],
                            capacity=row['capacity'],
                            power=row.get('power', 0),
                            internal_resistance=row.get('internal_resistance', 0),
                            cycle_count=row.get('cycle_count', 0),
                            is_valid=row.get('is_valid', True),
                            quality_score=row.get('quality_score', 1.0)
                        )
                        db.session.add(sensor_data)
                
                elif table_name == 'batteries':
                    for _, row in df.iterrows():
                        existing = Battery.query.filter_by(battery_id=row['battery_id']).first()
                        if not existing:
                            battery = Battery(
                                battery_id=row['battery_id'],
                                model=row['model'],
                                capacity_nominal=row['capacity_nominal'],
                                voltage_nominal=row['voltage_nominal'],
                                location=row['location'],
                                installation_date=pd.to_datetime(row['installation_date']).date()
                            )
                            db.session.add(battery)
                
                else:
                    logger.error("サポートされていないテーブル", table_name=table_name)
                    return False
                
                db.session.commit()
                
                logger.info("CSVインポート完了", 
                          table=table_name,
                          csv_path=csv_path,
                          records=len(df))
                return True
                
        except Exception as e:
            logger.error("CSVインポートエラー", error=str(e))
            db.session.rollback()
            return False
    
    def optimize_database(self) -> bool:
        """データベース最適化"""
        try:
            with self.app.app_context():
                # SQLiteの場合
                if 'sqlite' in current_app.config['SQLALCHEMY_DATABASE_URI']:
                    db.session.execute('VACUUM')
                    db.session.execute('ANALYZE')
                    db.session.commit()
                    
                    logger.info("データベース最適化完了")
                    return True
                
                # PostgreSQLなどの場合
                else:
                    logger.info("データベース最適化はSQLiteのみサポート")
                    return False
                    
        except Exception as e:
            logger.error("データベース最適化エラー", error=str(e))
            return False

# グローバルインスタンス
db_manager = DatabaseManager()
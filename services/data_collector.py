"""
データ収集・処理サービス

センサーデータの収集、検証、データベース保存、
リアルタイム配信を行うメインデータ処理エンジン
"""

import json
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import asdict

from flask import current_app
from flask_socketio import emit
import structlog

from models.models import db, Battery, SensorData, Alert
from services.sensor_simulator import BatteryState, sensor_system

logger = structlog.get_logger()

class DataValidator:
    """データ検証クラス"""
    
    @staticmethod
    def validate_sensor_data(state: BatteryState) -> tuple[bool, float, List[str]]:
        """
        センサーデータの検証を行う
        
        Returns:
            tuple: (is_valid, quality_score, error_messages)
        """
        errors = []
        quality_score = 1.0
        
        # 電圧範囲チェック
        if not (2.5 <= state.voltage <= 4.5):
            errors.append(f"電圧異常: {state.voltage}V (範囲: 2.5-4.5V)")
            quality_score *= 0.5
        
        # 電流範囲チェック
        if abs(state.current) > 5.0:
            errors.append(f"電流異常: {state.current}A (範囲: -5.0~5.0A)")
            quality_score *= 0.7
        
        # 温度範囲チェック
        if not (-20 <= state.temperature <= 80):
            errors.append(f"温度異常: {state.temperature}°C (範囲: -20~80°C)")
            quality_score *= 0.6
        
        # 容量範囲チェック
        if not (0 <= state.capacity <= 100):
            errors.append(f"容量異常: {state.capacity}% (範囲: 0-100%)")
            quality_score *= 0.4
        
        # 電力整合性チェック
        expected_power = state.voltage * abs(state.current)
        power_diff = abs(state.power - expected_power) / max(expected_power, 0.1)
        if power_diff > 0.1:  # 10%以上の差
            errors.append(f"電力計算不整合: {state.power}W vs {expected_power}W")
            quality_score *= 0.8
        
        is_valid = len(errors) == 0 or quality_score > 0.5
        return is_valid, quality_score, errors

class AlertManager:
    """アラート管理クラス"""
    
    def __init__(self, app=None):
        self.app = app
        self.alert_callbacks: List[Callable] = []
        
        # アラート閾値（設定から取得）
        if app:
            with app.app_context():
                self.thresholds = current_app.config.get('ALERT_THRESHOLDS', {})
        else:
            self.thresholds = {
                'voltage_min': 3.0,
                'voltage_max': 4.2,
                'current_max': 3.0,
                'temperature_max': 60.0,
                'capacity_min': 20.0
            }
    
    def add_alert_callback(self, callback: Callable) -> None:
        """アラートコールバック追加"""
        self.alert_callbacks.append(callback)
    
    def check_alerts(self, state: BatteryState, battery_db_id: int) -> List[Alert]:
        """アラート条件チェック"""
        alerts = []
        
        # 電圧アラート
        if state.voltage < self.thresholds['voltage_min']:
            alerts.append(self._create_alert(
                battery_db_id, 'voltage', 'critical',
                '低電圧アラート', 
                f'電圧が危険レベルまで低下: {state.voltage}V',
                state.voltage, self.thresholds['voltage_min']
            ))
        elif state.voltage > self.thresholds['voltage_max']:
            alerts.append(self._create_alert(
                battery_db_id, 'voltage', 'warning',
                '過電圧アラート',
                f'電圧が高すぎます: {state.voltage}V',
                state.voltage, self.thresholds['voltage_max']
            ))
        
        # 電流アラート
        if abs(state.current) > self.thresholds['current_max']:
            alerts.append(self._create_alert(
                battery_db_id, 'current', 'warning',
                '過電流アラート',
                f'電流が過大: {state.current}A',
                abs(state.current), self.thresholds['current_max']
            ))
        
        # 温度アラート
        if state.temperature > self.thresholds['temperature_max']:
            severity = 'critical' if state.temperature > 70 else 'warning'
            alerts.append(self._create_alert(
                battery_db_id, 'temperature', severity,
                '高温アラート',
                f'温度が危険レベル: {state.temperature}°C',
                state.temperature, self.thresholds['temperature_max']
            ))
        
        # 容量アラート
        if state.capacity < self.thresholds['capacity_min']:
            severity = 'critical' if state.capacity < 10 else 'warning'
            alerts.append(self._create_alert(
                battery_db_id, 'capacity', severity,
                '低容量アラート',
                f'バッテリー残量低下: {state.capacity}%',
                state.capacity, self.thresholds['capacity_min']
            ))
        
        # 健康スコアアラート
        if state.health_score < 50:
            alerts.append(self._create_alert(
                battery_db_id, 'health', 'warning',
                'バッテリー劣化警告',
                f'健康スコア低下: {state.health_score}点',
                state.health_score, 50
            ))
        
        return alerts
    
    def _create_alert(self, battery_id: int, alert_type: str, severity: str,
                     title: str, message: str, sensor_value: float, 
                     threshold_value: float) -> Alert:
        """アラートオブジェクト作成"""
        return Alert(
            battery_id=battery_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            sensor_value=sensor_value,
            threshold_value=threshold_value,
            status='active',
            created_at=datetime.now(timezone.utc)
        )
    
    def process_alerts(self, alerts: List[Alert]) -> None:
        """アラート処理"""
        for alert in alerts:
            try:
                # データベース保存
                db.session.add(alert)
                db.session.commit()
                
                # コールバック実行
                for callback in self.alert_callbacks:
                    callback(alert)
                
                logger.info("アラート生成", 
                          alert_type=alert.alert_type,
                          severity=alert.severity,
                          message=alert.message)
                
            except Exception as e:
                logger.error("アラート処理エラー", error=str(e))
                db.session.rollback()

class DataCollector:
    """メインデータ収集クラス"""
    
    def __init__(self, app=None, socketio=None):
        self.app = app
        self.socketio = socketio
        self.is_running = False
        self.data_buffer: Dict[str, List[Dict]] = {}
        self.buffer_lock = threading.Lock()
        
        # コンポーネント初期化
        self.validator = DataValidator()
        self.alert_manager = AlertManager(app)
        
        # 統計情報
        self.stats = {
            'total_samples': 0,
            'valid_samples': 0,
            'alerts_generated': 0,
            'last_update': None
        }
    
    def initialize_batteries(self) -> None:
        """バッテリーデータベースの初期化"""
        if not self.app:
            return
            
        with self.app.app_context():
            try:
                # サンプルバッテリーの追加
                sample_batteries = [
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
                    }
                ]
                
                for battery_data in sample_batteries:
                    existing = Battery.query.filter_by(
                        battery_id=battery_data['battery_id']
                    ).first()
                    
                    if not existing:
                        battery = Battery(**battery_data)
                        db.session.add(battery)
                        logger.info("バッテリー追加", battery_id=battery_data['battery_id'])
                
                db.session.commit()
                
                # センサーシミュレーターにバッテリー追加
                for battery_data in sample_batteries:
                    if battery_data['battery_id'] not in sensor_system.simulators:
                        sensor_system.add_battery(
                            battery_data['battery_id'],
                            nominal_voltage=battery_data['voltage_nominal'],
                            nominal_capacity=battery_data['capacity_nominal']
                        )
                
            except Exception as e:
                logger.error("バッテリー初期化エラー", error=str(e))
                db.session.rollback()
    
    def start_collection(self) -> None:
        """データ収集開始"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # センサーシステムコールバック登録
        sensor_system.add_data_callback(self._process_sensor_data)
        
        # バッテリー初期化
        self.initialize_batteries()
        
        # センサーシミュレーション開始
        sensor_system.start_simulation()
        
        # データ保存スレッド開始
        threading.Thread(target=self._data_save_loop, daemon=True).start()
        
        logger.info("データ収集開始")
    
    def stop_collection(self) -> None:
        """データ収集停止"""
        self.is_running = False
        sensor_system.stop_simulation()
        logger.info("データ収集停止")
    
    def _process_sensor_data(self, states: List[BatteryState]) -> None:
        """センサーデータ処理"""
        if not self.is_running:
            return
        
        processed_data = []
        
        for state in states:
            try:
                # データ検証
                is_valid, quality_score, errors = self.validator.validate_sensor_data(state)
                
                if errors:
                    logger.warning("データ検証警告", 
                                 battery_id=state.battery_id,
                                 errors=errors)
                
                # データ変換
                data_dict = state.to_dict()
                data_dict.update({
                    'is_valid': is_valid,
                    'quality_score': quality_score,
                    'validation_errors': errors
                })
                
                processed_data.append(data_dict)
                
                # バッファに追加
                with self.buffer_lock:
                    if state.battery_id not in self.data_buffer:
                        self.data_buffer[state.battery_id] = []
                    self.data_buffer[state.battery_id].append(data_dict)
                
                # 統計更新
                self.stats['total_samples'] += 1
                if is_valid:
                    self.stats['valid_samples'] += 1
                self.stats['last_update'] = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error("データ処理エラー", 
                           battery_id=state.battery_id if state else 'unknown',
                           error=str(e))
        
        # リアルタイム配信
        if self.socketio and processed_data:
            self.socketio.emit('sensor_data', processed_data)
    
    def _data_save_loop(self) -> None:
        """データベース保存ループ"""
        while self.is_running:
            try:
                with self.buffer_lock:
                    buffer_copy = self.data_buffer.copy()
                    self.data_buffer.clear()
                
                if buffer_copy and self.app:
                    with self.app.app_context():
                        self._save_to_database(buffer_copy)
                
                time.sleep(5)  # 5秒ごとに保存
                
            except Exception as e:
                logger.error("データ保存ループエラー", error=str(e))
                time.sleep(1)
    
    def _save_to_database(self, buffer_data: Dict[str, List[Dict]]) -> None:
        """データベース保存"""
        try:
            for battery_id, data_list in buffer_data.items():
                # バッテリーID取得
                battery = Battery.query.filter_by(battery_id=battery_id).first()
                if not battery:
                    logger.warning("未知のバッテリーID", battery_id=battery_id)
                    continue
                
                for data in data_list:
                    # センサーデータ保存
                    sensor_data = SensorData(
                        battery_id=battery.id,
                        timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
                        voltage=data['voltage'],
                        current=data['current'],
                        temperature=data['temperature'],
                        capacity=data['capacity'],
                        power=data['power'],
                        internal_resistance=data['internal_resistance'],
                        cycle_count=data['cycle_count'],
                        is_valid=data['is_valid'],
                        quality_score=data['quality_score']
                    )
                    
                    db.session.add(sensor_data)
                    
                    # アラートチェック
                    if data['is_valid']:
                        state = BatteryState(
                            battery_id=battery_id,
                            timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
                            voltage=data['voltage'],
                            current=data['current'],
                            temperature=data['temperature'],
                            capacity=data['capacity'],
                            power=data['power'],
                            internal_resistance=data['internal_resistance'],
                            cycle_count=data['cycle_count'],
                            health_score=data['health_score'],
                            is_charging=data['is_charging']
                        )
                        
                        alerts = self.alert_manager.check_alerts(state, battery.id)
                        if alerts:
                            self.alert_manager.process_alerts(alerts)
                            self.stats['alerts_generated'] += len(alerts)
            
            db.session.commit()
            
        except Exception as e:
            logger.error("データベース保存エラー", error=str(e))
            db.session.rollback()
    
    def get_recent_data(self, battery_id: str, hours: int = 1) -> List[Dict]:
        """最近のデータ取得"""
        if not self.app:
            return []
        
        with self.app.app_context():
            try:
                battery = Battery.query.filter_by(battery_id=battery_id).first()
                if not battery:
                    return []
                
                since = datetime.now(timezone.utc) - timedelta(hours=hours)
                
                sensor_data = SensorData.query.filter(
                    SensorData.battery_id == battery.id,
                    SensorData.timestamp >= since
                ).order_by(SensorData.timestamp.desc()).limit(1000).all()
                
                return [
                    {
                        'timestamp': data.timestamp.isoformat(),
                        'voltage': data.voltage,
                        'current': data.current,
                        'temperature': data.temperature,
                        'capacity': data.capacity,
                        'power': data.power,
                        'internal_resistance': data.internal_resistance,
                        'cycle_count': data.cycle_count,
                        'is_valid': data.is_valid,
                        'quality_score': data.quality_score
                    }
                    for data in sensor_data
                ]
                
            except Exception as e:
                logger.error("データ取得エラー", error=str(e))
                return []
    
    def get_statistics(self) -> Dict:
        """システム統計情報取得"""
        return {
            **self.stats,
            'sensor_system': sensor_system.get_system_status(),
            'buffer_size': sum(len(data) for data in self.data_buffer.values())
        }

# グローバルインスタンス
data_collector = DataCollector()
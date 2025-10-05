"""
AI機械学習による予兆検知エンジン

リチウムイオンバッテリーの劣化・故障予測のための
機械学習モデル実装とリアルタイム予測機能
"""

import os
import pickle
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import (
    IsolationForest, RandomForestRegressor, 
    GradientBoostingClassifier
)
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_squared_error
from sklearn.cluster import DBSCAN
import structlog

from models.models import Battery, SensorData, Prediction

logger = structlog.get_logger()

@dataclass
class PredictionResult:
    """予測結果データクラス"""
    battery_id: str
    risk_level: str  # normal, warning, critical, danger
    confidence_score: float  # 0-1
    health_score: float  # 0-100
    predicted_failure_time: Optional[datetime]
    degradation_rate: float  # %/day
    remaining_cycles: int
    anomaly_flags: Dict[str, bool]
    explanation: str
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'battery_id': self.battery_id,
            'risk_level': self.risk_level,
            'confidence_score': round(self.confidence_score, 3),
            'health_score': round(self.health_score, 1),
            'predicted_failure_time': self.predicted_failure_time.isoformat() if self.predicted_failure_time else None,
            'degradation_rate': round(self.degradation_rate, 4),
            'remaining_cycles': self.remaining_cycles,
            'anomaly_flags': self.anomaly_flags,
            'explanation': self.explanation
        }

class FeatureExtractor:
    """特徴量抽出クラス"""
    
    @staticmethod
    def extract_statistical_features(data: pd.DataFrame) -> Dict[str, float]:
        """統計的特徴量の抽出"""
        features = {}
        
        for column in ['voltage', 'current', 'temperature', 'capacity', 'power']:
            if column in data.columns:
                values = data[column].dropna()
                if len(values) > 0:
                    features.update({
                        f'{column}_mean': values.mean(),
                        f'{column}_std': values.std(),
                        f'{column}_min': values.min(),
                        f'{column}_max': values.max(),
                        f'{column}_range': values.max() - values.min(),
                        f'{column}_cv': values.std() / values.mean() if values.mean() != 0 else 0,
                        f'{column}_skew': values.skew(),
                        f'{column}_kurtosis': values.kurtosis()
                    })
        
        return features
    
    @staticmethod
    def extract_temporal_features(data: pd.DataFrame) -> Dict[str, float]:
        """時系列特徴量の抽出"""
        features = {}
        
        if len(data) < 2:
            return features
        
        # データを時系列順にソート
        data = data.sort_values('timestamp')
        
        # 変化率特徴量
        for column in ['voltage', 'temperature', 'capacity']:
            if column in data.columns:
                values = data[column].dropna()
                if len(values) > 1:
                    # 1次差分（変化率）
                    diff = values.diff().dropna()
                    features.update({
                        f'{column}_diff_mean': diff.mean(),
                        f'{column}_diff_std': diff.std(),
                        f'{column}_trend': np.polyfit(range(len(values)), values, 1)[0] if len(values) > 2 else 0
                    })
        
        # サイクル特徴量
        if 'cycle_count' in data.columns:
            cycle_data = data['cycle_count'].dropna()
            if len(cycle_data) > 0:
                features['cycle_progression'] = cycle_data.iloc[-1] - cycle_data.iloc[0]
                features['cycle_rate'] = features['cycle_progression'] / len(cycle_data) if len(cycle_data) > 1 else 0
        
        # 充放電パターン特徴量
        if 'current' in data.columns:
            current = data['current'].dropna()
            if len(current) > 0:
                charge_time = len(current[current > 0.1])
                discharge_time = len(current[current < -0.1])
                total_time = len(current)
                
                features['charge_ratio'] = charge_time / total_time if total_time > 0 else 0
                features['discharge_ratio'] = discharge_time / total_time if total_time > 0 else 0
                features['idle_ratio'] = 1 - features['charge_ratio'] - features['discharge_ratio']
        
        return features
    
    @staticmethod
    def extract_physics_features(data: pd.DataFrame) -> Dict[str, float]:
        """物理的特徴量の抽出"""
        features = {}
        
        if len(data) == 0:
            return features
        
        # 内部抵抗解析
        if 'internal_resistance' in data.columns:
            resistance = data['internal_resistance'].dropna()
            if len(resistance) > 0:
                features['resistance_mean'] = resistance.mean()
                features['resistance_trend'] = np.polyfit(range(len(resistance)), resistance, 1)[0] if len(resistance) > 2 else 0
        
        # 電力効率解析
        if all(col in data.columns for col in ['voltage', 'current', 'power']):
            # 理論電力と実測電力の比較
            theoretical_power = data['voltage'] * data['current'].abs()
            actual_power = data['power']
            
            efficiency = actual_power / theoretical_power
            efficiency = efficiency.replace([np.inf, -np.inf], np.nan).dropna()
            
            if len(efficiency) > 0:
                features['power_efficiency_mean'] = efficiency.mean()
                features['power_efficiency_std'] = efficiency.std()
        
        # 温度-性能相関
        if all(col in data.columns for col in ['temperature', 'capacity']):
            temp_capacity_corr = data['temperature'].corr(data['capacity'])
            features['temp_capacity_correlation'] = temp_capacity_corr if not np.isnan(temp_capacity_corr) else 0
        
        return features

class AnomalyDetector:
    """異常検知クラス"""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train(self, training_data: pd.DataFrame) -> None:
        """異常検知モデルの訓練"""
        try:
            if len(training_data) < 10:
                logger.warning("訓練データが不十分", samples=len(training_data))
                return
            
            # 特徴量抽出
            feature_extractor = FeatureExtractor()
            
            features_list = []
            for i in range(len(training_data)):
                # ウィンドウサイズ50のデータを使用
                window_start = max(0, i - 49)
                window_data = training_data.iloc[window_start:i+1]
                
                if len(window_data) >= 5:  # 最小ウィンドウサイズ
                    stat_features = feature_extractor.extract_statistical_features(window_data)
                    temporal_features = feature_extractor.extract_temporal_features(window_data)
                    physics_features = feature_extractor.extract_physics_features(window_data)
                    
                    combined_features = {**stat_features, **temporal_features, **physics_features}
                    features_list.append(combined_features)
            
            if not features_list:
                logger.warning("特徴量抽出失敗")
                return
            
            # DataFrame作成
            features_df = pd.DataFrame(features_list)
            features_df = features_df.fillna(0)
            
            if features_df.empty:
                logger.warning("特徴量データが空")
                return
            
            # 正規化
            scaled_features = self.scaler.fit_transform(features_df)
            
            # 異常検知モデル訓練
            self.isolation_forest.fit(scaled_features)
            self.is_trained = True
            
            logger.info("異常検知モデル訓練完了", 
                       samples=len(features_df),
                       features=len(features_df.columns))
                       
        except Exception as e:
            logger.error("異常検知モデル訓練エラー", error=str(e))
    
    def detect_anomalies(self, data: pd.DataFrame) -> Dict[str, Any]:
        """異常検知実行"""
        if not self.is_trained:
            return {'is_anomaly': False, 'anomaly_score': 0.0, 'anomaly_flags': {}}
        
        try:
            feature_extractor = FeatureExtractor()
            
            # 特徴量抽出
            stat_features = feature_extractor.extract_statistical_features(data)
            temporal_features = feature_extractor.extract_temporal_features(data)
            physics_features = feature_extractor.extract_physics_features(data)
            
            combined_features = {**stat_features, **temporal_features, **physics_features}
            
            if not combined_features:
                return {'is_anomaly': False, 'anomaly_score': 0.0, 'anomaly_flags': {}}
            
            # DataFrame作成と正規化
            features_df = pd.DataFrame([combined_features])
            features_df = features_df.fillna(0)
            
            # 不足する特徴量を0で埋める
            expected_features = self.scaler.feature_names_in_ if hasattr(self.scaler, 'feature_names_in_') else []
            for feature in expected_features:
                if feature not in features_df.columns:
                    features_df[feature] = 0
            
            # 余分な特徴量を削除
            features_df = features_df[expected_features] if expected_features else features_df
            
            scaled_features = self.scaler.transform(features_df)
            
            # 異常スコア計算
            anomaly_score = self.isolation_forest.decision_function(scaled_features)[0]
            is_anomaly = self.isolation_forest.predict(scaled_features)[0] == -1
            
            # 詳細な異常フラグ
            anomaly_flags = self._analyze_anomaly_details(data, combined_features)
            
            return {
                'is_anomaly': is_anomaly,
                'anomaly_score': float(anomaly_score),
                'anomaly_flags': anomaly_flags
            }
            
        except Exception as e:
            logger.error("異常検知実行エラー", error=str(e))
            return {'is_anomaly': False, 'anomaly_score': 0.0, 'anomaly_flags': {}}
    
    def _analyze_anomaly_details(self, data: pd.DataFrame, features: Dict) -> Dict[str, bool]:
        """詳細な異常フラグの分析"""
        flags = {}
        
        # 電圧異常
        if 'voltage_mean' in features:
            flags['voltage_anomaly'] = features['voltage_mean'] < 3.0 or features['voltage_mean'] > 4.3
        
        # 温度異常
        if 'temperature_mean' in features:
            flags['temperature_anomaly'] = features['temperature_mean'] > 60 or features['temperature_mean'] < -10
        
        # 容量異常
        if 'capacity_mean' in features:
            flags['capacity_anomaly'] = features['capacity_mean'] < 10
        
        # 急激な変化
        if 'voltage_diff_std' in features:
            flags['voltage_instability'] = features['voltage_diff_std'] > 0.1
        
        if 'temperature_diff_std' in features:
            flags['temperature_instability'] = features['temperature_diff_std'] > 5.0
        
        # 内部抵抗異常
        if 'resistance_mean' in features:
            flags['resistance_anomaly'] = features['resistance_mean'] > 0.2
        
        return flags

class DegradationPredictor:
    """劣化予測クラス"""
    
    def __init__(self):
        self.health_model = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            max_depth=10
        )
        self.risk_classifier = GradientBoostingClassifier(
            n_estimators=100,
            random_state=42,
            learning_rate=0.1
        )
        self.scaler = RobustScaler()
        self.is_trained = False
    
    def train(self, training_data: List[Dict]) -> None:
        """劣化予測モデルの訓練"""
        try:
            if len(training_data) < 50:
                logger.warning("劣化予測訓練データ不足", samples=len(training_data))
                return
            
            # 合成データ生成（実際のシステムでは履歴データを使用）
            synthetic_data = self._generate_synthetic_training_data()
            training_data.extend(synthetic_data)
            
            df = pd.DataFrame(training_data)
            
            # 特徴量とラベル準備
            feature_columns = [
                'voltage_mean', 'voltage_std', 'current_mean', 'current_std',
                'temperature_mean', 'temperature_std', 'capacity_mean',
                'power_mean', 'internal_resistance', 'cycle_count'
            ]
            
            # 不足する列を0で埋める
            for col in feature_columns:
                if col not in df.columns:
                    df[col] = 0
            
            X = df[feature_columns].fillna(0)
            
            # ヘルススコア回帰用ターゲット
            y_health = df.get('health_score', 100 - df['cycle_count'] * 0.01).fillna(90)
            
            # リスク分類用ターゲット
            y_risk = pd.cut(y_health, 
                          bins=[0, 50, 70, 85, 100], 
                          labels=['danger', 'critical', 'warning', 'normal']).astype(str)
            
            # 訓練・テスト分割
            X_train, X_test, y_health_train, y_health_test, y_risk_train, y_risk_test = train_test_split(
                X, y_health, y_risk, test_size=0.2, random_state=42
            )
            
            # 正規化
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # モデル訓練
            self.health_model.fit(X_train_scaled, y_health_train)
            self.risk_classifier.fit(X_train_scaled, y_risk_train)
            
            # 性能評価
            health_pred = self.health_model.predict(X_test_scaled)
            risk_pred = self.risk_classifier.predict(X_test_scaled)
            
            health_rmse = np.sqrt(mean_squared_error(y_health_test, health_pred))
            
            self.is_trained = True
            
            logger.info("劣化予測モデル訓練完了",
                       samples=len(X_train),
                       health_rmse=health_rmse,
                       risk_accuracy=self.risk_classifier.score(X_test_scaled, y_risk_test))
                       
        except Exception as e:
            logger.error("劣化予測モデル訓練エラー", error=str(e))
    
    def predict(self, features: Dict) -> Dict:
        """劣化予測実行"""
        if not self.is_trained:
            # デフォルト予測
            return {
                'health_score': 90.0,
                'risk_level': 'normal',
                'confidence_score': 0.5,
                'degradation_rate': 0.01,
                'remaining_cycles': 1000
            }
        
        try:
            # 特徴量準備
            feature_columns = [
                'voltage_mean', 'voltage_std', 'current_mean', 'current_std',
                'temperature_mean', 'temperature_std', 'capacity_mean',
                'power_mean', 'internal_resistance', 'cycle_count'
            ]
            
            feature_values = []
            for col in feature_columns:
                feature_values.append(features.get(col, 0))
            
            X = np.array([feature_values])
            X_scaled = self.scaler.transform(X)
            
            # 予測実行
            health_score = self.health_model.predict(X_scaled)[0]
            risk_level = self.risk_classifier.predict(X_scaled)[0]
            confidence_score = np.max(self.risk_classifier.predict_proba(X_scaled)[0])
            
            # 劣化率計算
            current_cycles = features.get('cycle_count', 0)
            degradation_rate = max(0.001, (100 - health_score) / max(current_cycles, 1) / 365)
            
            # 残存サイクル計算
            remaining_cycles = max(0, int((health_score - 50) / max(degradation_rate * 365, 0.01)))
            
            return {
                'health_score': max(0, min(100, health_score)),
                'risk_level': risk_level,
                'confidence_score': confidence_score,
                'degradation_rate': degradation_rate,
                'remaining_cycles': remaining_cycles
            }
            
        except Exception as e:
            logger.error("劣化予測実行エラー", error=str(e))
            return {
                'health_score': 90.0,
                'risk_level': 'normal',
                'confidence_score': 0.5,
                'degradation_rate': 0.01,
                'remaining_cycles': 1000
            }
    
    def _generate_synthetic_training_data(self) -> List[Dict]:
        """合成訓練データ生成"""
        data = []
        
        for i in range(1000):
            cycle = np.random.randint(0, 2000)
            base_degradation = cycle * 0.01
            
            # バッテリー特性のバリエーション
            voltage_mean = 3.7 + np.random.normal(0, 0.1)
            current_mean = np.random.uniform(-2, 2)
            temp_mean = 25 + np.random.normal(0, 10)
            capacity_mean = max(0, 100 - base_degradation + np.random.normal(0, 5))
            
            # 異常パターン追加
            if np.random.random() < 0.1:  # 10%の異常データ
                if np.random.random() < 0.5:
                    temp_mean += np.random.uniform(20, 40)  # 過熱
                else:
                    voltage_mean *= 0.8  # 電圧低下
            
            health_score = max(50, min(100, 100 - base_degradation + np.random.normal(0, 5)))
            
            data.append({
                'voltage_mean': voltage_mean,
                'voltage_std': np.random.uniform(0.01, 0.1),
                'current_mean': current_mean,
                'current_std': np.random.uniform(0.1, 0.5),
                'temperature_mean': temp_mean,
                'temperature_std': np.random.uniform(0.5, 3.0),
                'capacity_mean': capacity_mean,
                'power_mean': abs(voltage_mean * current_mean),
                'internal_resistance': 0.05 + cycle * 0.00001 + np.random.normal(0, 0.01),
                'cycle_count': cycle,
                'health_score': health_score
            })
        
        return data

class MLPredictor:
    """メイン機械学習予測クラス"""
    
    def __init__(self, app=None):
        self.app = app
        self.anomaly_detector = AnomalyDetector()
        self.degradation_predictor = DegradationPredictor()
        self.feature_extractor = FeatureExtractor()
        
        self.model_version = "v1.0.0"
        self.last_training_time = None
        self.prediction_cache = {}
    
    def initialize_models(self) -> None:
        """モデル初期化"""
        try:
            # 既存のモデルファイルを読み込み（あれば）
            self._load_models()
            
            # モデルが未訓練の場合は初期訓練実行
            if not (self.anomaly_detector.is_trained and self.degradation_predictor.is_trained):
                self._perform_initial_training()
                self._save_models()
            
            logger.info("ML予測モデル初期化完了")
            
        except Exception as e:
            logger.error("ML予測モデル初期化エラー", error=str(e))
    
    def predict_battery_health(self, battery_id: str, 
                              recent_data: Optional[List[Dict]] = None) -> PredictionResult:
        """バッテリー健康状態予測"""
        try:
            # データ取得
            if recent_data is None:
                recent_data = self._get_recent_sensor_data(battery_id)
            
            if not recent_data:
                return self._default_prediction(battery_id)
            
            # DataFrame変換
            df = pd.DataFrame(recent_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 特徴量抽出
            stat_features = self.feature_extractor.extract_statistical_features(df)
            temporal_features = self.feature_extractor.extract_temporal_features(df)
            physics_features = self.feature_extractor.extract_physics_features(df)
            
            combined_features = {**stat_features, **temporal_features, **physics_features}
            
            # 異常検知
            anomaly_result = self.anomaly_detector.detect_anomalies(df)
            
            # 劣化予測
            degradation_result = self.degradation_predictor.predict(combined_features)
            
            # 故障時期予測
            failure_time = self._predict_failure_time(degradation_result)
            
            # 説明文生成
            explanation = self._generate_explanation(
                anomaly_result, degradation_result, combined_features
            )
            
            # 結果作成
            result = PredictionResult(
                battery_id=battery_id,
                risk_level=degradation_result['risk_level'],
                confidence_score=degradation_result['confidence_score'],
                health_score=degradation_result['health_score'],
                predicted_failure_time=failure_time,
                degradation_rate=degradation_result['degradation_rate'],
                remaining_cycles=degradation_result['remaining_cycles'],
                anomaly_flags=anomaly_result['anomaly_flags'],
                explanation=explanation
            )
            
            # キャッシュに保存
            self.prediction_cache[battery_id] = result
            
            return result
            
        except Exception as e:
            logger.error("バッテリー予測エラー", battery_id=battery_id, error=str(e))
            return self._default_prediction(battery_id)
    
    def retrain_models(self) -> bool:
        """モデル再訓練"""
        try:
            if not self.app:
                return False
            
            with self.app.app_context():
                # 過去30日のデータを取得
                since = datetime.now(timezone.utc) - timedelta(days=30)
                
                training_data = []
                batteries = Battery.query.all()
                
                for battery in batteries:
                    sensor_data = SensorData.query.filter(
                        SensorData.battery_id == battery.id,
                        SensorData.timestamp >= since,
                        SensorData.is_valid == True
                    ).all()
                    
                    if len(sensor_data) > 100:  # 十分なデータがある場合
                        df = pd.DataFrame([{
                            'timestamp': data.timestamp,
                            'voltage': data.voltage,
                            'current': data.current,
                            'temperature': data.temperature,
                            'capacity': data.capacity,
                            'power': data.power,
                            'internal_resistance': data.internal_resistance,
                            'cycle_count': data.cycle_count
                        } for data in sensor_data])
                        
                        # 異常検知用データ
                        self.anomaly_detector.train(df)
                        
                        # 劣化予測用データ
                        features = self.feature_extractor.extract_statistical_features(df)
                        features.update(self.feature_extractor.extract_temporal_features(df))
                        features.update(self.feature_extractor.extract_physics_features(df))
                        training_data.append(features)
                
                # 劣化予測モデル訓練
                if training_data:
                    self.degradation_predictor.train(training_data)
                
                # モデル保存
                self._save_models()
                self.last_training_time = datetime.now(timezone.utc)
                
                logger.info("モデル再訓練完了", 
                          batteries_count=len(batteries),
                          training_samples=len(training_data))
                return True
                
        except Exception as e:
            logger.error("モデル再訓練エラー", error=str(e))
            return False
    
    def _get_recent_sensor_data(self, battery_id: str, hours: int = 24) -> List[Dict]:
        """最近のセンサーデータ取得"""
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
                    SensorData.timestamp >= since,
                    SensorData.is_valid == True
                ).order_by(SensorData.timestamp.desc()).limit(500).all()
                
                return [{
                    'timestamp': data.timestamp.isoformat(),
                    'voltage': data.voltage,
                    'current': data.current,
                    'temperature': data.temperature,
                    'capacity': data.capacity,
                    'power': data.power,
                    'internal_resistance': data.internal_resistance,
                    'cycle_count': data.cycle_count
                } for data in sensor_data]
                
            except Exception as e:
                logger.error("センサーデータ取得エラー", error=str(e))
                return []
    
    def _default_prediction(self, battery_id: str) -> PredictionResult:
        """デフォルト予測結果"""
        return PredictionResult(
            battery_id=battery_id,
            risk_level='normal',
            confidence_score=0.5,
            health_score=90.0,
            predicted_failure_time=None,
            degradation_rate=0.01,
            remaining_cycles=1000,
            anomaly_flags={},
            explanation="データ不足のため、デフォルト予測を使用"
        )
    
    def _predict_failure_time(self, degradation_result: Dict) -> Optional[datetime]:
        """故障時期予測"""
        try:
            health_score = degradation_result['health_score']
            degradation_rate = degradation_result['degradation_rate']
            
            if degradation_rate > 0 and health_score > 50:
                days_to_failure = (health_score - 50) / (degradation_rate * 365)
                if days_to_failure > 0:
                    return datetime.now(timezone.utc) + timedelta(days=days_to_failure)
            
            return None
            
        except Exception:
            return None
    
    def _generate_explanation(self, anomaly_result: Dict, 
                            degradation_result: Dict, 
                            features: Dict) -> str:
        """予測説明文生成"""
        explanations = []
        
        health_score = degradation_result['health_score']
        risk_level = degradation_result['risk_level']
        
        # 健康状態説明
        if health_score >= 80:
            explanations.append("バッテリー状態は良好です。")
        elif health_score >= 60:
            explanations.append("軽度の劣化が見られます。")
        elif health_score >= 40:
            explanations.append("明らかな劣化が進行しています。")
        else:
            explanations.append("重度の劣化状態です。交換を検討してください。")
        
        # 異常フラグ説明
        anomaly_flags = anomaly_result.get('anomaly_flags', {})
        if anomaly_flags.get('temperature_anomaly'):
            explanations.append("高温異常が検出されています。")
        if anomaly_flags.get('voltage_anomaly'):
            explanations.append("電圧異常が検出されています。")
        if anomaly_flags.get('capacity_anomaly'):
            explanations.append("容量異常が検出されています。")
        
        # 劣化率説明
        degradation_rate = degradation_result['degradation_rate']
        if degradation_rate > 0.05:
            explanations.append("劣化速度が早いです。")
        elif degradation_rate > 0.02:
            explanations.append("通常の劣化速度です。")
        else:
            explanations.append("劣化速度は遅いです。")
        
        return " ".join(explanations)
    
    def _perform_initial_training(self) -> None:
        """初期訓練実行"""
        logger.info("初期モデル訓練開始")
        
        # 合成データによる初期訓練
        synthetic_data = self.degradation_predictor._generate_synthetic_training_data()
        self.degradation_predictor.train(synthetic_data)
        
        # 異常検知用の初期データ
        df = pd.DataFrame(synthetic_data[:500])  # 正常データのみ使用
        self.anomaly_detector.train(df)
    
    def _save_models(self) -> None:
        """モデル保存"""
        try:
            model_dir = 'models/saved'
            os.makedirs(model_dir, exist_ok=True)
            
            # 異常検知モデル保存
            with open(f'{model_dir}/anomaly_detector.pkl', 'wb') as f:
                pickle.dump({
                    'isolation_forest': self.anomaly_detector.isolation_forest,
                    'scaler': self.anomaly_detector.scaler,
                    'is_trained': self.anomaly_detector.is_trained
                }, f)
            
            # 劣化予測モデル保存
            with open(f'{model_dir}/degradation_predictor.pkl', 'wb') as f:
                pickle.dump({
                    'health_model': self.degradation_predictor.health_model,
                    'risk_classifier': self.degradation_predictor.risk_classifier,
                    'scaler': self.degradation_predictor.scaler,
                    'is_trained': self.degradation_predictor.is_trained
                }, f)
            
            # メタデータ保存
            metadata = {
                'model_version': self.model_version,
                'training_time': datetime.now(timezone.utc).isoformat(),
                'feature_extractor': 'FeatureExtractor_v1.0'
            }
            
            with open(f'{model_dir}/metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("モデル保存完了")
            
        except Exception as e:
            logger.error("モデル保存エラー", error=str(e))
    
    def _load_models(self) -> None:
        """モデル読み込み"""
        try:
            model_dir = 'models/saved'
            
            # 異常検知モデル読み込み
            anomaly_path = f'{model_dir}/anomaly_detector.pkl'
            if os.path.exists(anomaly_path):
                with open(anomaly_path, 'rb') as f:
                    anomaly_data = pickle.load(f)
                
                self.anomaly_detector.isolation_forest = anomaly_data['isolation_forest']
                self.anomaly_detector.scaler = anomaly_data['scaler']
                self.anomaly_detector.is_trained = anomaly_data['is_trained']
            
            # 劣化予測モデル読み込み
            degradation_path = f'{model_dir}/degradation_predictor.pkl'
            if os.path.exists(degradation_path):
                with open(degradation_path, 'rb') as f:
                    degradation_data = pickle.load(f)
                
                self.degradation_predictor.health_model = degradation_data['health_model']
                self.degradation_predictor.risk_classifier = degradation_data['risk_classifier']
                self.degradation_predictor.scaler = degradation_data['scaler']
                self.degradation_predictor.is_trained = degradation_data['is_trained']
            
            # メタデータ読み込み
            metadata_path = f'{model_dir}/metadata.json'
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                self.model_version = metadata.get('model_version', self.model_version)
                self.last_training_time = metadata.get('training_time')
            
            logger.info("モデル読み込み完了", version=self.model_version)
            
        except Exception as e:
            logger.error("モデル読み込みエラー", error=str(e))

# グローバルインスタンス
ml_predictor = MLPredictor()
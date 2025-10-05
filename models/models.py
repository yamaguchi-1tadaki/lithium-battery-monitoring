"""
データベースモデル定義
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import Index

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """ユーザーモデル"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Battery(db.Model):
    """バッテリーモデル"""
    __tablename__ = 'batteries'
    
    id = db.Column(db.Integer, primary_key=True)
    battery_id = db.Column(db.String(50), unique=True, nullable=False)  # 一意識別子
    model = db.Column(db.String(100), nullable=False)  # バッテリー型番
    capacity_nominal = db.Column(db.Float, nullable=False)  # 公称容量 (Ah)
    voltage_nominal = db.Column(db.Float, nullable=False)  # 公称電圧 (V)
    location = db.Column(db.String(200))  # 設置場所
    installation_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, maintenance, retired
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # リレーションシップ
    sensor_data = db.relationship('SensorData', backref='battery', lazy='dynamic', cascade='all, delete-orphan')
    predictions = db.relationship('Prediction', backref='battery', lazy='dynamic', cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='battery', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Battery {self.battery_id} - {self.model}>'

class SensorData(db.Model):
    """センサーデータモデル"""
    __tablename__ = 'sensor_data'
    
    id = db.Column(db.Integer, primary_key=True)
    battery_id = db.Column(db.Integer, db.ForeignKey('batteries.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # センサー測定値
    voltage = db.Column(db.Float, nullable=False)      # 電圧 (V)
    current = db.Column(db.Float, nullable=False)      # 電流 (A)
    temperature = db.Column(db.Float, nullable=False)  # 温度 (°C)
    capacity = db.Column(db.Float, nullable=False)     # 残量 (%)
    
    # 計算値
    power = db.Column(db.Float)                        # 電力 (W)
    internal_resistance = db.Column(db.Float)          # 内部抵抗 (Ω)
    cycle_count = db.Column(db.Integer, default=0)     # 充放電サイクル数
    
    # データ品質フラグ
    is_valid = db.Column(db.Boolean, default=True)
    quality_score = db.Column(db.Float, default=1.0)   # データ品質スコア (0-1)
    
    def __repr__(self):
        return f'<SensorData {self.battery_id} @ {self.timestamp}>'
    
    # インデックス定義
    __table_args__ = (
        Index('idx_sensor_data_battery_timestamp', 'battery_id', 'timestamp'),
        Index('idx_sensor_data_timestamp', 'timestamp'),
    )

class Prediction(db.Model):
    """予測結果モデル"""
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    battery_id = db.Column(db.Integer, db.ForeignKey('batteries.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # 予測結果
    risk_level = db.Column(db.String(20), nullable=False)  # normal, warning, critical, danger
    confidence_score = db.Column(db.Float, nullable=False)  # 信頼度 (0-1)
    predicted_failure_time = db.Column(db.DateTime)  # 故障予測時刻
    health_score = db.Column(db.Float)  # バッテリー健康度 (0-100)
    
    # 詳細分析結果
    degradation_rate = db.Column(db.Float)  # 劣化率 (%/日)
    remaining_cycles = db.Column(db.Integer)  # 残り充放電サイクル数
    anomaly_flags = db.Column(db.Text)  # JSON形式の異常フラグ
    
    # メタデータ
    model_version = db.Column(db.String(50))  # 使用したMLモデルバージョン
    data_points_used = db.Column(db.Integer)  # 予測に使用したデータポイント数
    
    def __repr__(self):
        return f'<Prediction {self.battery_id} - {self.risk_level} @ {self.created_at}>'
    
    # インデックス定義
    __table_args__ = (
        Index('idx_predictions_battery_created', 'battery_id', 'created_at'),
    )

class Alert(db.Model):
    """アラートモデル"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    battery_id = db.Column(db.Integer, db.ForeignKey('batteries.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # アラート情報
    alert_type = db.Column(db.String(50), nullable=False)  # voltage, current, temperature, prediction
    severity = db.Column(db.String(20), nullable=False)    # info, warning, error, critical
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    
    # 状態管理
    status = db.Column(db.String(20), default='active')    # active, acknowledged, resolved
    acknowledged_at = db.Column(db.DateTime)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)
    
    # 関連データ
    sensor_value = db.Column(db.Float)  # トリガーとなったセンサー値
    threshold_value = db.Column(db.Float)  # 閾値
    
    def __repr__(self):
        return f'<Alert {self.alert_type} - {self.severity} @ {self.created_at}>'
    
    # インデックス定義
    __table_args__ = (
        Index('idx_alerts_battery_created', 'battery_id', 'created_at'),
        Index('idx_alerts_status_severity', 'status', 'severity'),
    )

class SystemLog(db.Model):
    """システムログモデル"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    level = db.Column(db.String(10), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    module = db.Column(db.String(100))  # ログを出力したモジュール名
    message = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 関連ユーザー（あれば）
    
    # 追加情報（JSON形式）
    extra_data = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SystemLog {self.level} @ {self.timestamp}>'
    
    # インデックス定義
    __table_args__ = (
        Index('idx_system_logs_timestamp', 'timestamp'),
        Index('idx_system_logs_level', 'level'),
    )
"""
バッテリー監視システム設定ファイル
"""
import os
from datetime import timedelta

class Config:
    """基本設定クラス"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # データベース設定
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///battery_monitor.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # 開発時のみTrue
    
    # Flask-Login設定
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    
    # SocketIO設定
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # センシング設定
    SENSOR_UPDATE_INTERVAL = 1.0  # 秒
    DATA_RETENTION_DAYS = 30
    
    # アラート設定
    ALERT_THRESHOLDS = {
        'voltage_min': 3.0,      # V
        'voltage_max': 4.2,      # V
        'current_max': 3.0,      # A
        'temperature_max': 60.0, # °C
        'capacity_min': 20.0     # %
    }
    
    # ML設定
    MODEL_RETRAIN_INTERVAL = 24  # 時間
    PREDICTION_WINDOW = 100      # データポイント数
    
    # ログ設定
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/battery_monitor.log'

class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    LOG_LEVEL = 'WARNING'

class TestConfig(Config):
    """テスト環境設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# 設定の選択
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}
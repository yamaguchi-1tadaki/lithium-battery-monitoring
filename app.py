"""
リチウムイオンバッテリー監視システム メインアプリケーション

Flask + SocketIOによるリアルタイム監視システム
"""

import os
import json
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import structlog

# アプリケーション設定
from config.config import config
from models.models import db, User, Battery, SensorData, Alert, Prediction
from services.data_collector import data_collector
from services.ml_predictor import ml_predictor
from services.sensor_simulator import sensor_system

# ログ設定
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

def create_app(config_name='development'):
    """アプリケーションファクトリー"""
    app = Flask(__name__)
    
    # 設定読み込み
    app.config.from_object(config[config_name])
    
    # 拡張機能初期化
    db.init_app(app)
    
    # Flask-Login設定
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'ログインが必要です。'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # SocketIO設定
    socketio = SocketIO(app, 
                       cors_allowed_origins="*",
                       async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading'))
    
    # データベース初期化
    with app.app_context():
        db.create_all()
        
        # デフォルト管理者ユーザーの作成
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@battery-monitor.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            logger.info("デフォルト管理者ユーザー作成", username='admin')
    
    # サービス初期化
    data_collector.app = app
    data_collector.socketio = socketio
    ml_predictor.app = app
    
    # ML予測モデル初期化
    ml_predictor.initialize_models()
    
    # ルート登録
    register_routes(app)
    register_socketio_events(socketio)
    
    return app, socketio

def register_routes(app):
    """ルート登録"""
    
    @app.route('/')
    def index():
        """メインダッシュボード"""
        return render_template('dashboard.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """ログイン"""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                user.last_login = datetime.now(timezone.utc)
                db.session.commit()
                
                logger.info("ユーザーログイン", username=username)
                return redirect(url_for('index'))
            else:
                flash('ユーザー名またはパスワードが間違っています。')
        
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        """ログアウト"""
        logger.info("ユーザーログアウト", username=current_user.username)
        logout_user()
        return redirect(url_for('login'))
    
    @app.route('/admin')
    @login_required
    def admin_dashboard():
        """管理画面"""
        if not current_user.is_admin:
            flash('管理者権限が必要です。')
            return redirect(url_for('index'))
        
        return render_template('admin/dashboard.html')
    
    # API エンドポイント
    @app.route('/api/batteries')
    @login_required
    def api_batteries():
        """バッテリー一覧取得"""
        try:
            batteries = Battery.query.all()
            result = []
            
            for battery in batteries:
                # 最新のセンサーデータ取得
                latest_data = SensorData.query.filter_by(
                    battery_id=battery.id
                ).order_by(SensorData.timestamp.desc()).first()
                
                # 最新のアラート取得
                latest_alert = Alert.query.filter_by(
                    battery_id=battery.id,
                    status='active'
                ).order_by(Alert.created_at.desc()).first()
                
                # 最新の予測結果取得
                latest_prediction = Prediction.query.filter_by(
                    battery_id=battery.id
                ).order_by(Prediction.created_at.desc()).first()
                
                battery_info = {
                    'id': battery.id,
                    'battery_id': battery.battery_id,
                    'model': battery.model,
                    'location': battery.location,
                    'status': battery.status,
                    'installation_date': battery.installation_date.isoformat(),
                    'latest_data': {
                        'voltage': latest_data.voltage if latest_data else None,
                        'current': latest_data.current if latest_data else None,
                        'temperature': latest_data.temperature if latest_data else None,
                        'capacity': latest_data.capacity if latest_data else None,
                        'timestamp': latest_data.timestamp.isoformat() if latest_data else None
                    },
                    'alert_status': latest_alert.severity if latest_alert else 'normal',
                    'health_score': latest_prediction.health_score if latest_prediction else None,
                    'risk_level': latest_prediction.risk_level if latest_prediction else 'normal'
                }
                
                result.append(battery_info)
            
            return jsonify({'success': True, 'batteries': result})
            
        except Exception as e:
            logger.error("バッテリー一覧取得エラー", error=str(e))
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/battery/<battery_id>/data')
    @login_required
    def api_battery_data(battery_id):
        """特定バッテリーのデータ取得"""
        try:
            hours = request.args.get('hours', 1, type=int)
            recent_data = data_collector.get_recent_data(battery_id, hours)
            
            return jsonify({
                'success': True,
                'battery_id': battery_id,
                'data': recent_data
            })
            
        except Exception as e:
            logger.error("バッテリーデータ取得エラー", battery_id=battery_id, error=str(e))
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/battery/<battery_id>/predict')
    @login_required
    def api_battery_predict(battery_id):
        """バッテリー予測結果取得"""
        try:
            prediction = ml_predictor.predict_battery_health(battery_id)
            
            # 予測結果をデータベースに保存
            battery = Battery.query.filter_by(battery_id=battery_id).first()
            if battery:
                prediction_record = Prediction(
                    battery_id=battery.id,
                    risk_level=prediction.risk_level,
                    confidence_score=prediction.confidence_score,
                    predicted_failure_time=prediction.predicted_failure_time,
                    health_score=prediction.health_score,
                    degradation_rate=prediction.degradation_rate,
                    remaining_cycles=prediction.remaining_cycles,
                    anomaly_flags=json.dumps(prediction.anomaly_flags),
                    model_version=ml_predictor.model_version,
                    data_points_used=100  # 仮の値
                )
                
                db.session.add(prediction_record)
                db.session.commit()
            
            return jsonify({
                'success': True,
                'prediction': prediction.to_dict()
            })
            
        except Exception as e:
            logger.error("バッテリー予測エラー", battery_id=battery_id, error=str(e))
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/alerts')
    @login_required
    def api_alerts():
        """アラート一覧取得"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            status = request.args.get('status', 'active')
            
            query = Alert.query.filter_by(status=status)
            alerts_pagination = query.order_by(Alert.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            alerts_data = []
            for alert in alerts_pagination.items:
                battery = Battery.query.get(alert.battery_id)
                alerts_data.append({
                    'id': alert.id,
                    'battery_id': battery.battery_id if battery else 'Unknown',
                    'battery_location': battery.location if battery else 'Unknown',
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                    'message': alert.message,
                    'created_at': alert.created_at.isoformat(),
                    'status': alert.status,
                    'sensor_value': alert.sensor_value,
                    'threshold_value': alert.threshold_value
                })
            
            return jsonify({
                'success': True,
                'alerts': alerts_data,
                'pagination': {
                    'page': page,
                    'pages': alerts_pagination.pages,
                    'per_page': per_page,
                    'total': alerts_pagination.total,
                    'has_next': alerts_pagination.has_next,
                    'has_prev': alerts_pagination.has_prev
                }
            })
            
        except Exception as e:
            logger.error("アラート取得エラー", error=str(e))
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/system/status')
    @login_required
    def api_system_status():
        """システムステータス取得"""
        try:
            stats = data_collector.get_statistics()
            
            return jsonify({
                'success': True,
                'system_status': {
                    'data_collection': data_collector.is_running,
                    'sensor_simulation': sensor_system.is_running,
                    'ml_models_trained': (
                        ml_predictor.anomaly_detector.is_trained and 
                        ml_predictor.degradation_predictor.is_trained
                    ),
                    'total_batteries': Battery.query.count(),
                    'active_alerts': Alert.query.filter_by(status='active').count(),
                    'data_stats': stats
                }
            })
            
        except Exception as e:
            logger.error("システムステータス取得エラー", error=str(e))
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/system/control', methods=['POST'])
    @login_required
    def api_system_control():
        """システム制御"""
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': '管理者権限が必要です'}), 403
        
        try:
            action = request.json.get('action')
            
            if action == 'start_collection':
                data_collector.start_collection()
                message = "データ収集を開始しました"
            elif action == 'stop_collection':
                data_collector.stop_collection()
                message = "データ収集を停止しました"
            elif action == 'retrain_models':
                success = ml_predictor.retrain_models()
                message = "モデル再訓練が完了しました" if success else "モデル再訓練に失敗しました"
            elif action == 'inject_scenario':
                scenario = request.json.get('scenario', 'high_temp_stress')
                sensor_system.inject_scenario(scenario)
                message = f"シナリオ '{scenario}' を実行しました"
            else:
                return jsonify({'success': False, 'error': '無効なアクション'}), 400
            
            logger.info("システム制御実行", action=action, user=current_user.username)
            return jsonify({'success': True, 'message': message})
            
        except Exception as e:
            logger.error("システム制御エラー", error=str(e))
            return jsonify({'success': False, 'error': str(e)}), 500

def register_socketio_events(socketio):
    """SocketIOイベント登録"""
    
    @socketio.on('connect')
    def on_connect():
        """クライアント接続"""
        if current_user.is_authenticated:
            join_room('authenticated')
            logger.info("SocketIO接続", user=current_user.username)
            emit('status', {'message': 'リアルタイム監視に接続しました'})
        else:
            emit('error', {'message': '認証が必要です'})
    
    @socketio.on('disconnect')
    def on_disconnect():
        """クライアント切断"""
        if current_user.is_authenticated:
            leave_room('authenticated')
            logger.info("SocketIO切断", user=current_user.username)
    
    @socketio.on('join_battery')
    def on_join_battery(data):
        """特定バッテリーの監視開始"""
        if current_user.is_authenticated:
            battery_id = data.get('battery_id')
            join_room(f'battery_{battery_id}')
            emit('status', {'message': f'バッテリー {battery_id} の監視を開始しました'})
    
    @socketio.on('leave_battery')
    def on_leave_battery(data):
        """特定バッテリーの監視停止"""
        if current_user.is_authenticated:
            battery_id = data.get('battery_id')
            leave_room(f'battery_{battery_id}')
            emit('status', {'message': f'バッテリー {battery_id} の監視を停止しました'})
    
    @socketio.on('request_prediction')
    def on_request_prediction(data):
        """予測要求"""
        if current_user.is_authenticated:
            try:
                battery_id = data.get('battery_id')
                prediction = ml_predictor.predict_battery_health(battery_id)
                
                emit('prediction_result', {
                    'battery_id': battery_id,
                    'prediction': prediction.to_dict()
                })
                
            except Exception as e:
                logger.error("予測要求エラー", error=str(e))
                emit('error', {'message': f'予測処理でエラーが発生しました: {str(e)}'})

# アプリケーション作成
app, socketio = create_app()

if __name__ == '__main__':
    logger.info("バッテリー監視システム開始")
    
    # データ収集開始
    data_collector.start_collection()
    
    # サーバー起動
    socketio.run(app, 
                debug=True, 
                host='0.0.0.0', 
                port=5000,
                use_reloader=False)  # データ収集スレッドとの競合回避
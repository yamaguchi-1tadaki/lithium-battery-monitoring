# リチウムイオンバッテリーAI予兆検知システム 操作マニュアル

## 📋 目次
1. [システム概要](#システム概要)
2. [アクセス方法](#アクセス方法)
3. [ログイン・認証](#ログイン認証)
4. [メインダッシュボード](#メインダッシュボード)
5. [管理者画面](#管理者画面)
6. [API仕様](#api仕様)
7. [トラブルシューティング](#トラブルシューティング)
8. [技術仕様](#技術仕様)
9. [運用・保守](#運用保守)

---

## システム概要

### 🎯 システムの目的
リチウムイオンバッテリーの健康状態をリアルタイムで監視し、AI機械学習による予兆検知と故障予測を行う総合監視システムです。SMART POWER社の電力事業における蓄電システムの安全管理と効率的な運用を支援します。

### 🚀 主要機能
- **リアルタイム監視**: 10台まで同時監視可能
- **AI予兆検知**: 異常検知・劣化予測・健康度評価
- **WebSocketライブ更新**: リアルタイムデータ表示
- **アラート管理**: 重要度別の自動警告システム
- **データ分析**: 統計情報と傾向分析
- **管理者制御**: システム設定とユーザー管理

### 🏗️ システム構成
```
フロントエンド: Bootstrap 5 + Chart.js + WebSocket
バックエンド: Flask + SocketIO + SQLAlchemy
AI・ML: scikit-learn (Isolation Forest, Random Forest, Gradient Boosting)
データベース: SQLite
認証: Flask-Login
```

---

## アクセス方法

### 🌐 システムURL
**メインシステム:**
```
https://5000-iqgwx5r4z3myowhrkmifd-6532622b.e2b.dev
```

### 📱 対応ブラウザ
- Google Chrome (推奨)
- Mozilla Firefox
- Microsoft Edge
- Safari

### 🔐 ネットワーク要件
- インターネット接続必須
- WebSocket通信対応
- JavaScript有効化必須

---

## ログイン・認証

### 👤 ユーザー権限レベル

#### 管理者 (admin)
- **ユーザー名**: `admin`
- **パスワード**: `admin123`
- **権限**: 全機能アクセス、システム管理、ユーザー管理

#### 操作者 (operator)
- **ユーザー名**: `operator`
- **パスワード**: `operator123`
- **権限**: 監視・制御、データ操作、アラート管理

#### 閲覧者 (viewer)
- **ユーザー名**: `viewer`
- **パスワード**: `viewer123`
- **権限**: データ閲覧のみ

### 🔑 ログイン手順
1. システムURLにアクセス
2. ログイン画面で認証情報を入力
3. 「ログイン」ボタンをクリック
4. ダッシュボードに自動リダイレクト

### 🚪 ログアウト
- 右上の「ログアウト」ボタンをクリック
- セッション自動終了（30分無操作）

---

## メインダッシュボード

### 📊 画面構成

#### ヘッダー部
- システムロゴとタイトル
- ナビゲーションメニュー
- ユーザー情報とログアウト

#### バッテリー選択エリア
- 登録バッテリー一覧
- 選択したバッテリーの詳細表示
- バッテリー追加/削除ボタン（管理者のみ）

#### リアルタイム監視パネル
- 電圧グラフ（リアルタイム更新）
- 電流グラフ（充放電状況）
- 温度トレンド
- 容量（SOC）表示

#### AI予測結果パネル
- 健康度スコア（0-100）
- 異常スコア（-1〜1）
- 劣化予測（残存サイクル数）
- 予測説明テキスト

#### アラート一覧
- アクティブアラート表示
- 重要度別色分け
- アラート詳細とアクション

### 🎛️ 操作方法

#### バッテリー選択
1. 左側のバッテリーリストから監視対象を選択
2. 選択したバッテリーの詳細情報が右側に表示
3. リアルタイムデータが自動更新開始

#### グラフ操作
- **ズーム**: マウスホイールでズームイン/アウト
- **パン**: ドラッグで表示範囲移動
- **期間選択**: 上部のボタンで表示期間変更（1時間/6時間/24時間）
- **データ点表示**: グラフ上でホバーすると詳細値表示

#### アラート管理
- **確認**: アラートをクリックして詳細表示
- **承認**: 「承認」ボタンでアラート承認
- **解決**: 問題解決後「解決済み」に変更

---

## 管理者画面

### 🔧 アクセス方法
管理者権限でログイン後、「管理」メニューまたは以下URLでアクセス:
```
https://5000-iqgwx5r4z3myowhrkmifd-6532622b.e2b.dev/admin
```

### 📈 システム統計画面

#### システムパフォーマンス
- CPU使用率
- メモリ使用量
- データベース接続数
- WebSocket接続数

#### データ統計
- 総バッテリー数
- 総センサーデータ数
- アクティブアラート数
- 予測実行回数

#### AI学習状況
- モデル最終学習日時
- 学習データ件数
- 予測精度指標
- モデルバージョン

### 🔋 バッテリー管理

#### バッテリー追加
1. 「新規バッテリー追加」ボタンをクリック
2. バッテリー情報を入力:
   - バッテリーID（一意識別子）
   - モデル名
   - 定格容量（Ah）
   - 定格電圧（V）
   - 設置場所
   - 設置日
3. 「登録」ボタンで保存

#### バッテリー編集
1. バッテリーリストから対象を選択
2. 「編集」ボタンをクリック
3. 情報を修正
4. 「更新」ボタンで保存

#### バッテリー削除
1. 削除対象を選択
2. 「削除」ボタンをクリック
3. 確認ダイアログで「OK」

### 🤖 AI学習管理

#### モデル再学習
1. 「AI学習」タブを選択
2. 学習データ期間を指定
3. 「モデル再学習実行」ボタンをクリック
4. 学習進捗を監視
5. 完了通知を確認

#### 学習パラメータ調整
- **異常検知感度**: 0.1〜1.0（デフォルト: 0.1）
- **予測期間**: 1〜30日（デフォルト: 7日）
- **学習データ期間**: 7〜90日（デフォルト: 30日）

### 🚨 アラート設定

#### 閾値設定
- **電圧**: 下限/上限値設定
- **電流**: 最大充放電電流
- **温度**: 動作温度範囲
- **容量**: 最小容量警告値

#### 通知設定
- **メール通知**: SMTP設定（未実装）
- **Slack通知**: Webhook URL設定（未実装）
- **システム内通知**: 常時有効

### 👥 ユーザー管理

#### ユーザー追加
1. 「ユーザー管理」タブを選択
2. 「新規ユーザー追加」をクリック
3. ユーザー情報を入力:
   - ユーザー名
   - メールアドレス
   - パスワード
   - 権限レベル
4. 「作成」ボタンで保存

#### 権限変更
1. ユーザーリストから対象を選択
2. 権限レベルを変更
3. 「更新」ボタンで保存

---

## API仕様

### 🔌 エンドポイント一覧

#### システム情報
```http
GET /api/system/status
```
**レスポンス例:**
```json
{
  "status": "running",
  "uptime": 3600,
  "version": "1.0.0",
  "battery_count": 5,
  "active_alerts": 2
}
```

#### バッテリー管理
```http
GET /api/batteries
POST /api/batteries
PUT /api/batteries/{id}
DELETE /api/batteries/{id}
```

#### センサーデータ
```http
GET /api/sensor-data/{battery_id}
GET /api/sensor-data/{battery_id}?start_time=2025-01-01&end_time=2025-01-02
```

#### AI予測
```http
GET /api/predictions/{battery_id}
POST /api/train
```

#### アラート
```http
GET /api/alerts
POST /api/alerts/{id}/acknowledge
POST /api/alerts/{id}/resolve
```

### 🔐 認証方式
- セッション認証（Flask-Login）
- API キー認証（未実装）
- JWT トークン（未実装）

### 📡 WebSocket イベント

#### 受信イベント
- `sensor_data`: リアルタイムセンサーデータ
- `prediction_update`: AI予測結果更新
- `alert`: 新規アラート通知
- `system_stats`: システム統計更新

#### 送信イベント
- `join_room`: 特定バッテリーの監視開始
- `leave_room`: 監視終了
- `request_prediction`: AI予測実行要求

---

## トラブルシューティング

### 🚨 よくある問題と解決方法

#### ログインできない
**症状**: ユーザー名/パスワードが正しいのにログインできない
**解決方法**:
1. ブラウザのキャッシュとクッキーをクリア
2. プライベートモードで再試行
3. 別のブラウザで試行
4. システム管理者に連絡

#### ダッシュボードでデータが表示されない
**症状**: グラフが空白またはエラー表示
**解決方法**:
1. ページをリロード（F5キー）
2. バッテリーが正しく選択されているか確認
3. WebSocket接続状況を確認（コンソールログ）
4. 管理者画面でシステム状態を確認

#### リアルタイム更新が止まった
**症状**: データが一定時間更新されない
**解決方法**:
1. ネットワーク接続を確認
2. ブラウザタブをアクティブにする
3. ページをリロード
4. システム再起動が必要な場合は管理者に連絡

#### AI予測が機能しない
**症状**: 予測結果が表示されない、エラーメッセージ表示
**解決方法**:
1. 管理者画面でAI学習状況を確認
2. 十分な学習データがあるか確認（最低100データポイント必要）
3. モデル再学習を実行
4. システムログでエラー詳細を確認

### 📞 サポート連絡先
- **技術サポート**: SMART POWER社 技術開発部
- **緊急時**: システム管理者（山口高広）
- **バグ報告**: GitHub Issues
- **機能要求**: 事業開発チーム

---

## 技術仕様

### 🖥️ システム要件

#### サーバー環境
- **OS**: Linux/Windows/macOS
- **Python**: 3.8以上
- **メモリ**: 最低2GB、推奨4GB
- **ストレージ**: 最低1GB、推奨10GB
- **ネットワーク**: インターネット接続必須

#### クライアント環境
- **ブラウザ**: Chrome 90+, Firefox 88+, Edge 90+, Safari 14+
- **JavaScript**: ES6対応必須
- **WebSocket**: 対応必須
- **画面解像度**: 最低1024x768、推奨1920x1080

### 🏗️ アーキテクチャ

#### フロントエンド技術
```
UI Framework: Bootstrap 5.3
Charts: Chart.js 4.0
Real-time: Socket.IO Client
HTTP Client: Axios
Icons: Font Awesome
```

#### バックエンド技術
```
Web Framework: Flask 3.1
Real-time: Flask-SocketIO 5.5
ORM: SQLAlchemy 2.0
Authentication: Flask-Login
Database: SQLite 3
```

#### AI・機械学習
```
ML Library: scikit-learn 1.6
Anomaly Detection: Isolation Forest
Degradation Prediction: Random Forest
Health Assessment: Gradient Boosting
Feature Engineering: 統計・時系列・物理的特徴
```

### 📊 データベーススキーマ

#### users テーブル
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### batteries テーブル
```sql
CREATE TABLE batteries (
    id INTEGER PRIMARY KEY,
    battery_id VARCHAR(50) UNIQUE NOT NULL,
    model VARCHAR(100) NOT NULL,
    capacity_nominal FLOAT NOT NULL,
    voltage_nominal FLOAT NOT NULL,
    location VARCHAR(200),
    installation_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### sensor_data テーブル
```sql
CREATE TABLE sensor_data (
    id INTEGER PRIMARY KEY,
    battery_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    voltage FLOAT,
    current FLOAT,
    temperature FLOAT,
    capacity FLOAT,
    power FLOAT,
    internal_resistance FLOAT,
    cycle_count INTEGER,
    is_valid BOOLEAN DEFAULT TRUE,
    quality_score FLOAT,
    FOREIGN KEY (battery_id) REFERENCES batteries (id)
);
```

#### predictions テーブル
```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    battery_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    risk_level VARCHAR(20),
    confidence_score FLOAT,
    predicted_failure_time DATETIME,
    health_score FLOAT,
    degradation_rate FLOAT,
    remaining_cycles INTEGER,
    anomaly_flags TEXT,
    model_version VARCHAR(20),
    data_points_used INTEGER,
    FOREIGN KEY (battery_id) REFERENCES batteries (id)
);
```

#### alerts テーブル
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    battery_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    status VARCHAR(20) DEFAULT 'active',
    acknowledged_at DATETIME,
    acknowledged_by INTEGER,
    resolved_at DATETIME,
    sensor_value FLOAT,
    threshold_value FLOAT,
    FOREIGN KEY (battery_id) REFERENCES batteries (id),
    FOREIGN KEY (acknowledged_by) REFERENCES users (id)
);
```

### 🔧 設定ファイル

#### config/development.py
```python
class DevelopmentConfig:
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///battery_monitor.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'dev-secret-key'
    WTF_CSRF_ENABLED = True
    
    # SocketIO設定
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_LOGGER = True
    SOCKETIO_ENGINEIO_LOGGER = True
    
    # AI・ML設定
    ML_MODEL_PATH = 'models/'
    PREDICTION_INTERVAL = 60  # 秒
    ANOMALY_THRESHOLD = 0.1
    
    # アラート設定
    VOLTAGE_MIN = 2.5
    VOLTAGE_MAX = 4.2
    TEMPERATURE_MIN = -10
    TEMPERATURE_MAX = 60
    CURRENT_MAX = 10.0
```

---

## 運用・保守

### 🔄 日常運用作業

#### 毎日の確認項目
- [ ] システム稼働状況確認
- [ ] アクティブアラート確認・対応
- [ ] データ収集状況確認
- [ ] AI予測精度確認
- [ ] ディスク容量確認

#### 毎週の保守作業
- [ ] ログファイルローテーション
- [ ] データベース最適化
- [ ] バックアップ実行・確認
- [ ] セキュリティアップデート確認
- [ ] パフォーマンス指標レビュー

#### 毎月の定期作業
- [ ] AIモデル再学習
- [ ] 古いデータのアーカイブ
- [ ] ユーザーアクセス権限見直し
- [ ] システム設定見直し
- [ ] 運用レポート作成

### 💾 バックアップ・復旧

#### 自動バックアップ
```bash
# 毎日午前2時に実行
0 2 * * * /path/to/backup_script.sh

# バックアップスクリプト例
#!/bin/bash
DATE=$(date +%Y%m%d)
cp /home/user/webapp/instance/battery_monitor.db /backup/battery_monitor_${DATE}.db
tar -czf /backup/webapp_${DATE}.tar.gz /home/user/webapp/
```

#### 手動バックアップ
```bash
# データベースバックアップ
sqlite3 battery_monitor.db ".backup backup_$(date +%Y%m%d).db"

# 完全システムバックアップ
tar -czf system_backup_$(date +%Y%m%d).tar.gz /home/user/webapp/
```

#### 復旧手順
1. システム停止
2. バックアップファイルから復元
3. 設定ファイル確認
4. 依存関係インストール
5. システム起動・動作確認

### 📊 監視・アラート

#### システム監視項目
- CPU使用率（閾値: 80%）
- メモリ使用率（閾値: 85%）
- ディスク使用率（閾値: 90%）
- プロセス生存確認
- WebSocket接続数

#### アプリケーション監視
- レスポンス時間（閾値: 5秒）
- エラー率（閾値: 5%）
- データベース接続プール
- AI予測実行頻度
- アクティブユーザー数

### 🔐 セキュリティ

#### 定期セキュリティ作業
- [ ] 依存関係脆弱性スキャン
- [ ] ログイン試行監視
- [ ] 不審なAPI呼び出し確認
- [ ] SSL証明書有効期限確認
- [ ] アクセスログ分析

#### セキュリティ設定
```python
# セキュリティヘッダー設定
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
}

# セッション設定
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

### 🚀 パフォーマンス最適化

#### データベース最適化
```sql
-- インデックス作成
CREATE INDEX idx_sensor_data_timestamp ON sensor_data(timestamp);
CREATE INDEX idx_sensor_data_battery_id ON sensor_data(battery_id);
CREATE INDEX idx_alerts_status ON alerts(status);

-- 統計情報更新
ANALYZE;

-- データベース圧縮
VACUUM;
```

#### キャッシュ設定
```python
# Redis設定（オプション）
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = 'redis://localhost:6379/0'
CACHE_DEFAULT_TIMEOUT = 300

# メモリキャッシュ設定
CACHE_CONFIG = {
    'prediction_cache_size': 1000,
    'data_cache_timeout': 60,
    'api_rate_limit': '100/hour'
}
```

### 📈 容量計画

#### データ増加予測
- センサーデータ: 約1MB/日/バッテリー
- 予測結果: 約100KB/日/バッテリー
- ログファイル: 約10MB/日
- 年間総容量: 約5GB（10バッテリー想定）

#### スケーリング計画
- **50バッテリー**: メモリ8GB、ストレージ50GB
- **100バッテリー**: メモリ16GB、ストレージ100GB、負荷分散検討
- **500バッテリー**: マイクロサービス化、データベース分離

---

## 📞 サポート・連絡先

### 🏢 開発・保守チーム
**SMART POWER株式会社 技術開発部**
- **プロジェクト責任者**: 山口高広（技術開発マネージャー）
- **技術担当**: AI・蓄電システム開発チーム
- **運用担当**: システム運用チーム

### 📧 連絡方法
- **一般問い合わせ**: [事業開発本部お問い合わせ窓口]
- **技術サポート**: [技術サポートデスク]
- **緊急時対応**: [24時間サポートライン]

### 📚 関連リソース
- **GitHub リポジトリ**: https://github.com/yamaguchi-1tadaki/lithium-battery-monitoring
- **技術ドキュメント**: /docs/
- **API仕様書**: /docs/api/
- **更新履歴**: /CHANGELOG.md

---

## 📝 付録

### A. エラーコード一覧
| コード | 説明 | 対処方法 |
|--------|------|----------|
| AUTH001 | 認証失敗 | ユーザー名・パスワードを確認 |
| DB001 | データベース接続エラー | システム管理者に連絡 |
| ML001 | AI学習エラー | データ品質を確認、再学習実行 |
| API001 | API呼び出しエラー | リクエスト形式を確認 |
| WS001 | WebSocket接続エラー | ネットワーク状況を確認 |

### B. 設定ファイルテンプレート
```yaml
# config.yaml
system:
  name: "リチウムイオンバッテリー監視システム"
  version: "1.0.0"
  environment: "production"

database:
  url: "sqlite:///battery_monitor.db"
  backup_interval: 86400  # 24時間

monitoring:
  data_collection_interval: 60  # 秒
  prediction_interval: 300      # 5分
  alert_check_interval: 30      # 30秒

thresholds:
  voltage_min: 2.5
  voltage_max: 4.2
  temperature_max: 60
  current_max: 10.0
```

### C. 運用チェックリスト
```markdown
## 日次チェックリスト
- [ ] システム稼働確認
- [ ] エラーログ確認
- [ ] アラート対応状況確認
- [ ] データ収集状況確認
- [ ] バックアップ実行確認

## 週次チェックリスト
- [ ] パフォーマンス指標確認
- [ ] セキュリティログ確認
- [ ] AI予測精度確認
- [ ] ユーザーフィードバック確認
- [ ] システムリソース使用状況確認

## 月次チェックリスト
- [ ] AIモデル再学習
- [ ] システム設定見直し
- [ ] ユーザー権限見直し
- [ ] 運用レポート作成
- [ ] 改善計画策定
```

---

**📅 最終更新日**: 2025年10月5日  
**📖 マニュアルバージョン**: 1.0.0  
**👨‍💼 作成者**: SMART POWER社 技術開発部  
**🎯 対象システム**: リチウムイオンバッテリーAI予兆検知システム v1.0

---

*本マニュアルは、SMART POWER社の電力・蓄電事業における技術資産として活用し、スマートグリッド技術連携、IoT監視システム展開、AI技術プラットフォーム構築の基盤となることを目的としています。*
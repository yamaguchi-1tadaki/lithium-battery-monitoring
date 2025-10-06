# 🔌 API リファレンス - リチウムイオンバッテリー監視システム

## 📋 目次
1. [API概要](#api概要)
2. [認証](#認証)
3. [エンドポイント一覧](#エンドポイント一覧)
4. [WebSocket API](#websocket-api)
5. [エラーハンドリング](#エラーハンドリング)
6. [レート制限](#レート制限)
7. [SDKとサンプル](#sdkとサンプル)

---

## API概要

### ベースURL
```
https://5000-iqgwx5r4z3myowhrkmifd-6532622b.e2b.dev
```

### APIバージョン
```
v1.0.0
```

### データ形式
- **リクエスト**: JSON
- **レスポンス**: JSON
- **文字エンコーディング**: UTF-8
- **タイムゾーン**: JST (Asia/Tokyo)

### HTTPメソッド
- `GET`: データ取得
- `POST`: データ作成
- `PUT`: データ更新
- `DELETE`: データ削除
- `PATCH`: 部分更新

---

## 認証

### セッション認証
```http
POST /api/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**レスポンス:**
```json
{
  "status": "success",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "permissions": ["read", "write", "admin"]
  },
  "session_expires_at": "2025-01-01T12:00:00Z"
}
```

### ログアウト
```http
POST /api/logout
```

### 認証状態確認
```http
GET /api/auth/status
```

---

## エンドポイント一覧

### 🔋 バッテリー管理

#### バッテリー一覧取得
```http
GET /api/batteries
```

**レスポンス:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "battery_id": "BATTERY_001",
      "model": "Industrial Li-ion 100Ah",
      "capacity_nominal": 100.0,
      "voltage_nominal": 3.7,
      "location": "データセンター A棟",
      "installation_date": "2024-01-15",
      "status": "active",
      "last_data_received": "2025-01-01T12:00:00Z",
      "health_score": 85.2,
      "anomaly_score": 0.1
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 10,
    "pages": 1
  }
}
```

#### バッテリー詳細取得
```http
GET /api/batteries/{battery_id}
```

**レスポンス:**
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "battery_id": "BATTERY_001",
    "model": "Industrial Li-ion 100Ah",
    "capacity_nominal": 100.0,
    "voltage_nominal": 3.7,
    "location": "データセンター A棟",
    "installation_date": "2024-01-15",
    "status": "active",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2025-01-01T12:00:00Z",
    "statistics": {
      "total_cycles": 156,
      "total_runtime_hours": 2480,
      "average_temperature": 26.5,
      "max_temperature": 45.2,
      "min_voltage": 3.2,
      "max_voltage": 4.1
    }
  }
}
```

#### バッテリー登録
```http
POST /api/batteries
Content-Type: application/json

{
  "battery_id": "BATTERY_011",
  "model": "Tesla 2170 Cell",
  "capacity_nominal": 85.0,
  "voltage_nominal": 3.6,
  "location": "工場 B棟 ライン3",
  "installation_date": "2025-01-01"
}
```

**レスポンス:**
```json
{
  "status": "success",
  "data": {
    "id": 11,
    "battery_id": "BATTERY_011",
    "message": "バッテリーが正常に登録されました"
  }
}
```

#### バッテリー更新
```http
PUT /api/batteries/{battery_id}
Content-Type: application/json

{
  "location": "工場 C棟 ライン1",
  "status": "maintenance"
}
```

#### バッテリー削除
```http
DELETE /api/batteries/{battery_id}
```

### 📊 センサーデータ

#### センサーデータ取得
```http
GET /api/sensor-data/{battery_id}?start_time=2025-01-01T00:00:00Z&end_time=2025-01-01T23:59:59Z&limit=1000
```

**パラメータ:**
- `start_time`: 開始日時 (ISO 8601形式)
- `end_time`: 終了日時 (ISO 8601形式)
- `limit`: 取得件数上限 (デフォルト: 100, 最大: 10000)
- `interval`: データ間隔 ('1m', '5m', '1h', '1d')

**レスポンス:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 12345,
      "battery_id": 1,
      "timestamp": "2025-01-01T12:00:00Z",
      "voltage": 3.85,
      "current": -2.3,
      "temperature": 26.2,
      "capacity": 87.5,
      "power": -8.855,
      "internal_resistance": 0.048,
      "cycle_count": 156,
      "is_valid": true,
      "quality_score": 0.95
    }
  ],
  "metadata": {
    "total_records": 1440,
    "valid_records": 1438,
    "invalid_records": 2,
    "data_quality": 99.86,
    "time_range": {
      "start": "2025-01-01T00:00:00Z",
      "end": "2025-01-01T23:59:59Z"
    }
  }
}
```

#### 最新センサーデータ取得
```http
GET /api/sensor-data/{battery_id}/latest
```

#### センサーデータ統計取得
```http
GET /api/sensor-data/{battery_id}/statistics?period=24h
```

**レスポンス:**
```json
{
  "status": "success",
  "data": {
    "period": "24h",
    "voltage": {
      "min": 3.65,
      "max": 4.05,
      "avg": 3.82,
      "std": 0.12
    },
    "current": {
      "min": -5.2,
      "max": 4.8,
      "avg": -0.5,
      "std": 2.1
    },
    "temperature": {
      "min": 24.1,
      "max": 28.9,
      "avg": 26.2,
      "std": 1.3
    },
    "capacity": {
      "min": 85.2,
      "max": 98.7,
      "avg": 91.5,
      "std": 4.2
    }
  }
}
```

### 🤖 AI予測

#### 予測結果取得
```http
GET /api/predictions/{battery_id}?limit=10
```

**レスポンス:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 5678,
      "battery_id": 1,
      "created_at": "2025-01-01T12:00:00Z",
      "risk_level": "medium",
      "confidence_score": 0.85,
      "predicted_failure_time": "2025-03-15T10:00:00Z",
      "health_score": 82.5,
      "degradation_rate": 0.15,
      "remaining_cycles": 844,
      "anomaly_flags": ["voltage_drift", "capacity_fade"],
      "model_version": "v2.1.0",
      "data_points_used": 2880,
      "explanation": "軽微な容量劣化が検出されましたが、正常範囲内です。定期メンテナンスを推奨します。"
    }
  ]
}
```

#### 最新予測結果取得
```http
GET /api/predictions/{battery_id}/latest
```

#### AI予測実行
```http
POST /api/predictions/{battery_id}/predict
Content-Type: application/json

{
  "prediction_type": ["anomaly", "degradation", "health"],
  "data_points": 1440,
  "model_version": "latest"
}
```

#### モデル再学習実行
```http
POST /api/train
Content-Type: application/json

{
  "model_types": ["anomaly_detector", "degradation_predictor"],
  "training_period_days": 30,
  "force_retrain": false
}
```

**レスポンス:**
```json
{
  "status": "success",
  "job_id": "training_20250101_120000",
  "estimated_completion": "2025-01-01T12:30:00Z",
  "message": "モデル学習を開始しました"
}
```

#### 学習ジョブ状況確認
```http
GET /api/train/status/{job_id}
```

### 🚨 アラート管理

#### アラート一覧取得
```http
GET /api/alerts?status=active&severity=warning&limit=50
```

**パラメータ:**
- `status`: active, acknowledged, resolved
- `severity`: critical, warning, info
- `battery_id`: 特定バッテリーのアラート
- `start_date`, `end_date`: 期間指定

**レスポンス:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 789,
      "battery_id": 1,
      "created_at": "2025-01-01T12:00:00Z",
      "alert_type": "voltage",
      "severity": "warning",
      "title": "過電圧アラート",
      "message": "電圧が閾値を超えました: 4.25V > 4.20V",
      "status": "active",
      "acknowledged_at": null,
      "acknowledged_by": null,
      "resolved_at": null,
      "sensor_value": 4.25,
      "threshold_value": 4.20,
      "battery": {
        "battery_id": "BATTERY_001",
        "location": "データセンター A棟"
      }
    }
  ]
}
```

#### アラート承認
```http
POST /api/alerts/{alert_id}/acknowledge
Content-Type: application/json

{
  "comment": "確認済み。監視を継続します。"
}
```

#### アラート解決
```http
POST /api/alerts/{alert_id}/resolve
Content-Type: application/json

{
  "resolution": "バッテリー交換により解決",
  "action_taken": "予防保守実施"
}
```

### 📈 システム管理

#### システム状態取得
```http
GET /api/system/status
```

**レスポンス:**
```json
{
  "status": "success",
  "data": {
    "system_status": "healthy",
    "uptime": 86400,
    "version": "1.0.0",
    "environment": "production",
    "database": {
      "status": "connected",
      "connections": 5,
      "pool_size": 20
    },
    "ml_models": {
      "anomaly_detector": {
        "status": "loaded",
        "version": "v2.1.0",
        "last_trained": "2025-01-01T00:00:00Z"
      },
      "degradation_predictor": {
        "status": "loaded",
        "version": "v2.1.0",
        "last_trained": "2025-01-01T00:00:00Z"
      }
    },
    "statistics": {
      "total_batteries": 10,
      "active_batteries": 8,
      "total_sensor_data": 1500000,
      "active_alerts": 3,
      "predictions_today": 240,
      "connected_users": 2
    }
  }
}
```

#### システム統計取得
```http
GET /api/system/statistics?period=24h
```

#### ヘルスチェック
```http
GET /api/health
```

**レスポンス:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-01T12:00:00Z",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "ml_models": "ok",
    "websocket": "ok"
  }
}
```

### 👥 ユーザー管理

#### ユーザー一覧取得 (管理者のみ)
```http
GET /api/users
```

#### ユーザー作成 (管理者のみ)
```http
POST /api/users
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "securepassword",
  "role": "operator",
  "is_active": true
}
```

#### ユーザー情報更新 (管理者のみ)
```http
PUT /api/users/{user_id}
Content-Type: application/json

{
  "role": "admin",
  "is_active": false
}
```

---

## WebSocket API

### 接続エンドポイント
```javascript
const socket = io('https://5000-iqgwx5r4z3myowhrkmifd-6532622b.e2b.dev');
```

### イベント一覧

#### 受信イベント

##### sensor_data
リアルタイムセンサーデータ
```javascript
socket.on('sensor_data', (data) => {
  console.log(data);
  // {
  //   battery_id: "BATTERY_001",
  //   timestamp: "2025-01-01T12:00:00Z",
  //   voltage: 3.85,
  //   current: -2.3,
  //   temperature: 26.2,
  //   capacity: 87.5
  // }
});
```

##### prediction_update
AI予測結果更新
```javascript
socket.on('prediction_update', (data) => {
  console.log(data);
  // {
  //   battery_id: "BATTERY_001",
  //   health_score: 82.5,
  //   anomaly_score: 0.1,
  //   risk_level: "medium"
  // }
});
```

##### alert
新規アラート通知
```javascript
socket.on('alert', (data) => {
  console.log(data);
  // {
  //   id: 789,
  //   battery_id: "BATTERY_001",
  //   severity: "warning",
  //   title: "過電圧アラート",
  //   message: "電圧が閾値を超えました"
  // }
});
```

##### system_stats
システム統計更新
```javascript
socket.on('system_stats', (data) => {
  console.log(data);
  // {
  //   connected_users: 3,
  //   active_batteries: 8,
  //   total_alerts: 5,
  //   cpu_usage: 45.2,
  //   memory_usage: 62.1
  // }
});
```

#### 送信イベント

##### join_room
特定バッテリーの監視開始
```javascript
socket.emit('join_room', {
  battery_id: 'BATTERY_001'
});
```

##### leave_room
監視終了
```javascript
socket.emit('leave_room', {
  battery_id: 'BATTERY_001'
});
```

##### request_prediction
AI予測実行要求
```javascript
socket.emit('request_prediction', {
  battery_id: 'BATTERY_001',
  prediction_type: 'health'
});
```

---

## エラーハンドリング

### HTTP ステータスコード
- `200 OK`: 成功
- `201 Created`: 作成成功
- `400 Bad Request`: 不正なリクエスト
- `401 Unauthorized`: 認証が必要
- `403 Forbidden`: 権限不足
- `404 Not Found`: リソースが見つからない
- `429 Too Many Requests`: レート制限
- `500 Internal Server Error`: サーバーエラー

### エラーレスポンス形式
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "入力データが不正です",
    "details": [
      {
        "field": "voltage",
        "message": "電圧は0以上である必要があります"
      }
    ]
  },
  "timestamp": "2025-01-01T12:00:00Z",
  "request_id": "req_12345"
}
```

### エラーコード一覧
| コード | 説明 | HTTP Status |
|--------|------|-------------|
| `VALIDATION_ERROR` | 入力データ検証エラー | 400 |
| `AUTH_REQUIRED` | 認証が必要 | 401 |
| `INSUFFICIENT_PERMISSIONS` | 権限不足 | 403 |
| `RESOURCE_NOT_FOUND` | リソースが見つからない | 404 |
| `RATE_LIMIT_EXCEEDED` | レート制限超過 | 429 |
| `DATABASE_ERROR` | データベースエラー | 500 |
| `ML_MODEL_ERROR` | 機械学習モデルエラー | 500 |
| `WEBSOCKET_ERROR` | WebSocket接続エラー | 500 |

---

## レート制限

### 制限内容
- **認証API**: 10 req/min/IP
- **データ取得API**: 100 req/min/user
- **データ更新API**: 50 req/min/user
- **AI予測API**: 20 req/min/user
- **WebSocket接続**: 10 connections/user

### レート制限ヘッダー
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1640995200
```

---

## SDKとサンプル

### JavaScript SDK

#### インストール
```bash
npm install lithium-battery-monitor-sdk
```

#### 基本的な使用方法
```javascript
import { BatteryMonitorClient } from 'lithium-battery-monitor-sdk';

const client = new BatteryMonitorClient({
  baseUrl: 'https://5000-iqgwx5r4z3myowhrkmifd-6532622b.e2b.dev',
  username: 'admin',
  password: 'admin123'
});

// 認証
await client.login();

// バッテリー一覧取得
const batteries = await client.getBatteries();

// リアルタイムデータ監視
client.subscribeSensorData('BATTERY_001', (data) => {
  console.log('New sensor data:', data);
});

// AI予測実行
const prediction = await client.predictBatteryHealth('BATTERY_001');
```

### Python SDK

#### インストール
```bash
pip install lithium-battery-monitor-sdk
```

#### 基本的な使用方法
```python
from lithium_battery_monitor import BatteryMonitorClient

client = BatteryMonitorClient(
    base_url='https://5000-iqgwx5r4z3myowhrkmifd-6532622b.e2b.dev',
    username='admin',
    password='admin123'
)

# 認証
client.login()

# バッテリー一覧取得
batteries = client.get_batteries()

# センサーデータ取得
sensor_data = client.get_sensor_data(
    battery_id='BATTERY_001',
    start_time='2025-01-01T00:00:00Z',
    end_time='2025-01-01T23:59:59Z'
)

# AI予測実行
prediction = client.predict_battery_health('BATTERY_001')
```

### cURLサンプル

#### ログイン + データ取得
```bash
# ログイン
curl -c cookies.txt -X POST \
  https://5000-iqgwx5r4z3myowhrkmifd-6532622b.e2b.dev/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "admin", "password": "admin123"}'

# バッテリー一覧取得
curl -b cookies.txt \
  https://5000-iqgwx5r4z3myowhrkmifd-6532622b.e2b.dev/api/batteries

# センサーデータ取得
curl -b cookies.txt \
  'https://5000-iqgwx5r4z3myowhrkmifd-6532622b.e2b.dev/api/sensor-data/BATTERY_001?limit=100'
```

---

**📅 最終更新**: 2025年10月5日  
**📖 APIバージョン**: v1.0.0  
**👨‍💼 作成者**: PFU事業開発本部  
**📧 サポート**: api-support@pfu.fujitsu.com
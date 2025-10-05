"""
リチウムイオンバッテリーセンサーデータシミュレーター

リアルなバッテリー特性を模倣したセンサーデータを生成します。
劣化パターン、温度依存性、充放電特性を含みます。
"""

import random
import math
import time
import threading
import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import numpy as np

@dataclass
class BatteryState:
    """バッテリー状態データクラス"""
    battery_id: str
    timestamp: datetime
    voltage: float
    current: float
    temperature: float
    capacity: float
    power: float
    internal_resistance: float
    cycle_count: int
    health_score: float
    is_charging: bool
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class BatterySimulator:
    """リチウムイオンバッテリーシミュレーター"""
    
    def __init__(self, battery_id: str, nominal_voltage: float = 3.7, 
                 nominal_capacity: float = 2.5, initial_soh: float = 1.0):
        """
        Args:
            battery_id: バッテリー識別子
            nominal_voltage: 公称電圧 (V)
            nominal_capacity: 公称容量 (Ah)
            initial_soh: 初期健康状態 (0-1)
        """
        self.battery_id = battery_id
        self.nominal_voltage = nominal_voltage
        self.nominal_capacity = nominal_capacity
        self.max_voltage = 4.2  # 満充電電圧
        self.min_voltage = 3.0  # 過放電保護電圧
        
        # 状態変数
        self.current_capacity = 100.0  # 現在の容量 (%)
        self.soh = initial_soh  # State of Health
        self.cycle_count = 0
        self.temperature = 25.0  # 周囲温度 (°C)
        self.is_charging = False
        self.charge_current = 0.0  # 充放電電流 (A)
        
        # 劣化パラメータ
        self.degradation_rate = 0.0001  # 1サイクルあたりの劣化率
        self.temperature_stress_factor = 1.0
        
        # ノイズパラメータ
        self.voltage_noise = 0.01
        self.current_noise = 0.05
        self.temperature_noise = 0.5
        
        # 異常シミュレーション用フラグ
        self.simulate_anomaly = False
        self.anomaly_type = None  # 'overcharge', 'overheat', 'internal_short'
        
    def get_voltage_from_capacity(self, capacity_percent: float) -> float:
        """容量から電圧を計算（リチウムイオンバッテリーの放電特性）"""
        # 容量-電圧特性曲線（実際のLi-ion特性を近似）
        if capacity_percent > 95:
            voltage = self.max_voltage - (100 - capacity_percent) * 0.02
        elif capacity_percent > 20:
            voltage = self.min_voltage + (capacity_percent - 20) * 0.0125
        else:
            # 急激な電圧降下
            voltage = self.min_voltage + capacity_percent * 0.005
        
        # 温度補正
        temp_coefficient = -0.003  # V/°C
        voltage += (self.temperature - 25) * temp_coefficient
        
        # SOH影響
        voltage *= (0.95 + 0.05 * self.soh)
        
        return max(voltage, 2.5)  # 最低電圧保護
    
    def get_internal_resistance(self) -> float:
        """内部抵抗計算"""
        base_resistance = 0.05  # Ω
        
        # SOH影響（劣化により内部抵抗増加）
        soh_factor = 1 + (1 - self.soh) * 2
        
        # 温度影響（低温で抵抗増加）
        temp_factor = 1 + (25 - self.temperature) * 0.02
        
        # 容量影響（低容量で抵抗増加）
        capacity_factor = 1 + (100 - self.current_capacity) * 0.005
        
        return base_resistance * soh_factor * temp_factor * capacity_factor
    
    def simulate_charging_cycle(self, target_capacity: float = 100.0, 
                               charge_rate: float = 1.0) -> None:
        """充電サイクルシミュレーション"""
        if self.current_capacity < target_capacity:
            self.is_charging = True
            
            # 充電電流計算（CC-CV特性）
            if self.current_capacity < 80:
                # 定電流充電
                self.charge_current = charge_rate
            else:
                # 定電圧充電（テーパー）
                self.charge_current = charge_rate * (100 - self.current_capacity) / 20
            
            # 容量増加
            capacity_increase = self.charge_current / self.nominal_capacity * 100 / 60  # %/min
            self.current_capacity = min(self.current_capacity + capacity_increase, 100.0)
            
        else:
            self.is_charging = False
            self.charge_current = 0.0
    
    def simulate_discharge_cycle(self, load_current: float = 0.5) -> None:
        """放電サイクルシミュレーション"""
        if self.current_capacity > 0:
            self.is_charging = False
            self.charge_current = -load_current
            
            # 容量減少
            capacity_decrease = load_current / self.nominal_capacity * 100 / 60  # %/min
            self.current_capacity = max(self.current_capacity - capacity_decrease, 0.0)
    
    def simulate_temperature_change(self) -> None:
        """温度変化シミュレーション"""
        # 基本の周囲温度変動（日内変動）
        base_temp = 25 + 5 * math.sin(time.time() / 3600)  # 1時間周期
        
        # 充放電による発熱
        heat_generation = abs(self.charge_current) * 0.1 * self.get_internal_resistance()
        
        # 温度更新
        self.temperature += (base_temp + heat_generation - self.temperature) * 0.1
        
        # 異常発熱シミュレーション
        if self.anomaly_type == 'overheat':
            self.temperature += random.uniform(0, 2)
    
    def simulate_degradation(self) -> None:
        """経年劣化シミュレーション"""
        # サイクル劣化
        if abs(self.charge_current) > 0.1:  # 充放電中
            cycle_stress = abs(self.charge_current) / self.nominal_capacity
            temp_stress = max(1, (self.temperature - 25) * 0.05)
            
            degradation = self.degradation_rate * cycle_stress * temp_stress
            self.soh = max(0.5, self.soh - degradation)
            
            # サイクル数カウント
            if not self.is_charging and self.charge_current < -0.1:
                self.cycle_count += 1 / 3600  # 1時間で1サイクル相当
    
    def inject_anomaly(self, anomaly_type: str, duration: int = 60) -> None:
        """異常状態の注入"""
        self.simulate_anomaly = True
        self.anomaly_type = anomaly_type
        
        # 一定時間後に異常状態を解除
        def clear_anomaly():
            time.sleep(duration)
            self.simulate_anomaly = False
            self.anomaly_type = None
        
        threading.Thread(target=clear_anomaly, daemon=True).start()
    
    def get_current_state(self) -> BatteryState:
        """現在のバッテリー状態を取得"""
        # 基本値計算
        voltage = self.get_voltage_from_capacity(self.current_capacity)
        current = self.charge_current
        internal_resistance = self.get_internal_resistance()
        power = voltage * abs(current)
        
        # 異常状態の処理
        if self.simulate_anomaly:
            if self.anomaly_type == 'overcharge':
                voltage += random.uniform(0.1, 0.3)
                current *= 1.5
            elif self.anomaly_type == 'internal_short':
                voltage *= 0.8
                current += random.uniform(0.2, 0.5)
                self.temperature += random.uniform(5, 15)
        
        # ノイズ追加
        voltage += random.gauss(0, self.voltage_noise)
        current += random.gauss(0, self.current_noise)
        temperature = self.temperature + random.gauss(0, self.temperature_noise)
        
        # 健康スコア計算
        health_score = (self.soh * 50 + 
                       (100 - min(abs(current), 3) / 3 * 20) +
                       (100 - max(0, temperature - 40) / 20 * 30))
        health_score = max(0, min(100, health_score))
        
        return BatteryState(
            battery_id=self.battery_id,
            timestamp=datetime.now(timezone.utc),
            voltage=round(voltage, 3),
            current=round(current, 3),
            temperature=round(temperature, 1),
            capacity=round(self.current_capacity, 1),
            power=round(power, 3),
            internal_resistance=round(internal_resistance, 4),
            cycle_count=int(self.cycle_count),
            health_score=round(health_score, 1),
            is_charging=self.is_charging
        )

class MultibatterySensorSystem:
    """複数バッテリーの統合センサーシステム"""
    
    def __init__(self):
        self.simulators: Dict[str, BatterySimulator] = {}
        self.is_running = False
        self.update_interval = 1.0  # 秒
        self.data_callbacks = []
        
    def add_battery(self, battery_id: str, **kwargs) -> None:
        """バッテリーシミュレーターを追加"""
        self.simulators[battery_id] = BatterySimulator(battery_id, **kwargs)
        print(f"バッテリー {battery_id} を追加しました")
    
    def remove_battery(self, battery_id: str) -> None:
        """バッテリーシミュレーターを削除"""
        if battery_id in self.simulators:
            del self.simulators[battery_id]
            print(f"バッテリー {battery_id} を削除しました")
    
    def add_data_callback(self, callback) -> None:
        """データ更新コールバック関数を追加"""
        self.data_callbacks.append(callback)
    
    def start_simulation(self) -> None:
        """シミュレーション開始"""
        if self.is_running:
            return
        
        self.is_running = True
        threading.Thread(target=self._simulation_loop, daemon=True).start()
        print("センサーシミュレーションを開始しました")
    
    def stop_simulation(self) -> None:
        """シミュレーション停止"""
        self.is_running = False
        print("センサーシミュレーションを停止しました")
    
    def _simulation_loop(self) -> None:
        """メインシミュレーションループ"""
        while self.is_running:
            try:
                all_states = []
                
                for battery_id, simulator in self.simulators.items():
                    # 温度変化シミュレーション
                    simulator.simulate_temperature_change()
                    
                    # 充放電シミュレーション（ランダムパターン）
                    if random.random() < 0.1:  # 10%の確率で状態変更
                        if random.random() < 0.5:
                            simulator.simulate_charging_cycle()
                        else:
                            simulator.simulate_discharge_cycle(random.uniform(0.2, 1.0))
                    
                    # 劣化シミュレーション
                    simulator.simulate_degradation()
                    
                    # 現在状態取得
                    current_state = simulator.get_current_state()
                    all_states.append(current_state)
                
                # コールバック実行
                for callback in self.data_callbacks:
                    try:
                        callback(all_states)
                    except Exception as e:
                        print(f"コールバック実行エラー: {e}")
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"シミュレーションループエラー: {e}")
                time.sleep(1)
    
    def inject_scenario(self, scenario_name: str) -> None:
        """シナリオベースの異常注入"""
        scenarios = {
            'high_temp_stress': {
                'description': '高温ストレステスト',
                'actions': lambda: [sim.inject_anomaly('overheat', 300) 
                                  for sim in self.simulators.values()]
            },
            'overcharge_test': {
                'description': '過充電テスト',
                'actions': lambda: [list(self.simulators.values())[0].inject_anomaly('overcharge', 120)]
            },
            'internal_short': {
                'description': '内部短絡シミュレーション',
                'actions': lambda: [list(self.simulators.values())[0].inject_anomaly('internal_short', 180)]
            }
        }
        
        if scenario_name in scenarios:
            scenario = scenarios[scenario_name]
            print(f"シナリオ実行: {scenario['description']}")
            scenario['actions']()
        else:
            print(f"未知のシナリオ: {scenario_name}")
    
    def get_system_status(self) -> Dict:
        """システム全体のステータス取得"""
        status = {
            'is_running': self.is_running,
            'battery_count': len(self.simulators),
            'batteries': {}
        }
        
        for battery_id, simulator in self.simulators.items():
            state = simulator.get_current_state()
            status['batteries'][battery_id] = {
                'health_score': state.health_score,
                'capacity': state.capacity,
                'temperature': state.temperature,
                'cycle_count': state.cycle_count,
                'soh': simulator.soh
            }
        
        return status

# シングルトンインスタンス
sensor_system = MultibatterySensorSystem()

if __name__ == "__main__":
    # テスト実行
    def print_data(states):
        for state in states:
            print(f"{state.battery_id}: {state.voltage}V, {state.current}A, "
                  f"{state.temperature}°C, {state.capacity}%")
    
    sensor_system.add_data_callback(print_data)
    sensor_system.add_battery("BATTERY_001")
    sensor_system.add_battery("BATTERY_002")
    sensor_system.start_simulation()
    
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    
    sensor_system.stop_simulation()
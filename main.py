#!/usr/bin/env python3
"""
iot-temperature-monitor
IoT Temperature & Humidity Monitor with simulated sensor readings,
real-time alerts, data logging, statistics, and ASCII chart visualization.

Author: Sameer Bansal
Reg No: RA2311032010061
College: SRM Institute of Science and Technology
Branch: B.Tech CSE (IoT) | Batch: 2023-2027
"""

import random
import time
import datetime
import os
import csv
import json
import math

# ── Configuration ─────────────────────────────────────────
CONFIG = {
    "location": "SRM IST Lab, Kattankulathur",
    "sensor_id": "DHT22-SRM-001",
    "update_interval": 2,  # seconds between readings
    "temp_min_normal": 18.0,  # °C
    "temp_max_normal": 35.0,  # °C
    "temp_critical_low": 10.0,  # °C
    "temp_critical_high": 45.0,  # °C
    "humidity_min": 30.0,  # %
    "humidity_max": 90.0,  # %
    "log_file": "output/temperature_log.csv",
    "json_report": "output/temperature_report.json",
    "max_history": 100,
}

# Alert thresholds
ALERTS = {
    "CRITICAL_HIGH": {"temp": 45.0, "color": "\033[91m", "icon": "🔴"},
    "HIGH": {"temp": 35.0, "color": "\033[93m", "icon": "🟡"},
    "NORMAL": {"temp": 25.0, "color": "\033[92m", "icon": "🟢"},
    "LOW": {"temp": 18.0, "color": "\033[94m", "icon": "🔵"},
    "CRITICAL_LOW": {"temp": 10.0, "color": "\033[95m", "icon": "🟣"},
}

RESET = "\033[0m"
BOLD = "\033[1m"


# ── Sensor Simulation ─────────────────────────────────────
class DHT22Sensor:
    """Simulates a DHT22 Temperature & Humidity Sensor"""

    def __init__(self):
        self.base_temp = 28.0
        self.base_humidity = 60.0
        self.drift = 0.0
        self.reading_count = 0
        self.last_temp = self.base_temp
        self.last_humidity = self.base_humidity

    def read(self):
        """Simulate realistic sensor reading with noise and drift"""
        self.reading_count += 1

        # Add gradual drift (simulates room heating/cooling)
        self.drift += random.uniform(-0.3, 0.3)
        self.drift = max(-8.0, min(8.0, self.drift))

        # Add sensor noise
        noise_temp = random.gauss(0, 0.4)
        noise_humidity = random.gauss(0, 1.0)

        # Simulate occasional temperature spikes (IoT anomalies)
        spike = 0
        if random.random() < 0.05:  # 5% chance of spike
            spike = random.uniform(5, 12) * random.choice([-1, 1])

        temp = round(self.base_temp + self.drift + noise_temp + spike, 2)
        humidity = round(self.base_humidity + random.uniform(-5, 5) + noise_humidity, 2)

        # Clamp to realistic bounds
        temp = max(-10.0, min(60.0, temp))
        humidity = max(0.0, min(100.0, humidity))

        # Simulate occasional sensor failure (1% chance)
        if random.random() < 0.01:
            return None, None, "SENSOR_ERROR"

        self.last_temp = temp
        self.last_humidity = humidity
        return temp, humidity, "OK"

    def calibrate(self, temp_offset=0.0, humidity_offset=0.0):
        self.base_temp += temp_offset
        self.base_humidity += humidity_offset


# ── Alert System ──────────────────────────────────────────
class AlertSystem:
    def __init__(self):
        self.alert_log = []
        self.alert_counts = {k: 0 for k in ALERTS}

    def check(self, temp, humidity):
        alerts = []

        if temp >= CONFIG["temp_critical_high"]:
            level = "CRITICAL_HIGH"
        elif temp >= CONFIG["temp_max_normal"]:
            level = "HIGH"
        elif temp <= CONFIG["temp_critical_low"]:
            level = "CRITICAL_LOW"
        elif temp <= CONFIG["temp_min_normal"]:
            level = "LOW"
        else:
            level = "NORMAL"

        if level != "NORMAL":
            alert = {
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "temp": temp,
                "humidity": humidity,
                "icon": ALERTS[level]["icon"],
            }
            alerts.append(alert)
            self.alert_log.append(alert)
            self.alert_counts[level] += 1

        if humidity > CONFIG["humidity_max"]:
            alerts.append(
                {
                    "level": "HIGH_HUMIDITY",
                    "humidity": humidity,
                    "icon": "💧",
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                }
            )
        elif humidity < CONFIG["humidity_min"]:
            alerts.append(
                {
                    "level": "LOW_HUMIDITY",
                    "humidity": humidity,
                    "icon": "🏜️",
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                }
            )

        return level, alerts


# ── Data Logger ───────────────────────────────────────────
class DataLogger:
    def __init__(self):
        os.makedirs("output", exist_ok=True)
        self.readings = []
        self._init_csv()

    def _init_csv(self):
        with open(CONFIG["log_file"], "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "temperature_c",
                    "humidity_pct",
                    "heat_index",
                    "alert_level",
                    "sensor_status",
                ]
            )

    def log(self, temp, humidity, heat_index, alert_level, status):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, temp, humidity, heat_index, alert_level, status]

        with open(CONFIG["log_file"], "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        self.readings.append(
            {
                "timestamp": timestamp,
                "temp": temp,
                "humidity": humidity,
                "heat_index": heat_index,
                "alert_level": alert_level,
            }
        )

        if len(self.readings) > CONFIG["max_history"]:
            self.readings.pop(0)

    def get_stats(self):
        if not self.readings:
            return {}
        temps = [r["temp"] for r in self.readings if r["temp"] is not None]
        humidities = [r["humidity"] for r in self.readings if r["humidity"] is not None]
        return {
            "count": len(temps),
            "temp_avg": round(sum(temps) / len(temps), 2),
            "temp_min": min(temps),
            "temp_max": max(temps),
            "temp_range": round(max(temps) - min(temps), 2),
            "humidity_avg": round(sum(humidities) / len(humidities), 2),
            "humidity_min": min(humidities),
            "humidity_max": max(humidities),
        }

    def save_report(self, alert_system):
        stats = self.get_stats()
        report = {
            "report_generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sensor_id": CONFIG["sensor_id"],
            "location": CONFIG["location"],
            "statistics": stats,
            "alert_summary": alert_system.alert_counts,
            "total_alerts": len(alert_system.alert_log),
            "last_10_readings": self.readings[-10:],
        }
        with open(CONFIG["json_report"], "w") as f:
            json.dump(report, f, indent=2)
        return CONFIG["json_report"]


# ── Heat Index Calculator ─────────────────────────────────
def calculate_heat_index(temp_c, humidity):
    """Calculate Heat Index (Feels Like temperature)"""
    temp_f = (temp_c * 9 / 5) + 32
    if temp_f < 80:
        hi_f = 0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (humidity * 0.094))
    else:
        hi_f = (
            -42.379
            + 2.04901523 * temp_f
            + 10.14333127 * humidity
            - 0.22475541 * temp_f * humidity
            - 0.00683783 * temp_f**2
            - 0.05481717 * humidity**2
            + 0.00122874 * temp_f**2 * humidity
            + 0.00085282 * temp_f * humidity**2
            - 0.00000199 * temp_f**2 * humidity**2
        )
    return round((hi_f - 32) * 5 / 9, 2)


# ── ASCII Chart ───────────────────────────────────────────
def draw_ascii_chart(
    readings, key="temp", title="Temperature (°C)", width=50, height=10
):
    if len(readings) < 2:
        print("  Not enough data for chart yet.")
        return

    values = [r[key] for r in readings[-width:] if r[key] is not None]
    if not values:
        return

    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val or 1

    print(f"\n  📊 {title} (last {len(values)} readings)")
    print(f"  {'─' * (width + 8)}")

    for row in range(height, -1, -1):
        threshold = min_val + (row / height) * val_range
        if row % 2 == 0:
            label = f"{threshold:5.1f} │"
        else:
            label = f"      │"

        line = ""
        for val in values:
            normalized = (val - min_val) / val_range
            if normalized >= row / height:
                line += "█"
            else:
                line += " "
        print(f"  {label}{line}")

    print(f"  {'      └' + '─' * len(values)}")
    print(f"  {'':7} {'Start':>{len(values)//2}}{'Latest':>{len(values)//2}}")


# ── Display Functions ─────────────────────────────────────
def clear():
    os.system("cls" if os.name == "nt" else "clear")


def display_banner():
    print("=" * 60)
    print("    🌡️  IOT TEMPERATURE & HUMIDITY MONITOR")
    print(f"    Sensor  : {CONFIG['sensor_id']}")
    print(f"    Location: {CONFIG['location']}")
    print("    Author  : Sameer Bansal | RA2311032010061")
    print("=" * 60)


def get_alert_color(level):
    return ALERTS.get(level, {}).get("color", "\033[92m")


def display_reading(temp, humidity, heat_index, level, alerts, reading_num):
    icon = ALERTS.get(level, {}).get("icon", "🟢")
    color = get_alert_color(level)
    now = datetime.datetime.now().strftime("%H:%M:%S")

    print(f"\n  ┌{'─' * 50}┐")
    print(f"  │  🕐 {now}  |  Reading #{reading_num:<6}                  │")
    print(f"  │{'─' * 50}│")
    print(
        f"  │  🌡️  Temperature  : {color}{BOLD}{temp:>6.2f} °C{RESET}  {icon}  ({level})      │"
    )
    print(f"  │  💧 Humidity     : {humidity:>6.2f} %                       │")
    print(f"  │  🥵 Heat Index   : {heat_index:>6.2f} °C  (Feels Like)       │")
    print(f"  └{'─' * 50}┘")

    for alert in alerts:
        alevel = alert.get("level", "")
        aicon = alert.get("icon", "⚠️")
        if "HUMIDITY" in alevel:
            print(f"  {aicon} ALERT: {alevel} — Humidity: {alert['humidity']}%")
        else:
            print(
                f"  {aicon} ALERT: {alevel} — Temp: {alert['temp']}°C at {alert['time']}"
            )


def display_stats(logger, alert_system):
    stats = logger.get_stats()
    if not stats:
        print("  No data yet.")
        return

    print(f"\n  📈 STATISTICS ({stats['count']} readings)")
    print("  " + "─" * 45)
    print(f"  🌡️  Avg Temperature  : {stats['temp_avg']:>6.2f} °C")
    print(f"  ⬆️  Max Temperature  : {stats['temp_max']:>6.2f} °C")
    print(f"  ⬇️  Min Temperature  : {stats['temp_min']:>6.2f} °C")
    print(f"  📊 Temp Range       : {stats['temp_range']:>6.2f} °C")
    print(f"  💧 Avg Humidity     : {stats['humidity_avg']:>6.2f} %")
    print(f"  ⚠️  Total Alerts     : {len(alert_system.alert_log)}")
    print("  " + "─" * 45)
    print(f"  Alert Breakdown:")
    for level, count in alert_system.alert_counts.items():
        if count > 0:
            icon = ALERTS.get(level, {}).get("icon", "⚠️")
            print(f"    {icon} {level:<15}: {count}")


def display_menu():
    print("""
  OPTIONS:
  [1] Start live monitoring (10 readings)
  [2] Single reading
  [3] View statistics
  [4] View temperature chart
  [5] View humidity chart
  [6] Save report
  [7] Run full simulation (50 readings)
  [q] Quit
""")


# ── Main ──────────────────────────────────────────────────
def main():
    clear()
    display_banner()

    sensor = DHT22Sensor()
    alert_system = AlertSystem()
    logger = DataLogger()

    print(f"\n  ✅ Sensor initialized: {CONFIG['sensor_id']}")
    print(f"  📍 Location: {CONFIG['location']}")
    print(f"  📁 Logging to: {CONFIG['log_file']}")
    print(f"\n  ⚠️  ALERT THRESHOLDS:")
    print(f"    Critical High : ≥ {CONFIG['temp_critical_high']}°C")
    print(f"    High          : ≥ {CONFIG['temp_max_normal']}°C")
    print(
        f"    Normal        : {CONFIG['temp_min_normal']}–{CONFIG['temp_max_normal']}°C"
    )
    print(f"    Low           : ≤ {CONFIG['temp_min_normal']}°C")
    print(f"    Critical Low  : ≤ {CONFIG['temp_critical_low']}°C")

    display_menu()

    reading_num = 0

    while True:
        try:
            choice = input("\n  Enter option: ").strip().lower()

            if choice == "q":
                if logger.readings:
                    path = logger.save_report(alert_system)
                    print(f"\n  💾 Final report saved: {path}")
                print(f"\n  👋 Goodbye! Total readings: {reading_num}")
                break

            elif choice in ["1", "2", "7"]:
                count = 10 if choice == "1" else 1 if choice == "2" else 50
                interval = CONFIG["update_interval"] if count > 1 else 0

                print(
                    f"\n  🔄 {'Running' if count > 1 else 'Taking'} "
                    f"{count} reading{'s' if count > 1 else ''}...\n"
                )

                for i in range(count):
                    temp, humidity, status = sensor.read()

                    if status == "SENSOR_ERROR":
                        print(f"  ⚠️  [{i+1}/{count}] Sensor error — retrying...")
                        continue

                    heat_index = calculate_heat_index(temp, humidity)
                    level, alerts = alert_system.check(temp, humidity)
                    logger.log(temp, humidity, heat_index, level, status)
                    reading_num += 1

                    display_reading(
                        temp, humidity, heat_index, level, alerts, reading_num
                    )

                    if count > 1 and i < count - 1:
                        print(
                            f"  ⏳ Next reading in {interval}s... " f"(Ctrl+C to stop)",
                            end="\r",
                        )
                        time.sleep(interval)

                print(f"\n  ✅ Done! {count} readings completed.")

            elif choice == "3":
                display_stats(logger, alert_system)

            elif choice == "4":
                draw_ascii_chart(logger.readings, "temp", "Temperature (°C)")

            elif choice == "5":
                draw_ascii_chart(logger.readings, "humidity", "Humidity (%)")

            elif choice == "6":
                if not logger.readings:
                    print("  ⚠️  No data to save yet. Take some readings first.")
                else:
                    path = logger.save_report(alert_system)
                    print(f"  ✅ Report saved: {path}")
                    print(f"  ✅ CSV log     : {CONFIG['log_file']}")

            elif choice == "menu":
                display_menu()

            else:
                print("  ⚠️  Invalid option. Type 'menu' to see options.")

        except KeyboardInterrupt:
            print("\n\n  ⏹️  Monitoring stopped.")
            if logger.readings:
                path = logger.save_report(alert_system)
                print(f"  💾 Report saved: {path}")
            break


if __name__ == "__main__":
    main()


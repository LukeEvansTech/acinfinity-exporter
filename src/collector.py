"""Data collector for AC Infinity metrics."""

import logging
import threading
import time
from typing import Any

from . import metrics
from .client import ACInfinityClient

logger = logging.getLogger(__name__)

# Sensor type mappings
SENSOR_TYPE_PROBE_TEMP_F = 1
SENSOR_TYPE_PROBE_TEMP_C = 2
SENSOR_TYPE_PROBE_HUMIDITY = 3
SENSOR_TYPE_PROBE_VPD = 4
SENSOR_TYPE_CTRL_TEMP_F = 5
SENSOR_TYPE_CTRL_TEMP_C = 6
SENSOR_TYPE_CTRL_HUMIDITY = 7
SENSOR_TYPE_CTRL_VPD = 8
SENSOR_TYPE_CO2 = 9
SENSOR_TYPE_LIGHT = 10
SENSOR_TYPE_SOIL = 12

SENSOR_TYPE_NAMES = {
    SENSOR_TYPE_PROBE_TEMP_F: "probe_temp",
    SENSOR_TYPE_PROBE_TEMP_C: "probe_temp",
    SENSOR_TYPE_PROBE_HUMIDITY: "probe_humidity",
    SENSOR_TYPE_PROBE_VPD: "probe_vpd",
    SENSOR_TYPE_CTRL_TEMP_F: "ctrl_temp",
    SENSOR_TYPE_CTRL_TEMP_C: "ctrl_temp",
    SENSOR_TYPE_CTRL_HUMIDITY: "ctrl_humidity",
    SENSOR_TYPE_CTRL_VPD: "ctrl_vpd",
    SENSOR_TYPE_CO2: "co2",
    SENSOR_TYPE_LIGHT: "light",
    SENSOR_TYPE_SOIL: "soil",
}

TEMPERATURE_SENSORS = {
    SENSOR_TYPE_PROBE_TEMP_F,
    SENSOR_TYPE_PROBE_TEMP_C,
    SENSOR_TYPE_CTRL_TEMP_F,
    SENSOR_TYPE_CTRL_TEMP_C,
}

HUMIDITY_SENSORS = {
    SENSOR_TYPE_PROBE_HUMIDITY,
    SENSOR_TYPE_CTRL_HUMIDITY,
}

VPD_SENSORS = {
    SENSOR_TYPE_PROBE_VPD,
    SENSOR_TYPE_CTRL_VPD,
}

FAHRENHEIT_SENSORS = {
    SENSOR_TYPE_PROBE_TEMP_F,
    SENSOR_TYPE_CTRL_TEMP_F,
}


def fahrenheit_to_celsius(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (f - 32) * 5 / 9


def scale_value(value: int | float, precision: int) -> float:
    """Scale value based on precision (decimal places)."""
    if precision <= 0:
        return float(value)
    return value / (10 ** precision)


class ACInfinityCollector:
    """Collects metrics from AC Infinity API."""

    def __init__(self, client: ACInfinityClient, poll_interval: int = 60) -> None:
        self.client = client
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._tracked_labels: dict[str, set[tuple]] = {
            "controller": set(),
            "device": set(),
            "sensor_temp": set(),
            "sensor_humidity": set(),
            "sensor_vpd": set(),
            "sensor_co2": set(),
            "sensor_light": set(),
            "sensor_soil": set(),
        }

    def start(self) -> None:
        """Start the background collection thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Started collector thread with %ds interval", self.poll_interval)

    def stop(self) -> None:
        """Stop the background collection thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        """Main collection loop."""
        while not self._stop_event.is_set():
            self.collect()
            self._stop_event.wait(self.poll_interval)

    def _clear_stale_metrics(
        self,
        current_labels: set[tuple],
        tracked_key: str,
        *gauges: Any,
    ) -> None:
        """Remove metrics for labels that no longer exist."""
        stale = self._tracked_labels[tracked_key] - current_labels
        for labels in stale:
            for gauge in gauges:
                try:
                    gauge.remove(*labels)
                except KeyError:
                    pass
        self._tracked_labels[tracked_key] = current_labels

    def collect(self) -> None:
        """Collect metrics from AC Infinity API."""
        logger.debug("Starting metrics collection")
        start_time = time.time()

        devices = self.client.get_devices()

        if not devices:
            metrics.last_scrape_success.set(0)
            metrics.last_scrape_timestamp.set(start_time)
            logger.warning("No devices returned from API")
            return

        current_controllers: set[tuple] = set()
        current_devices: set[tuple] = set()
        current_sensor_temp: set[tuple] = set()
        current_sensor_humidity: set[tuple] = set()
        current_sensor_vpd: set[tuple] = set()
        current_sensor_co2: set[tuple] = set()
        current_sensor_light: set[tuple] = set()
        current_sensor_soil: set[tuple] = set()

        for device in devices:
            controller_id = str(device.get("devId", ""))
            controller_name = device.get("devName", "Unknown")
            device_info_data = device.get("deviceInfo", {})

            if not controller_id:
                continue

            labels = (controller_id, controller_name)
            current_controllers.add(labels)

            # Controller info metric
            metrics.controller_info.labels(*labels).set(1)

            # Controller temperature (divide by 100 for Celsius)
            temp = device_info_data.get("temperature")
            if temp is not None:
                metrics.controller_temperature.labels(*labels).set(temp / 100)

            # Controller humidity (divide by 100 for percentage)
            humidity = device_info_data.get("humidity")
            if humidity is not None:
                metrics.controller_humidity.labels(*labels).set(humidity / 100)

            # Controller VPD (divide by 100 for kPa)
            vpd = device_info_data.get("vpd")
            if vpd is not None:
                metrics.controller_vpd.labels(*labels).set(vpd / 100)

            # Process ports (connected devices)
            ports = device_info_data.get("ports") or []
            for port_data in ports:
                port_num = str(port_data.get("port", ""))
                port_name = port_data.get("portName", "Unknown")

                if not port_num:
                    continue

                port_labels = (controller_id, port_num, port_name)
                current_devices.add(port_labels)

                metrics.device_info.labels(*port_labels).set(1)

                # Device speed (speak field, 0-10)
                speed = port_data.get("speak")
                if speed is not None:
                    metrics.device_speed.labels(*port_labels).set(speed)

                # Device online status
                online = port_data.get("online")
                if online is not None:
                    metrics.device_online.labels(*port_labels).set(1 if online else 0)

                # Device state
                state = port_data.get("state")
                if state is not None:
                    metrics.device_state.labels(*port_labels).set(state)

            # Process sensors
            sensors = device_info_data.get("sensors") or []
            for sensor in sensors:
                self._process_sensor(
                    sensor,
                    controller_id,
                    current_sensor_temp,
                    current_sensor_humidity,
                    current_sensor_vpd,
                    current_sensor_co2,
                    current_sensor_light,
                    current_sensor_soil,
                )

        # Clear stale metrics
        self._clear_stale_metrics(
            current_controllers,
            "controller",
            metrics.controller_info,
            metrics.controller_temperature,
            metrics.controller_humidity,
            metrics.controller_vpd,
        )
        self._clear_stale_metrics(
            current_devices,
            "device",
            metrics.device_info,
            metrics.device_speed,
            metrics.device_online,
            metrics.device_state,
        )
        self._clear_stale_metrics(
            current_sensor_temp, "sensor_temp", metrics.sensor_temperature
        )
        self._clear_stale_metrics(
            current_sensor_humidity, "sensor_humidity", metrics.sensor_humidity
        )
        self._clear_stale_metrics(current_sensor_vpd, "sensor_vpd", metrics.sensor_vpd)
        self._clear_stale_metrics(current_sensor_co2, "sensor_co2", metrics.sensor_co2)
        self._clear_stale_metrics(
            current_sensor_light, "sensor_light", metrics.sensor_light
        )
        self._clear_stale_metrics(
            current_sensor_soil, "sensor_soil", metrics.sensor_soil
        )

        metrics.last_scrape_success.set(1)
        metrics.last_scrape_timestamp.set(start_time)
        logger.info(
            "Collection complete: %d controllers, %d devices",
            len(current_controllers),
            len(current_devices),
        )

    def _process_sensor(
        self,
        sensor: dict[str, Any],
        controller_id: str,
        current_temp: set[tuple],
        current_humidity: set[tuple],
        current_vpd: set[tuple],
        current_co2: set[tuple],
        current_light: set[tuple],
        current_soil: set[tuple],
    ) -> None:
        """Process a single sensor and update metrics."""
        sensor_type = sensor.get("sensorType")
        sensor_data = sensor.get("sensorData")
        sensor_port = str(sensor.get("sensorPort", sensor.get("port", "0")))
        precision = sensor.get("sensorPrecis", 0)
        unit = sensor.get("sensorUnit", 1)  # 0=F, 1=C

        if sensor_type is None or sensor_data is None:
            return

        sensor_type_name = SENSOR_TYPE_NAMES.get(sensor_type, f"type_{sensor_type}")
        value = scale_value(sensor_data, precision)

        if sensor_type in TEMPERATURE_SENSORS:
            # Convert Fahrenheit to Celsius if needed
            if sensor_type in FAHRENHEIT_SENSORS or unit == 0:
                value = fahrenheit_to_celsius(value)
            labels = (controller_id, sensor_port, sensor_type_name)
            current_temp.add(labels)
            metrics.sensor_temperature.labels(*labels).set(value)

        elif sensor_type in HUMIDITY_SENSORS:
            labels = (controller_id, sensor_port, sensor_type_name)
            current_humidity.add(labels)
            metrics.sensor_humidity.labels(*labels).set(value)

        elif sensor_type in VPD_SENSORS:
            labels = (controller_id, sensor_port, sensor_type_name)
            current_vpd.add(labels)
            metrics.sensor_vpd.labels(*labels).set(value)

        elif sensor_type == SENSOR_TYPE_CO2:
            labels = (controller_id, sensor_port)
            current_co2.add(labels)
            metrics.sensor_co2.labels(*labels).set(value)

        elif sensor_type == SENSOR_TYPE_LIGHT:
            labels = (controller_id, sensor_port)
            current_light.add(labels)
            metrics.sensor_light.labels(*labels).set(value)

        elif sensor_type == SENSOR_TYPE_SOIL:
            labels = (controller_id, sensor_port)
            current_soil.add(labels)
            metrics.sensor_soil.labels(*labels).set(value)

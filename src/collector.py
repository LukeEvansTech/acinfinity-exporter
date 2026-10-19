"""Data collector for AC Infinity metrics."""

import logging
import threading
import time
from typing import Any

from . import metrics
from .client import ACInfinityClient

logger = logging.getLogger(__name__)

# Sensor type ids as reported in the "sensors" array of devInfoListAll.
# Values follow dalinicus/homeassistant-acinfinity, whose fixtures come from
# real AI controller captures; only AI controllers expose this array.
SENSOR_TYPE_PROBE_TEMP_F = 0
SENSOR_TYPE_PROBE_TEMP_C = 1
SENSOR_TYPE_PROBE_HUMIDITY = 2
SENSOR_TYPE_PROBE_VPD = 3
SENSOR_TYPE_CTRL_TEMP_F = 4
SENSOR_TYPE_CTRL_TEMP_C = 5
SENSOR_TYPE_CTRL_HUMIDITY = 6
SENSOR_TYPE_CTRL_VPD = 7
SENSOR_TYPE_SOIL = 10
SENSOR_TYPE_CO2 = 11
SENSOR_TYPE_LIGHT = 12
SENSOR_TYPE_HYDRO_PH = 13
SENSOR_TYPE_HYDRO_EC_US = 14
SENSOR_TYPE_HYDRO_EC_MS = 15
SENSOR_TYPE_HYDRO_TDS_PPM = 16
SENSOR_TYPE_HYDRO_TDS_PPT = 17
SENSOR_TYPE_HYDRO_WATER_TEMP_F = 18
SENSOR_TYPE_HYDRO_WATER_TEMP_C = 19
SENSOR_TYPE_WATER = 20

SENSOR_TYPE_NAMES = {
    SENSOR_TYPE_PROBE_TEMP_F: "probe_temp",
    SENSOR_TYPE_PROBE_TEMP_C: "probe_temp",
    SENSOR_TYPE_PROBE_HUMIDITY: "probe_humidity",
    SENSOR_TYPE_PROBE_VPD: "probe_vpd",
    SENSOR_TYPE_CTRL_TEMP_F: "ctrl_temp",
    SENSOR_TYPE_CTRL_TEMP_C: "ctrl_temp",
    SENSOR_TYPE_CTRL_HUMIDITY: "ctrl_humidity",
    SENSOR_TYPE_CTRL_VPD: "ctrl_vpd",
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
    SENSOR_TYPE_HYDRO_WATER_TEMP_F,
}

WATER_TEMPERATURE_SENSORS = {
    SENSOR_TYPE_HYDRO_WATER_TEMP_F,
    SENSOR_TYPE_HYDRO_WATER_TEMP_C,
}

# Hydro EC and TDS arrive in one of two units; both are normalised to the
# smaller unit so each has a single gauge.
UNIT_MULTIPLIERS = {
    SENSOR_TYPE_HYDRO_EC_MS: 1000,  # mS/cm -> uS/cm
    SENSOR_TYPE_HYDRO_TDS_PPT: 1000,  # ppt -> ppm
}

# Which tracked-label set and gauge each single-gauge sensor type feeds.
SIMPLE_SENSOR_GAUGES = {
    SENSOR_TYPE_CO2: ("sensor_co2", metrics.sensor_co2),
    SENSOR_TYPE_LIGHT: ("sensor_light", metrics.sensor_light),
    SENSOR_TYPE_SOIL: ("sensor_soil", metrics.sensor_soil),
    SENSOR_TYPE_HYDRO_PH: ("sensor_hydro_ph", metrics.sensor_hydro_ph),
    SENSOR_TYPE_HYDRO_EC_US: ("sensor_hydro_ec", metrics.sensor_hydro_ec),
    SENSOR_TYPE_HYDRO_EC_MS: ("sensor_hydro_ec", metrics.sensor_hydro_ec),
    SENSOR_TYPE_HYDRO_TDS_PPM: ("sensor_hydro_tds", metrics.sensor_hydro_tds),
    SENSOR_TYPE_HYDRO_TDS_PPT: ("sensor_hydro_tds", metrics.sensor_hydro_tds),
    SENSOR_TYPE_WATER: ("sensor_water", metrics.sensor_water_detected),
}

SENSOR_GAUGES = {
    "sensor_temp": metrics.sensor_temperature,
    "sensor_humidity": metrics.sensor_humidity,
    "sensor_vpd": metrics.sensor_vpd,
    "sensor_hydro_water_temp": metrics.sensor_hydro_water_temperature,
    **dict(SIMPLE_SENSOR_GAUGES.values()),
}

SENSOR_UNIT_FAHRENHEIT = 0


def fahrenheit_to_celsius(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (f - 32) * 5 / 9


def scale_value(value: int | float, precision: int) -> float:
    """Scale a raw sensor integer by its reported precision.

    The API's precision is one more than the number of decimal places, so
    precision 3 means the value was multiplied by 100.
    """
    if precision <= 1:
        return float(value)
    return value / (10 ** (precision - 1))


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
            **{key: set() for key in SENSOR_GAUGES},
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

        current: dict[str, set[tuple]] = {key: set() for key in self._tracked_labels}

        for device in devices:
            controller_id = str(device.get("devId", ""))
            controller_name = device.get("devName", "Unknown")
            device_info_data = device.get("deviceInfo", {})

            if not controller_id:
                continue

            labels = (controller_id, controller_name)
            current["controller"].add(labels)

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

            # Controller VPD (divide by 100 for kPa); the API key is "vpdnums"
            vpd = device_info_data.get("vpdnums")
            if vpd is not None:
                metrics.controller_vpd.labels(*labels).set(vpd / 100)

            # Temperature trend (0=stable, 1=rising, 2=falling)
            t_trend = device_info_data.get("tTrend")
            if t_trend is not None:
                metrics.controller_temperature_trend.labels(*labels).set(t_trend)

            # Humidity trend (0=stable, 1=rising, 2=falling)
            h_trend = device_info_data.get("hTrend")
            if h_trend is not None:
                metrics.controller_humidity_trend.labels(*labels).set(h_trend)

            # Controller mode
            cur_mode = device_info_data.get("curMode")
            if cur_mode is not None:
                metrics.controller_mode.labels(*labels).set(cur_mode)

            # Last seen timestamp - use current time when we successfully get data
            metrics.controller_last_seen.labels(*labels).set(start_time)

            # Version info (firmware, hardware, wifi)
            firmware_version = device.get("firmwareVersion", "unknown")
            hardware_version = device.get("hardwareVersion", "unknown")
            wifi_name = device.get("wifiName", "unknown")
            metrics.controller_version_info.labels(
                controller_id,
                controller_name,
                firmware_version,
                hardware_version,
                wifi_name,
            ).set(1)

            # Process ports (connected devices); standalone fans report null
            ports = device_info_data.get("ports") or []
            for port_data in ports:
                port_num = str(port_data.get("port", ""))
                port_name = port_data.get("portName", "Unknown")

                if not port_num:
                    continue

                port_labels = (controller_id, port_num, port_name)
                current["device"].add(port_labels)

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

                # Device mode
                port_mode = port_data.get("curMode")
                if port_mode is not None:
                    metrics.device_mode.labels(*port_labels).set(port_mode)

                # Device connected (based on portResistance - 65535 means not connected)
                port_resistance = port_data.get("portResistance")
                if port_resistance is not None:
                    connected = 0 if port_resistance == 65535 else 1
                    metrics.device_connected.labels(*port_labels).set(connected)

                # Overcurrent status
                overcurrent = port_data.get("overcurrentStatus")
                if overcurrent is not None:
                    metrics.device_overcurrent.labels(*port_labels).set(overcurrent)

                # Abnormal state
                abnormal = port_data.get("abnormalState")
                if abnormal is not None:
                    metrics.device_abnormal.labels(*port_labels).set(abnormal)

            # Process sensors (AI controllers only)
            sensors = device_info_data.get("sensors") or []
            for sensor in sensors:
                self._process_sensor(sensor, controller_id, current)

        # Clear stale metrics
        self._clear_stale_metrics(
            current["controller"],
            "controller",
            metrics.controller_info,
            metrics.controller_temperature,
            metrics.controller_humidity,
            metrics.controller_vpd,
            metrics.controller_temperature_trend,
            metrics.controller_humidity_trend,
            metrics.controller_mode,
            metrics.controller_last_seen,
        )
        self._clear_stale_metrics(
            current["device"],
            "device",
            metrics.device_info,
            metrics.device_speed,
            metrics.device_online,
            metrics.device_state,
            metrics.device_mode,
            metrics.device_connected,
            metrics.device_overcurrent,
            metrics.device_abnormal,
        )
        for key, gauge in SENSOR_GAUGES.items():
            self._clear_stale_metrics(current[key], key, gauge)

        metrics.last_scrape_success.set(1)
        metrics.last_scrape_timestamp.set(start_time)
        logger.info(
            "Collection complete: %d controllers, %d devices",
            len(current["controller"]),
            len(current["device"]),
        )

    @staticmethod
    def _process_sensor(
        sensor: dict[str, Any],
        controller_id: str,
        current: dict[str, set[tuple]],
    ) -> None:
        """Process a single sensor and update metrics."""
        sensor_type = sensor.get("sensorType")
        sensor_data = sensor.get("sensorData")
        sensor_port = str(sensor.get("accessPort", "0"))
        precision = sensor.get("sensorPrecision", 1)
        unit = sensor.get("sensorUnit")

        if sensor_type is None or sensor_data is None:
            return

        value = scale_value(sensor_data, precision) * UNIT_MULTIPLIERS.get(
            sensor_type, 1
        )

        if (
            sensor_type in TEMPERATURE_SENSORS
            or sensor_type in WATER_TEMPERATURE_SENSORS
        ):
            is_fahrenheit = (
                unit == SENSOR_UNIT_FAHRENHEIT
                if unit is not None
                else sensor_type in FAHRENHEIT_SENSORS
            )
            if is_fahrenheit:
                value = round(fahrenheit_to_celsius(value), max(precision - 1, 0))

        if sensor_type in TEMPERATURE_SENSORS:
            key, gauge = "sensor_temp", metrics.sensor_temperature
        elif sensor_type in HUMIDITY_SENSORS:
            key, gauge = "sensor_humidity", metrics.sensor_humidity
        elif sensor_type in VPD_SENSORS:
            key, gauge = "sensor_vpd", metrics.sensor_vpd
        elif sensor_type in WATER_TEMPERATURE_SENSORS:
            key, gauge = (
                "sensor_hydro_water_temp",
                metrics.sensor_hydro_water_temperature,
            )
        elif sensor_type in SIMPLE_SENSOR_GAUGES:
            key, gauge = SIMPLE_SENSOR_GAUGES[sensor_type]
        else:
            logger.debug("Ignoring unknown sensor type %s", sensor_type)
            return

        labels: tuple[str, ...]
        if key in ("sensor_temp", "sensor_humidity", "sensor_vpd"):
            labels = (controller_id, sensor_port, SENSOR_TYPE_NAMES[sensor_type])
        else:
            labels = (controller_id, sensor_port)

        current[key].add(labels)
        gauge.labels(*labels).set(value)

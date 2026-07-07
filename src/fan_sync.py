"""AC Infinity Fan Sync Controller.

Syncs intake fan speed to a percentage of exhaust fan speed.
Designed to run as a standalone service in Kubernetes.
"""

import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

API_BASE = "http://www.acinfinityserver.com"
LOGIN_ENDPOINT = f"{API_BASE}/api/user/appUserLogin"
DEVICES_ENDPOINT = f"{API_BASE}/api/user/devInfoListAll"
GET_SETTINGS_ENDPOINT = f"{API_BASE}/api/dev/getdevModeSettingList"
SET_MODE_ENDPOINT = f"{API_BASE}/api/dev/addDevMode"


@dataclass
class FanConfig:
    """Configuration for a fan to sync."""

    controller_name: str  # Name of the controller (e.g., "Garage Main Rack")
    port: int  # Port number on the controller (1-4)


@dataclass
class SyncConfig:
    """Configuration for fan sync behavior."""

    exhaust: FanConfig
    intake: FanConfig
    intake_ratio: float = 0.85  # Intake runs at 85% of exhaust speed
    min_speed: int = 0  # Minimum speed (0-10)
    max_speed: int = 10  # Maximum speed (0-10)


class ACInfinityFanSync:
    """Syncs intake fan speed based on exhaust fan speed."""

    def __init__(self, email: str, password: str, sync_config: SyncConfig) -> None:
        self.email = email
        self.password = password
        self.sync_config = sync_config
        self.token: str | None = None
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
        })
        self._running = True

    def authenticate(self) -> bool:
        """Authenticate with AC Infinity API and get token."""
        try:
            # Note: API has typo - appPasswordl with 'l'
            # Password truncated to 25 chars per API limitation
            response = self.session.post(
                LOGIN_ENDPOINT,
                data={
                    "appEmail": self.email,
                    "appPasswordl": self.password[:25],
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 200:
                logger.error("Authentication failed: %s", data.get("msg", "Unknown error"))
                return False

            self.token = data.get("data", {}).get("appId")
            if not self.token:
                logger.error("No appId in authentication response")
                return False

            logger.info("Successfully authenticated with AC Infinity API")
            return True

        except requests.RequestException as e:
            logger.error("Authentication request failed: %s", e)
            return False

    def get_devices(self) -> list[dict[str, Any]]:
        """Fetch all devices from AC Infinity API."""
        if not self.token:
            if not self.authenticate():
                return []

        try:
            response = self.session.post(
                DEVICES_ENDPOINT,
                data={"userId": self.token},
                headers={"token": self.token},
                timeout=30,
            )

            if response.status_code == 401:
                logger.warning("Token expired, re-authenticating")
                if not self.authenticate():
                    return []
                return self.get_devices()

            response.raise_for_status()
            data = response.json()

            if data.get("code") != 200:
                logger.error("Failed to get devices: %s", data.get("msg", "Unknown error"))
                return []

            return data.get("data", [])

        except requests.RequestException as e:
            logger.error("Failed to fetch devices: %s", e)
            return []

    def find_controller(
        self, devices: list[dict[str, Any]], controller_name: str
    ) -> dict[str, Any] | None:
        """Find a controller by name."""
        for device in devices:
            if device.get("devName") == controller_name:
                return device
        return None

    def get_port_speed(self, controller: dict[str, Any], port: int) -> int | None:
        """Get current speed of a port on a controller."""
        device_info = controller.get("deviceInfo", {})
        ports = device_info.get("ports", [])

        for port_data in ports:
            if port_data.get("port") == port:
                return port_data.get("speak")

        return None

    def get_device_settings(self, controller_id: str, port: int) -> dict[str, Any] | None:
        """Get current settings for a device port."""
        if not self.token:
            return None

        try:
            response = self.session.post(
                GET_SETTINGS_ENDPOINT,
                data={"devId": controller_id, "port": port},
                headers={"token": self.token},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 200:
                logger.error("Failed to get settings: %s", data.get("msg"))
                return None

            return data.get("data", {})

        except requests.RequestException as e:
            logger.error("Failed to get device settings: %s", e)
            return None

    def set_device_speed(
        self, controller_id: str, port: int, speed: int
    ) -> bool:
        """Set the speed of a device.

        This sets the device to ON mode with the specified speed.
        Speed is 0-10 for Cloudline fans.
        """
        if not self.token:
            if not self.authenticate():
                return False

        # Get current settings first
        settings = self.get_device_settings(controller_id, port)
        if not settings:
            logger.error("Cannot set speed: failed to get current settings")
            return False

        # Build the update payload with required fields
        # Key fields for speed control:
        # - atType: 2 = ON mode (manual speed)
        # - onSpead: speed when in ON mode (0-10)
        # - speak: current speed display

        # Copy existing settings and update speed-related fields
        payload = {
            "devId": controller_id,
            "port": port,
            "atType": 2,  # ON mode for manual speed control
            "onSpead": speed,  # Target speed (note the typo in API)
            "speak": speed,
        }

        # Include other required fields from existing settings
        required_fields = [
            "modeSetid", "externalPort", "surplus", "offSpead",
            "loadState", "loadType", "devHt", "devLt", "devHh", "devLh",
            "activeHt", "activeLt", "activeHh", "activeLh",
            "acitveTimerOn", "acitveTimerOff",
            "activeCycleOn", "activeCycleOff",
            "schedStartTime", "schedEndtTime",
        ]

        for field in required_fields:
            if field in settings:
                payload[field] = settings[field]

        try:
            # API expects query string parameters
            url = f"{SET_MODE_ENDPOINT}?{urlencode(payload)}"
            response = self.session.post(
                url,
                headers={"token": self.token},
                timeout=30,
            )

            if response.status_code == 401:
                logger.warning("Token expired during set, re-authenticating")
                if not self.authenticate():
                    return False
                return self.set_device_speed(controller_id, port, speed)

            response.raise_for_status()
            data = response.json()

            if data.get("code") != 200:
                logger.error("Failed to set speed: %s", data.get("msg"))
                return False

            logger.info("Successfully set port %d speed to %d", port, speed)
            return True

        except requests.RequestException as e:
            logger.error("Failed to set device speed: %s", e)
            return False

    def calculate_intake_speed(self, exhaust_speed: int) -> int:
        """Calculate intake speed based on exhaust speed and ratio."""
        raw_speed = exhaust_speed * self.sync_config.intake_ratio
        speed = int(round(raw_speed))

        # Clamp to min/max
        speed = max(self.sync_config.min_speed, min(self.sync_config.max_speed, speed))

        return speed

    def sync_once(self) -> bool:
        """Perform one sync cycle."""
        devices = self.get_devices()
        if not devices:
            logger.error("No devices found")
            return False

        # Find exhaust controller
        exhaust_controller = self.find_controller(
            devices, self.sync_config.exhaust.controller_name
        )
        if not exhaust_controller:
            logger.error(
                "Exhaust controller '%s' not found",
                self.sync_config.exhaust.controller_name,
            )
            return False

        # Find intake controller
        intake_controller = self.find_controller(
            devices, self.sync_config.intake.controller_name
        )
        if not intake_controller:
            logger.error(
                "Intake controller '%s' not found",
                self.sync_config.intake.controller_name,
            )
            return False

        # Get current exhaust speed
        exhaust_speed = self.get_port_speed(
            exhaust_controller, self.sync_config.exhaust.port
        )
        if exhaust_speed is None:
            logger.error(
                "Could not read exhaust speed from port %d",
                self.sync_config.exhaust.port,
            )
            return False

        # Get current intake speed
        current_intake_speed = self.get_port_speed(
            intake_controller, self.sync_config.intake.port
        )

        # Calculate target intake speed
        target_intake_speed = self.calculate_intake_speed(exhaust_speed)

        logger.info(
            "Exhaust speed: %d, Current intake: %s, Target intake: %d",
            exhaust_speed,
            current_intake_speed,
            target_intake_speed,
        )

        # Only update if speed changed
        if current_intake_speed == target_intake_speed:
            logger.debug("Intake speed already at target, no change needed")
            return True

        # Set intake speed
        intake_id = str(intake_controller.get("devId"))
        return self.set_device_speed(
            intake_id,
            self.sync_config.intake.port,
            target_intake_speed,
        )

    def run(self, interval: int = 60) -> None:
        """Run the sync loop."""
        logger.info(
            "Starting fan sync: %s port %d -> %s port %d at %.0f%% ratio",
            self.sync_config.exhaust.controller_name,
            self.sync_config.exhaust.port,
            self.sync_config.intake.controller_name,
            self.sync_config.intake.port,
            self.sync_config.intake_ratio * 100,
        )
        logger.info("Sync interval: %ds", interval)

        while self._running:
            try:
                self.sync_once()
            except Exception as e:
                logger.exception("Error during sync: %s", e)

            # Sleep in small increments to allow quick shutdown
            for _ in range(interval):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("Fan sync stopped")

    def stop(self) -> None:
        """Stop the sync loop."""
        self._running = False


def get_env(name: str, default: str | None = None, required: bool = False) -> str:
    """Get environment variable with optional default."""
    value = os.environ.get(name, default)
    if required and not value:
        logger.error("Required environment variable %s not set", name)
        sys.exit(1)
    return value or ""


def main() -> None:
    """Main entry point."""
    # Configure logging
    log_level = get_env("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get credentials from environment
    email = get_env("ACINFINITY_EMAIL", required=True)
    password = get_env("ACINFINITY_PASSWORD", required=True)

    # Get sync configuration from environment
    exhaust_controller = get_env("EXHAUST_CONTROLLER", required=True)
    exhaust_port = int(get_env("EXHAUST_PORT", "1"))
    intake_controller = get_env("INTAKE_CONTROLLER", required=True)
    intake_port = int(get_env("INTAKE_PORT", "1"))
    intake_ratio = float(get_env("INTAKE_RATIO", "0.85"))
    sync_interval = int(get_env("SYNC_INTERVAL", "60"))

    # Build config
    sync_config = SyncConfig(
        exhaust=FanConfig(controller_name=exhaust_controller, port=exhaust_port),
        intake=FanConfig(controller_name=intake_controller, port=intake_port),
        intake_ratio=intake_ratio,
    )

    # Create sync controller
    fan_sync = ACInfinityFanSync(email, password, sync_config)

    # Initial authentication
    if not fan_sync.authenticate():
        logger.error("Initial authentication failed")
        sys.exit(1)

    # Handle shutdown signals
    def shutdown(signum, frame):
        logger.info("Received signal %d, shutting down", signum)
        fan_sync.stop()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Run sync loop
    fan_sync.run(interval=sync_interval)


if __name__ == "__main__":
    main()

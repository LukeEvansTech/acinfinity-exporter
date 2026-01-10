"""AC Infinity API client."""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_BASE = "http://www.acinfinityserver.com/api"
LOGIN_ENDPOINT = f"{API_BASE}/user/appUserLogin"
DEVICES_ENDPOINT = f"{API_BASE}/user/devInfoListAll"


class ACInfinityClient:
    """Client for AC Infinity cloud API."""

    def __init__(self, email: str, password: str) -> None:
        self.email = email
        self.password = password
        self.token: str | None = None
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
        })

    def authenticate(self) -> bool:
        """Authenticate with AC Infinity API and get token."""
        try:
            # Note: API has typo - appPasswordl with 'l'
            response = self.session.post(
                LOGIN_ENDPOINT,
                data={
                    "appEmail": self.email,
                    "appPasswordl": self.password,
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

            # Re-auth on 401
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

            devices = data.get("data", [])
            logger.debug("Retrieved %d devices", len(devices))
            return devices

        except requests.RequestException as e:
            logger.error("Failed to fetch devices: %s", e)
            return []

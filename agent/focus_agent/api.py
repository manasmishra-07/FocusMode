import requests
from urllib.parse import urlparse


class Revoked(Exception):
    pass


class API:
    def __init__(self, url):
        parsed = urlparse(url)
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname in ["127.0.0.1", "localhost"]
        ):
            raise ValueError("Backend must use HTTPS except on loopback")
        self.url = url.rstrip("/")
        self.credentials = None

    def request(self, method, path, data=None, jwt=None):
        headers = {}
        if jwt:
            headers["Authorization"] = "Bearer " + jwt
        elif self.credentials:
            headers.update(
                {
                    "X-Device-ID": self.credentials["device_id"],
                    "X-Device-Key": self.credentials["credential"],
                }
            )
        response = requests.request(
            method, self.url + path, json=data, headers=headers, timeout=5
        )
        if response.status_code in (401, 403) and not jwt:
            raise Revoked("Device credential was revoked")
        response.raise_for_status()
        return response.json()["data"]

    def identity(self, jwt):
        return self.request("GET", "/auth/me", jwt=jwt)

    def register(self, jwt, name, mode):
        return self.request(
            "POST", "/devices/pair", {"name": name, "os": mode}, jwt=jwt
        )

    def config(self):
        return self.request("GET", "/agent/config")

    def upload(self, event):
        return self.request("POST", "/agent/events", event)

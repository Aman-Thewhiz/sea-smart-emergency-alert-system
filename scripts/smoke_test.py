import json
import os
import sys
from urllib import request


def main() -> int:
    base_url = os.getenv("SEA_BASE_URL", "http://127.0.0.1:5000")
    payload = {"latitude": 37.7749, "longitude": -122.4194}
    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        f"{base_url}/send_alert",
        data=data,
        headers={"Content-Type": "application/json", "X-Request-ID": "smoke-test"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            print(f"Status: {response.status}")
            print(body)
            return 0
    except Exception as exc:
        print(f"Smoke test failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

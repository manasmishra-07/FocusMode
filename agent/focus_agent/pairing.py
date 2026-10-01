import secrets
import hashlib
import time


class Pairing:
    def __init__(self):
        self.rotate()

    def rotate(self):
        self.code = f"{secrets.randbelow(1000000):06d}"
        self.digest = hashlib.sha256(self.code.encode()).digest()
        self.expires = time.monotonic() + 180
        self.attempts = 0
        self.used = False

    def consume(self, code):
        if self.used or time.monotonic() > self.expires or self.attempts >= 5:
            raise ValueError(
                "Code expired, used, or locked. Generate a new code in the agent."
            )
        self.attempts += 1
        if not isinstance(code, str) or not secrets.compare_digest(
            hashlib.sha256(code.encode()).digest(), self.digest
        ):
            raise ValueError("Incorrect pairing code")
        self.used = True
        self.code = ""
        return True

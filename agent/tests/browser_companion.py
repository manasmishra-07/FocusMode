"""Manual browser test fixture: visible MOCK companion, ephemeral local state.
Prints its locally displayed code to the test terminal, never to the network.
Run from repository root: python agent/tests/browser_companion.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from focus_agent.pairing import Pairing
from focus_agent.ui import launch

original = Pairing.rotate


def test_rotate(self):
    original(self)
    print("LOCAL TEST PAIRING CODE:", self.code, flush=True)


Pairing.rotate = test_rotate
if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="focus-browser-test-") as directory:
        launch(directory, "mock")

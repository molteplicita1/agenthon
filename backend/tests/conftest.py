import os
import sys
import tempfile
from pathlib import Path

import pytest

os.environ["BRAIN_STATE_PATH"] = str(Path(tempfile.mkdtemp()) / "state.json")
os.environ["BRAIN_NO_LLM"] = "1"  # tests never call outside services
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


@pytest.fixture
def c():
    client = TestClient(main.app)
    assert client.post("/demo/reset").status_code == 200
    return client


def H(user):
    return {"X-User-Id": user}

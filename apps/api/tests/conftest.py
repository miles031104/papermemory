from pathlib import Path
import shutil
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path() -> Path:
    path = Path(".pytest-tmp") / "manual" / uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    yield path.resolve()
    shutil.rmtree(path, ignore_errors=True)

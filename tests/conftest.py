"""Корневой conftest.py тестов — добавляет tests/ в sys.path для импорта mock-сервера."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

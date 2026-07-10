from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARSER_DIR = PROJECT_ROOT / 'ParserNecessities'
TRANSFORMATION_SOURCE_DIR = PROJECT_ROOT / 'TransformationEngineNecessities' / 'source'
TRANSFORMATION_TRANSFORMS_DIR = PROJECT_ROOT / 'TransformationEngineNecessities' / 'transforms'

for path in (PROJECT_ROOT, PARSER_DIR):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


class FakeEntry:
    def __init__(self, value: str = ''):
        self.value = value

    def get(self) -> str:
        return self.value


class FakeListbox:
    def __init__(self, values=None):
        self.values = list(values or [])

    def size(self) -> int:
        return len(self.values)

    def get(self, start, end=None):
        if start == 0 and end == 'end':
            return tuple(self.values)
        if isinstance(start, int) and end is None:
            return self.values[start]
        return tuple(self.values)

    def insert(self, index, value):
        self.values.append(value)

    def configure(self, **kwargs):
        return None

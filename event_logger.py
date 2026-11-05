from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class EventLogger:
    csv_path: str
    enabled: bool = True

    _fp: Optional[Any] = None
    _writer: Optional[csv.DictWriter] = None
    _header_written: bool = False

    def _ensure_open(self, fieldnames: list[str]) -> None:
        if not self.enabled:
            return

        if self._fp and self._writer:
            return

        os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
        self._fp = open(self.csv_path, "a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fp, fieldnames=fieldnames, extrasaction="ignore")

        if self._fp.tell() == 0:
            self._writer.writeheader()
            self._header_written = True

    def log(self, row: Dict[str, Any]) -> None:
        if not self.enabled:
            return

        enriched = dict(row)
        enriched.setdefault("ts_unix", time.time())

        fieldnames = sorted(enriched.keys())
        self._ensure_open(fieldnames)
        assert self._writer is not None

        self._writer.writerow(enriched)
        self._fp.flush()  # type: ignore[union-attr]

    def close(self) -> None:
        if self._fp:
            try:
                self._fp.close()
            finally:
                self._fp = None
                self._writer = None

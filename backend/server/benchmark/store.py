"""Simple JSON-on-disk persistence for benchmark results. In-memory cache so the
API can list them without re-reading every file."""

import json
import os
import threading
from pathlib import Path
from .runner import BenchmarkResult


_DIR = Path(os.environ.get("FL_BENCH_DIR", Path.home() / ".flserver" / "benchmarks"))


class BenchmarkStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: dict[str, BenchmarkResult] = {}
        _DIR.mkdir(parents=True, exist_ok=True)
        self._reload()

    def _reload(self) -> None:
        for f in _DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                r = BenchmarkResult(**{k: v for k, v in data.items()
                                       if k in BenchmarkResult.__dataclass_fields__})
                self._cache[r.id] = r
            except Exception:
                continue

    def save(self, result: BenchmarkResult) -> None:
        with self._lock:
            self._cache[result.id] = result
            (_DIR / f"{result.id}.json").write_text(json.dumps(result.asdict(), indent=2))

    def get(self, run_id: str) -> BenchmarkResult | None:
        with self._lock:
            return self._cache.get(run_id)

    def list(self) -> list[dict]:
        with self._lock:
            # return a lightweight summary (no per-round detail) for the index
            return sorted([
                {
                    "id": r.id,
                    "scenario": r.scenario,
                    "final_test_accuracy": r.final_test_accuracy,
                    "final_test_loss": r.final_test_loss,
                    "rounds": len(r.rounds),
                    "status": r.status,
                    "started_at": r.started_at,
                    "finished_at": r.finished_at,
                }
                for r in self._cache.values()
            ], key=lambda x: x.get("started_at") or 0, reverse=True)

    def delete(self, run_id: str) -> bool:
        with self._lock:
            self._cache.pop(run_id, None)
            f = _DIR / f"{run_id}.json"
            if f.exists():
                f.unlink()
                return True
            return False

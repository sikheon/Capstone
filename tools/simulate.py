"""Spin up N simulated FL clients that share the real training stack.

  python tools/simulate.py --server http://localhost:8000 --clients 6 --noniid

Each simulated client is its own thread:
  - provisions credentials,
  - registers as kind="sim" with a fake device profile,
  - heart-beats every few seconds with randomized battery / network /CPU,
  - when /api/heartbeat says "selected for round X", it fetches the global
    weights via /api/round/current, trains on a shard of MNIST, and submits.

Run alongside the backend (uvicorn) and watch the dashboard fill in.
"""

import argparse
import os
import random
import sys
import threading
import time

import numpy as np

# allow `python tools/simulate.py` from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import algorithms, models, datasets       # noqa: E402  (after sys.path tweak)
from client.api import FLApiClient                    # noqa: E402


PROFILES = [
    {"kind": "sim", "os": "Linux",   "arch": "aarch64", "model_hw": "Raspberry Pi 5"},
    {"kind": "sim", "os": "Linux",   "arch": "aarch64", "model_hw": "Jetson Nano"},
    {"kind": "sim", "os": "Android", "arch": "arm64-v8a", "model_hw": "Pixel 7"},
    {"kind": "sim", "os": "Android", "arch": "arm64-v8a", "model_hw": "Galaxy S22"},
    {"kind": "sim", "os": "Linux",   "arch": "x86_64",  "model_hw": "Mini PC"},
]


def fake_flags(rng: random.Random, risk: str = "mixed") -> dict:
    """Per-tick telemetry. `risk` lets demos pin a client to a specific
    DropoutAdvisor band so the dashboard's watchlist actually fills:

      "high"  — battery < 20% & not charging, cell/no network, cpu > 90%
                → rule_based predictor scores ~1.0
      "med"   — cell network OR cpu mildly hot
                → ~0.3
      "low"   — wifi/ethernet, charging, low cpu
                → 0.0
      "mixed" — original random behaviour (default for ad-hoc loads)"""
    if risk == "high":
        return {
            "battery": round(rng.uniform(0.05, 0.18), 2),
            "charging": False,
            "network": rng.choice(["cell", "none"]),
            "cpu_load": round(rng.uniform(0.92, 0.99), 2),
        }
    if risk == "med":
        return {
            "battery": round(rng.uniform(0.3, 0.7), 2),
            "charging": rng.random() < 0.5,
            "network": rng.choice(["cell", "wifi"]),
            "cpu_load": round(rng.uniform(0.6, 0.95), 2),
        }
    if risk == "low":
        return {
            "battery": round(rng.uniform(0.6, 1.0), 2),
            "charging": True,
            "network": rng.choice(["wifi", "ethernet"]),
            "cpu_load": round(rng.uniform(0.05, 0.4), 2),
        }
    # mixed (original)
    return {
        "battery": round(rng.uniform(0.1, 1.0), 2),
        "charging": rng.random() < 0.6,
        "network": rng.choice(["wifi", "wifi", "ethernet", "cell", "cell", "none"]),
        "cpu_load": round(rng.uniform(0.05, 0.95), 2),
    }


def shard_indices(client_idx: int, total_clients: int, dataset_size: int,
                  noniid: bool) -> list[int]:
    rng = np.random.default_rng(client_idx)
    if noniid:
        shards = total_clients * 2
        shard_size = dataset_size // shards
        chosen = rng.choice(shards, size=2, replace=False)
        idx = np.concatenate([np.arange(s * shard_size, (s + 1) * shard_size) for s in chosen])
    else:
        idx = np.arange(dataset_size)
        rng.shuffle(idx)
        idx = idx[client_idx::total_clients]
    return idx.tolist()


def assign_risk(idx: int, total: int, risk_high: int, risk_med: int) -> str:
    """Deterministic per-client risk band so the dashboard stays stable across
    runs. First `risk_high` indices are 'high', next `risk_med` are 'med', rest 'low'."""
    if idx < risk_high:                   return "high"
    if idx < risk_high + risk_med:        return "med"
    return "low"


def run_client(idx: int, total: int, server: str, algo_name: str, model_name: str,
               dataset_name: str, noniid: bool, risk: str, stop: threading.Event) -> None:
    rng = random.Random(idx * 7919)
    profile = dict(PROFILES[idx % len(PROFILES)])

    api = FLApiClient(server)
    api.provision(suggested_id=f"sim-{idx:03d}")

    info = {**profile, "client_id": api.client_id,
            "hostname": f"sim-{idx:03d}",
            "app_version": "simulate-0.1.0",
            "metadata": {"seed": idx}}
    try: api.register(info)
    except Exception as e: print(f"[sim {idx}] register failed: {e}")

    algo = algorithms.get(algo_name)
    runner = models.get(model_name)
    dataset = datasets.get(dataset_name)
    my_idx = shard_indices(idx, total, dataset.size(), noniid)

    last_round = -1
    last_async = 0.0
    print(f"[sim {idx}] up - {profile['model_hw']} - shard size {len(my_idx)} - risk={risk}")

    while not stop.is_set():
        flags = fake_flags(rng, risk)
        try:
            r = api.heartbeat({"client_id": api.client_id, "kind": "sim", **flags})
            state = r.get("orchestrator_state")
            mode = r.get("mode")
            round_num = r.get("round")
            selected = r.get("selected_for_round")
            epochs = int(r.get("local_epochs") or 1)
            if state == "running":
                if mode == "sync" and selected and round_num != last_round:
                    last_round = round_num
                    info_r = api.current_round()
                    new_w, metrics = algo.local_train(runner, info_r["weights"],
                                                     dataset.load(my_idx, batch_size=32), epochs)
                    api.submit_update({"client_id": api.client_id, "weights": new_w,
                                       "num_samples": len(my_idx), "metrics": metrics})
                    print(f"[sim {idx}] r={round_num} loss={metrics['loss']:.3f} "
                          f"acc={metrics['accuracy']:.3f}")
                elif mode == "async" and time.time() - last_async > rng.uniform(8, 15):
                    last_async = time.time()
                    info_r = api.current_round()
                    new_w, metrics = algo.local_train(runner, info_r["weights"],
                                                     dataset.load(my_idx, batch_size=32), epochs)
                    api.submit_update({"client_id": api.client_id, "weights": new_w,
                                       "num_samples": len(my_idx), "metrics": metrics})
                    print(f"[sim {idx}] async push loss={metrics['loss']:.3f}")
        except Exception as e:
            print(f"[sim {idx}] hb error: {e}")
        time.sleep(rng.uniform(3, 6))


def main():
    p = argparse.ArgumentParser(description="FL client simulator")
    p.add_argument("--server",  default=os.environ.get("FL_SERVER_URL", "http://localhost:8000"))
    p.add_argument("--clients", type=int, default=4)
    p.add_argument("--algo",    default="fedavg")
    p.add_argument("--model",   default="cnn_mnist")
    p.add_argument("--dataset", default="mnist")
    p.add_argument("--noniid",  action="store_true",
                   help="non-IID sharding (2 classes per client)")
    p.add_argument("--risky", type=int, default=0,
                   help="how many of --clients to pin to a HIGH dropout-risk profile "
                        "(low battery + cell/no net + saturated cpu). Demos the dashboard's "
                        "이탈 관리 panel + dropout_aware selection.")
    p.add_argument("--risky-med", type=int, default=0,
                   help="how many of --clients to pin to a MEDIUM-risk profile.")
    args = p.parse_args()

    stop = threading.Event()
    threads: list[threading.Thread] = []
    for i in range(args.clients):
        risk = assign_risk(i, args.clients, args.risky, args.risky_med)
        t = threading.Thread(target=run_client,
                             args=(i, args.clients, args.server,
                                   args.algo, args.model, args.dataset, args.noniid, risk, stop),
                             daemon=True)
        t.start(); threads.append(t)

    print(f"\n[*] {args.clients} simulated clients running "
          f"(high={args.risky}, med={args.risky_med}, low={max(0, args.clients - args.risky - args.risky_med)}). "
          f"Ctrl+C to stop.\n")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] stopping simulators...")
        stop.set()
        for t in threads: t.join(timeout=2)


if __name__ == "__main__":
    main()

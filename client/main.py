import argparse
import time
from dataclasses import asdict

from . import algorithms, models, datasets, credentials, collectors
from .api import FLApiClient
from .config import config
from .device_info import collect as collect_device_info
from .reporter import LocalReporter


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FL edge client (Raspberry Pi / Jetson)")
    p.add_argument("--server", default=config.server_url,
                   help="central server URL (overrides FL_SERVER_URL)")
    p.add_argument("--algo", default=config.algorithm)
    p.add_argument("--model", default=config.model)
    p.add_argument("--dataset", default=config.dataset)
    p.add_argument("--epochs", type=int, default=config.local_epochs)
    p.add_argument("--reprovision", action="store_true",
                   help="discard saved credentials and request a fresh pair")
    p.add_argument("--collector", default=config.collector,
                   help="background data collector name (see collectors.available()). "
                        "'none' means train on the static --dataset loader.")
    return p.parse_args()


def ensure_credentials(api: FLApiClient, reprovision: bool) -> None:
    if reprovision:
        credentials.clear()
    cid, secret = credentials.load()
    if cid and secret:
        api.client_id, api.secret = cid, secret
        return
    issued = api.provision()
    credentials.save(issued["client_id"], issued["client_secret"])
    print(f"[edge] provisioned id={issued['client_id']}")


def participate(api: FLApiClient, algo, runner, dataset, epochs: int,
                collector=None) -> None:
    """Pull global weights, train locally, push the update back. When a
    Collector is wired and has enough buffered samples, train on those
    instead of the static dataset (Gboard pattern)."""
    info = api.current_round()
    weights = info.get("weights") or {}
    if not weights:
        print("[edge] no global weights available yet"); return

    batches = None; src_label = dataset.name if hasattr(dataset, "name") else "dataset"; n_samples = dataset.size()
    if collector is not None and collector.name != "none":
        drained = collector.drain(batch_size=32)
        if drained is None:
            print(f"[edge] collector '{collector.name}' buffering "
                  f"{collector.count()}/{collector.min_batch} — skipping"); return
        # Materialise so we can count; drained is a generator over (x, y).
        chunks = list(drained)
        batches = chunks
        n_samples = int(sum(len(y) for _, y in chunks))
        src_label = f"collector:{collector.name}"
    if batches is None:
        batches = dataset.load(batch_size=32)

    new_weights, metrics = algo.local_train(runner, weights, batches, epochs)
    api.submit_update({
        "client_id": api.client_id,
        "weights": new_weights,
        "num_samples": n_samples,
        "metrics": metrics,
    })
    print(f"[edge] round={info.get('round')} done - loss={metrics.get('loss'):.4f} "
          f"acc={metrics.get('accuracy'):.4f}  src={src_label}")


def main() -> None:
    args = parse_args()
    config.server_url = args.server

    api = FLApiClient(args.server)
    ensure_credentials(api, args.reprovision)

    reporter = LocalReporter()

    # Cache plug-in instances so we can switch live (server-driven swap) without
    # re-downloading the dataset each tick.
    algo_cache = {args.algo: algorithms.get(args.algo)}
    model_cache = {args.model: models.get(args.model)}
    dataset_cache = {args.dataset: datasets.get(args.dataset)}
    cur_algo, cur_model, cur_dataset = args.algo, args.model, args.dataset
    algo = algo_cache[cur_algo]
    runner = model_cache[cur_model]
    dataset = dataset_cache[cur_dataset]
    collector = collectors.get(args.collector)

    print(f"[edge] server={args.server} id={api.client_id}")
    print(f"[edge] algo={cur_algo} model={cur_model} dataset={cur_dataset} "
          f"collector={collector.name} samples={dataset.size()}")

    info = collect_device_info(kind="edge")
    info["client_id"] = api.client_id
    try:
        api.register(info)
    except Exception as e:
        print(f"[edge] register failed: {e}")

    def follow_server(srv_algo: str, srv_model: str, srv_dataset: str):
        """If the admin swapped a module on the server, load it locally too so
        we keep training on what the coordinator actually expects."""
        nonlocal algo, runner, dataset, cur_algo, cur_model, cur_dataset
        if srv_algo and srv_algo != cur_algo:
            algo_cache.setdefault(srv_algo, algorithms.get(srv_algo))
            algo = algo_cache[srv_algo]; cur_algo = srv_algo
            print(f"[edge] follow server: algorithm -> {srv_algo}")
        if srv_model and srv_model != cur_model:
            model_cache.setdefault(srv_model, models.get(srv_model))
            runner = model_cache[srv_model]; cur_model = srv_model
            print(f"[edge] follow server: model -> {srv_model}")
        if srv_dataset and srv_dataset != cur_dataset:
            dataset_cache.setdefault(srv_dataset, datasets.get(srv_dataset))
            dataset = dataset_cache[srv_dataset]; cur_dataset = srv_dataset
            print(f"[edge] follow server: dataset -> {srv_dataset} (samples={dataset.size()})")

    last_round = -1
    last_async_at = 0.0
    while True:
        flags = reporter.collect()
        try:
            r = api.heartbeat({"client_id": api.client_id, "kind": "edge", **asdict(flags)})
            state = r.get("orchestrator_state")
            mode = r.get("mode")
            round_num = r.get("round")
            selected = r.get("selected_for_round")
            epochs = int(r.get("local_epochs") or args.epochs)

            follow_server(r.get("algorithm"), r.get("model"), r.get("dataset"))

            if state == "running":
                if mode == "sync" and selected and round_num != last_round:
                    last_round = round_num
                    print(f"[edge] selected for round {round_num} - training {epochs} epoch(s)")
                    participate(api, algo, runner, dataset, epochs, collector)
                elif mode == "async" and time.time() - last_async_at >= 10:
                    last_async_at = time.time()
                    print(f"[edge] async tick - pushing update")
                    participate(api, algo, runner, dataset, epochs, collector)
        except Exception as e:
            print(f"[edge] heartbeat failed: {e}")
        time.sleep(config.heartbeat_sec)


if __name__ == "__main__":
    main()

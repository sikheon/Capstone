import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .core.client_manager import ClientManager
from .core.orchestrator import Orchestrator
from .dropout import DropoutAdvisor
from .api.rest import make_router as make_rest_router
from .api.ws import EventBus, make_router as make_ws_router
from .api.benchmark_api import make_router as make_bench_router
from .benchmark import BenchmarkRunner, BenchmarkStore


def create_app() -> FastAPI:
    app = FastAPI(title="FL Coordinator", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )

    clients = ClientManager()
    orchestrator = Orchestrator(clients)
    advisor = DropoutAdvisor()
    bus = EventBus()
    bench_runner = BenchmarkRunner()
    bench_store = BenchmarkStore()

    app.include_router(make_rest_router(orchestrator, clients, advisor), prefix="/api")
    app.include_router(make_ws_router(bus), prefix="/ws")
    app.include_router(make_bench_router(bench_runner, bench_store, bus), prefix="/api")

    @app.on_event("startup")
    async def _startup():
        loop = asyncio.get_running_loop()
        orchestrator.attach(loop, lambda e, p: bus.publish(e, p))
        # Gboard-style always-on: if FL_AUTO_START is set, kick the orchestrator
        # at boot in that mode so phones can opt-in whenever they're eligible.
        if config.auto_start in ("sync", "async"):
            orchestrator.start(config.auto_start)

    @app.on_event("shutdown")
    async def _shutdown():
        orchestrator.stop()

    app.state.orchestrator = orchestrator
    app.state.clients = clients
    app.state.bus = bus
    app.state.advisor = advisor
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("server.main:app", host=config.host, port=config.port, reload=False)

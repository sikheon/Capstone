# Convenience targets.  Run `make help` to see options.

.PHONY: help backend frontend cli simulate test docker-up docker-down clean

help:
	@echo "Targets:"
	@echo "  backend    — install + run the FastAPI coordinator"
	@echo "  frontend   — install + run the React dashboard (dev server)"
	@echo "  cli        — install flctl globally from ./cli"
	@echo "  simulate   — launch N=6 simulated clients (uses backend/.venv torch)"
	@echo "  test       — pytest backend"
	@echo "  docker-up  — docker compose up --build"
	@echo "  docker-down— docker compose down"
	@echo "  clean      — remove caches"

backend:
	cd backend && python -m venv .venv && \
	  ./.venv/bin/pip install --upgrade pip && \
	  ./.venv/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt && \
	  ./.venv/bin/python -m server.main

frontend:
	cd frontend && npm install && npm run dev

cli:
	cd cli && npm install && npm install -g .

simulate:
	cd backend && ./.venv/bin/python ../tools/simulate.py --clients 6

test:
	cd backend && ./.venv/bin/pytest

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf backend/.pytest_cache frontend/node_modules frontend/dist cli/node_modules

.PHONY: up down ingest pretrain seed health logs shell clean

up:
	docker compose up -d
	@echo "Waiting for services..."
	@sleep 10
	@docker compose ps

down:
	docker compose down

ingest:
	docker compose exec backend python scripts/ingest_historical.py

pretrain:
	docker compose exec backend python scripts/pretrain_lgbm.py

seed:
	docker compose exec backend python scripts/seed_neo4j.py

health:
	docker compose exec backend python scripts/health_check.py

logs:
	docker compose logs -f backend

shell:
	docker compose exec backend bash

clean:
	docker compose down -v
	@echo "All volumes removed."

build:
	docker compose build --no-cache

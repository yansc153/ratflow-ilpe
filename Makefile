.PHONY: build run test clean

build:
	docker compose build

run:
	docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f

test:
	pytest -v

clean:
	docker compose down -v
	rm -f ratflow.db

health:
	curl http://localhost:8080/health

test-discord:
	curl -X POST http://localhost:8080/discord/test

seed:
	python scripts/seed_mock_alert.py

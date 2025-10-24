.PHONY: up down logs producer consumer recommender api frontend

up:
	docker compose up -d

logs:
	docker compose logs -f

down:
	docker compose down -v

producer:
	python src/producer.py --seed-data data/resorts.jsonl

consumer:
	python src/consumer.py

recommender:
	python src/recommender.py --query "family friendly beach resort" --similarity

api:
	uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

.PHONY: help check compose-check test tree up api

help:
	@printf "AI-CryptoFutures-TCP development targets\n"
	@printf "  make check  - run basic repository skeleton checks\n"
	@printf "  make test   - run unit tests\n"
	@printf "  make up     - start the local development stack\n"
	@printf "  make api    - start the API locally without compose\n"
	@printf "  make tree   - print the tracked skeleton tree\n"

check: test compose-check
	@test -f README.md
	@test -f AGENTS.md
	@test -f .env.example
	@test -f docker-compose.yml
	@printf "Skeleton files are present.\n"

test:
	@python3 -m unittest discover -s tests/unit

compose-check:
	@docker compose config >/dev/null

up:
	@docker compose up

api:
	@python3 -m apps.api.server

tree:
	@find . -path ./.git -prune -o -print | sort

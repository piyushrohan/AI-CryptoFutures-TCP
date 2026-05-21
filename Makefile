.PHONY: help check ci compose-check docs-check lint secret-scan test tree up api

help:
	@printf "AI-CryptoFutures-TCP development targets\n"
	@printf "  make check  - run basic repository skeleton checks\n"
	@printf "  make ci     - run CI-equivalent local checks\n"
	@printf "  make lint   - run syntax checks\n"
	@printf "  make test   - run unit tests\n"
	@printf "  make up     - start the local development stack\n"
	@printf "  make api    - start the API locally without compose\n"
	@printf "  make tree   - print the tracked skeleton tree\n"

check: test compose-check docs-check secret-scan
	@test -f README.md
	@test -f AGENTS.md
	@test -f .env.example
	@test -f docker-compose.yml
	@printf "Skeleton files are present.\n"

ci: lint check

lint:
	@python3 -m compileall -q apps libs services tests

test:
	@python3 -m unittest discover -s tests/unit

compose-check:
	@docker compose config >/dev/null

docs-check:
	@test -f docs/roadmap/developer_roadmap.md
	@test -f docs/architecture/frontend_control_surface.md
	@test -f docs/architecture/system_design.md
	@test -f docs/code_review.md

secret-scan:
	@! git grep -n -E '(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})' -- . ':!*.pyc'

up:
	@docker compose up

api:
	@python3 -m apps.api.server

tree:
	@find . -path ./.git -prune -o -print | sort

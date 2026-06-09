.PHONY: help bootstrap-check check ci compose-check coverage docs-check lint migrate secret-scan test tree up api

help:
	@printf "AI-CryptoFutures-TCP development targets\n"
	@printf "  make check  - run basic repository skeleton checks\n"
	@printf "  make bootstrap-check - verify safe local bootstrap defaults\n"
	@printf "  make ci     - run CI-equivalent local checks\n"
	@printf "  make lint   - run syntax checks\n"
	@printf "  make test   - run unit tests\n"
	@printf "  make coverage - run unit tests with >=98%% coverage\n"
	@printf "  make migrate - apply Postgres migrations using DATABASE_URL\n"
	@printf "  make up     - start the local development stack\n"
	@printf "  make api    - start the API locally without compose\n"
	@printf "  make tree   - print the tracked skeleton tree\n"

check: coverage compose-check docs-check bootstrap-check secret-scan
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

coverage:
	@python3 -m coverage run -m unittest discover -s tests/unit
	@python3 -m coverage report --fail-under=98

migrate:
	@python3 -m alembic upgrade head

compose-check:
	@docker compose config >/dev/null

docs-check:
	@test -f docs/roadmap/developer_roadmap.md
	@test -f docs/roadmap/workstation_production_readiness.md
	@test -f docs/architecture/frontend_control_surface.md
	@test -f docs/architecture/system_design.md
	@test -f docs/roadmap/phase_7_9_implementation_status.md
	@test -f docs/market_data/three_asset_universe.md
	@test -f docs/code_review.md
	@test -f configs/symbol_universe.yml

bootstrap-check:
	@python3 -c "from apps.api.server import status_payload; p=status_payload(); r=p['runtime']; assert r['operator_mode']=='paper'; assert r['venue_target']=='internal_paper'; assert r['credential_scope']=='none'; assert r['trading_gate']=='locked'; assert r['autonomy_stage']=='observe_only'; assert r['live_trading_enabled'] is False; assert r['binance_credentials_required'] is False; assert p['placeholders']['frontend']=='expected'; assert p['placeholders']['api']=='running'; assert p['placeholders']['database']=='expected'; assert p['placeholders']['redis']=='expected'; assert p['placeholders']['monitoring']=='expected'"

# Baseline guardrail: catch common committed token/key formats during local checks.
secret-scan:
	@! git grep -n -E '(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})' -- . ':!*.pyc'

up:
	@docker compose up

api:
	@python3 -m apps.api.server

tree:
	@find . -path ./.git -prune -o -print | sort

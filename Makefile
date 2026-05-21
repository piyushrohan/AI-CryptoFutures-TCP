.PHONY: help check tree

help:
	@printf "AI-CryptoFutures-TCP development targets\n"
	@printf "  make check  - run basic repository skeleton checks\n"
	@printf "  make tree   - print the tracked skeleton tree\n"

check:
	@test -f README.md
	@test -f AGENTS.md
	@test -f .env.example
	@test -f docker-compose.yml
	@printf "Skeleton files are present.\n"

tree:
	@find . -path ./.git -prune -o -print | sort

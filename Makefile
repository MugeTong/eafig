ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))

format:
	ruff format .

test:
	pytest tests/

%:
	@:

.PHONY: test test-smoke test-docker test-smoke-docker

test:
	bash scripts/test_all.sh

test-smoke:
	bash scripts/test_smoke.sh

test-docker:
	docker compose run --rm web bash -lc "pytest -q"

test-smoke-docker:
	docker compose run --rm web bash -lc "bash scripts/test_smoke.sh"


# tracegate — single entry point (DX alla Laravel: sensible defaults, one command).
.DEFAULT_GOAL := help
PY ?= python3
SRC := src

.PHONY: help setup test self self-check lint binary clean

help:  ## show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:  ## install runtime + test deps (editable)
	$(PY) -m pip install --user --break-system-packages -e '.[test]'

test:  ## run the test suite (golden + adapters + detection + orchestrator)
	$(PY) -m pytest -q

self:  ## dogfood — generate tracegate's own catalog into docs/_generated/
	PYTHONPATH=$(SRC) $(PY) -m tracegate . --out docs/_generated

self-check:  ## dogfood drift-gate — fail if docs/_generated/ is stale (the CI proof)
	PYTHONPATH=$(SRC) $(PY) -m tracegate . --out docs/_generated --check

binary:  ## build the standalone single-file binary (Nuitka)
	$(PY) packaging/build_binary.py

clean:  ## remove build artifacts and caches
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

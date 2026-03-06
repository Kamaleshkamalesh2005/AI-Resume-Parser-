.PHONY: test test-unit test-integration coverage lint typecheck ci

# ── Testing ───────────────────────────────────────────────────────────
test:
	python -m pytest tests/ -q

test-unit:
	python -m pytest tests/unit/ -m unit -q

test-integration:
	python -m pytest tests/integration/ -m integration -q

coverage:
	python -m pytest tests/ \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80 \
		-q

# ── Linting / type-check ─────────────────────────────────────────────
lint:
	ruff check .

typecheck:
	mypy app/ --ignore-missing-imports --no-strict-optional

# ── Full CI pipeline (matches GitHub Actions) ─────────────────────────
ci: lint typecheck coverage

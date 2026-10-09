.PHONY: test install run clean dev

install:
	pip install -e ".[dev]"

test:
	pytest -v tests/

run:
	python -m outline_mcp.main

clean:
	rm -rf __pycache__ .pytest_cache dist build *.egg-info

dev: install
	pip install -e .

fmt:
	black outline_mcp/ tests/

lint:
	ruff check outline_mcp/ tests/

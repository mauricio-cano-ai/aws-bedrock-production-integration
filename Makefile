.PHONY: install lint type test verify sam-validate sam-build
install:
	python -m pip install -e ".[dev]"
lint:
	ruff check src tests
type:
	pyright
test:
	coverage run -m pytest -q
	coverage report -m
verify: lint type test
sam-validate:
	sam validate --lint
sam-build:
	sam build

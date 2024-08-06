.ONESHELL:
PY_ENV=.venv
PY_BIN=$(shell python -c "print('$(PY_ENV)/bin') if __import__('pathlib').Path('$(PY_ENV)/bin/pip').exists() else print('')")

.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

.PHONY: check-venv
check-venv:	  ## Check if the virtualenv exists.
	@if [ "$(PY_BIN)" = "" ]; then echo "No virtualenv detected, create one using 'make virtualenv'"; exit 1; else echo "Found venv $(PY_BIN)"; fi

.PHONY: fmt
fmt: check-venv
	$(PY_BIN)/ruff format .

.PHONY: lint
lint: check-venv
	$(PY_BIN)/ruff check .
	$(PY_BIN)/ruff format --check .
	@if [ -x "$(PY_BIN)/mypy" ]; then $(PY_BIN)/mypy argdantic/; else echo "mypy not installed, skipping"; fi

.PHONY: test
test: check-venv lint
	$(PY_BIN)/pytest --cov=argdantic --cov-report=xml -o console_output_style=progress

.PHONY: publish
publish: check-venv
	$(PY_BIN)/flit publish --pypirc $(CFG)

.PHONY: clean
clean:            ## Clean unused files.
	@find ./ -name '*.pyc' -exec rm -f {} \;
	@find ./ -name '__pycache__' -exec rm -rf {} \;
	@find ./ -name 'Thumbs.db' -exec rm -f {} \;
	@find ./ -name '*~' -exec rm -f {} \;
	@rm -rf .cache
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg-info
	@rm -rf htmlcov
	@rm -rf .tox/
	@rm -rf docs/_build

.PHONY: release
release:          ## Create a new tag for release.
	@echo "WARNING: This operation will create s version tag and push to github"
	@read -p "Version? (provide the next x.y.z semver) : " TAG
	@VER_FILE=$$(find argdantic -maxdepth 2 -type f -name 'version.py' | head -n 1)
	@echo "Updating version file :\n $${VER_FILE}"
	@echo __version__ = \""$${TAG}"\" > $${VER_FILE}
	@git add .
	@git commit -m "🔖 Release version v$${TAG}"
	@echo "creating git tag : v$${TAG}"
	@git tag v$${TAG}
	@git push -u origin HEAD --tags

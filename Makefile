# Makefile for ctxd

# Variables
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
SRC_DIR := ctxd

.PHONY: all install install-dev sync-deps test build run-daemon run-cli sync clean

all: install

# Installation
install: $(VENV_DIR)/bin/activate
	@echo "Installing dependencies and the project in editable mode..."
	uv pip install -e .

$(VENV_DIR)/bin/activate: pyproject.toml
	@echo "Creating virtual environment..."
	uv venv $(VENV_DIR)
	@echo "Installing dependencies..."
	uv pip sync uv.lock --python $(VENV_DIR)/bin/python
	@touch $(VENV_DIR)/bin/activate

install-dev: install
	@echo "Installing development dependencies..."
	uv pip install pytest --python $(VENV_DIR)/bin/python

sync-deps:
	@echo "Syncing dependencies..."
	uv pip sync uv.lock

# Testing
test: install-dev
	@echo "Running tests..."
	$(PYTHON) -m pytest

# Building
build:
	@echo "Building wheel..."
	uv pip wheel --out-dir dist .

# Running
run-daemon: install
	@echo "Starting the context cache daemon..."
	$(VENV_DIR)/bin/ctxdd

run-cli: install
	@echo "Running CLI command..."
	$(VENV_DIR)/bin/ctc $(ARGS)

sync:
	@echo "Running sync command..."
	$(MAKE) run-cli ARGS=sync

# Cleaning
clean:
	@echo "Cleaning up..."
	rm -rf dist build *.egg-info
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf $(VENV_DIR)


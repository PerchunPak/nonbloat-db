SHELL:=/usr/bin/env bash

.PHONY: format
format:
	ruff check --fix .
	ruff format .

.PHONY: lint
lint:
	ruff check .
	basedpyright .

.PHONY: style
style: format lint

.PHONY: unit
unit:
	pytest

.PHONY: package
package:
	poetry check
	pip check

.PHONY: test
test: style package unit

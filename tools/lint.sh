#!/usr/bin/env bash

set -e
set -x
# check formatting and linting with ruff
ruff check .
ruff format --check .

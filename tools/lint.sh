#!/usr/bin/env bash

set -e
set -x
# format with black and isort, then run flake8
black argdantic tests --check
isort argdantic tests --check-only
flake8 --max-line-length=120 argdantic tests
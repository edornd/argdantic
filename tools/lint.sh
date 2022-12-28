#!/usr/bin/env bash

set -e
set -x
# format with black and isort, then run flake8
black argdantic tests examples --check
isort argdantic tests examples --check-only
flake8 --max-line-length=120 argdantic tests examples

#!/usr/bin/env bash

set -e
set -x

pytest --cov=argdantic --cov-report=xml -o console_output_style=progress

#!/bin/bash
set -e
cd /repo
pytest tests/test_utils.py -x --tb=short
exit $?

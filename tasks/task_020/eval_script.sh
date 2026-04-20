#!/bin/bash
set -e
cd /repo
pytest tests/__init__.py tests/test_requests.py -x --tb=short
exit $?

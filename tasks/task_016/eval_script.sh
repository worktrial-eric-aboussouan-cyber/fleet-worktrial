#!/bin/bash
set -e
cd /repo
pytest tests/test_help.py tests/test_requests.py tests/test_utils.py -x --tb=short
exit $?

#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_status_code_425"
exit $?

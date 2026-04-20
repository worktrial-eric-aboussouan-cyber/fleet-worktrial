#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_redirect_history_no_self_reference"
exit $?

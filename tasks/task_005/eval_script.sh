#!/bin/bash
set -e
cd /repo
pytest tests/test_lowlevel.py tests/test_requests.py tests/test_testserver.py -x --tb=short
exit $?

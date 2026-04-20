#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_basicauth_with_netrc_leak"
exit $?

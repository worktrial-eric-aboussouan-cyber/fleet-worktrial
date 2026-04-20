#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_proxy_authorization_not_appended_to_https_request"
exit $?

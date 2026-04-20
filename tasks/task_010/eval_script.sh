#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_different_connection_pool_for_tls_settings"
exit $?

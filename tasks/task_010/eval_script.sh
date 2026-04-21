#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -k "test_different_connection_pool_for_tls_settings" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

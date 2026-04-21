#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -k "test_basicauth_with_netrc_leak" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

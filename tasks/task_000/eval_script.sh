#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -k "test_redirect_history_no_self_reference" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

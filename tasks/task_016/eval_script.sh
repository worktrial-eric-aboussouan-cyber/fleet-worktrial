#!/bin/bash
cd /repo
pytest tests/test_help.py tests/test_requests.py tests/test_utils.py --tb=short -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

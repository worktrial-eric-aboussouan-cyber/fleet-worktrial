#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -k "test_status_code_425" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

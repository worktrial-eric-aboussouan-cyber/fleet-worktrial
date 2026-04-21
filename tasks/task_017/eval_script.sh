#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

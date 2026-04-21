#!/bin/bash
cd /repo
pytest tests/test_lowlevel.py tests/test_requests.py tests/test_testserver.py --tb=short -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

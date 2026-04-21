#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -k "test_header_with_subclass_types" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

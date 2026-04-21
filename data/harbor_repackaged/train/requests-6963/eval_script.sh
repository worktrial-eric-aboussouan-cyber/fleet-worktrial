#!/bin/bash
cd /repo
pytest tests/test_utils.py --tb=short -k "test_works or test_not_vulnerable_to_bad_url_parsing" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

#!/bin/bash
cd /repo
pytest tests/test_utils.py --tb=short -k "test_empty_default_credentials_ignored" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

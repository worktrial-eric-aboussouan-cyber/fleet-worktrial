#!/bin/bash
set -e
cd /repo
pytest tests/test_utils.py -x --tb=short -k "test_works or test_not_vulnerable_to_bad_url_parsing"
exit $?

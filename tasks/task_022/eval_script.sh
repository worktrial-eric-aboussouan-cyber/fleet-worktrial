#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_header_value_not_str or test_header_no_return_chars or test_header_no_leading_space"
exit $?

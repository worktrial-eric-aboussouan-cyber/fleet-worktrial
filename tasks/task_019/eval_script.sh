#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_header_with_subclass_types"
exit $?

#!/bin/bash
set -e
cd /repo
pytest tests/test_utils.py -x --tb=short -k "test_empty_default_credentials_ignored"
exit $?

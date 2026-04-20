#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_session_get_adapter_prefix_with_trailing_slash or test_session_get_adapter_prefix_without_trailing_slash"
exit $?

#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -k "test_session_get_adapter_prefix_with_trailing_slash or test_session_get_adapter_prefix_without_trailing_slash" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

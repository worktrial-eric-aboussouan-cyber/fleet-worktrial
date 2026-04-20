#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_content_length_for_bytes_data or test_content_length_for_string_data_counts_bytes"
exit $?

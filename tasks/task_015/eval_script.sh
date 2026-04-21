#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -k "test_content_length_for_bytes_data or test_content_length_for_string_data_counts_bytes" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

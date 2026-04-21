#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -k "test_request_url_trims_leading_path_separators or test_content_length_for_bytes_data or test_content_length_for_string_data_counts_bytes or test_json_decode_errors_are_serializable_deserializable" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

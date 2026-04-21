#!/bin/bash
cd /repo
pytest tests/test_requests.py --tb=short -k "test_json_decode_errors_are_serializable_deserializable" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

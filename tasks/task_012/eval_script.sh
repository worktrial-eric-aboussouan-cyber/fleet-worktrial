#!/bin/bash
set -e
cd /repo
pytest tests/test_requests.py -x --tb=short -k "test_json_decode_errors_are_serializable_deserializable"
exit $?

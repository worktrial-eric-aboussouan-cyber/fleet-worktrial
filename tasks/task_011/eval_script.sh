#!/bin/bash
set -e
cd /repo
pytest tests/test_adapters.py -x --tb=short -k "test_request_url_trims_leading_path_separators"
exit $?

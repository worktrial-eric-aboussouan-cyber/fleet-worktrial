#!/bin/bash
cd /repo
pytest tests/test_adapters.py --tb=short -k "test_request_url_trims_leading_path_separators" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

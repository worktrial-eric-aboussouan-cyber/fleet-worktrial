#!/bin/bash
cd /repo
pytest tests/test_utils.py --tb=short -k "test_should_bypass_proxies_win_registry_bad_values" -q | tee /tmp/result.txt; tail -1 /tmp/result.txt
exit $?

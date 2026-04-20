#!/bin/bash
set -e
cd /repo
pytest tests/test_utils.py -x --tb=short -k "test_should_bypass_proxies_win_registry_ProxyOverride_value"
exit $?

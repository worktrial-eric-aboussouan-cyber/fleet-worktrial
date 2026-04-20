#!/bin/bash
set -e
cd /repo
pytest tests/test_help.py tests/test_requests.py tests/test_utils.py -x --tb=short -k "test_idna_without_version_attribute or test_idna_with_version_attribute or test_env_cert_bundles or test_iter_content_wraps_exceptions or test_session_close_proxy_clear or test_should_bypass_proxies_pass_only_hostname"
exit $?

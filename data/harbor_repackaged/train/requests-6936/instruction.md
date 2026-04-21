Issue: tests: add trailing slashes to mount to match docs recommendation?

I was digging into the docs and noticed this:
> The adapter will be chosen based on a longest prefix match. Be mindful prefixes such as http://localhost will also match http://localhost.other.com or http://localhost@other.com. It’s recommended to terminate full hostnames with a /.

[link](https://requests.readthedocs.io/en/latest/user/advanced/)

While checking out some tests that uses the `Session.mount()`, I saw that a few don’t follow this recommendation. For example, in test_session_get_adapter_prefix_matching  (https://github.com/psf/requests/blob/main/tests/test_requests.py#L1620):

```python
prefix = "https://example.com"  # no trailing slash
more_specific_prefix = prefix + "/some/path"  # no trailing slash
...
s.mount(prefix, prefix_adapter)
s.mount(more_specific_prefix, more_specific_prefix_adapter)
```

I know that the tests work great and do their job, but adding trailing slashes (e.g., https://example.com/ and https://example.com/some/path/) would align them with the docs and make the prefixes more precise.

Here are the tests I noticed:
- test_transport_adapter_ordering
- test_session_get_adapter_prefix_matching
- test_session_get_adapter_prefix_matching_mixed_case
- test_session_get_adapter_prefix_matching_is_case_insensitive

Would it be worth opening a PR to update these to include trailing slashes? The tests would stay the same, just following the docs best practice.

PR: test: add two more tests exercising the adapter

This PR adds two test cases for `Session.mount()` to cover the documentation's recommendation about trailing slashes in prefixes (see #6935). 

The first test `test_session_get_adapter_prefix_with_trailing_slash` verifies that prefixes with a trailing / (e.g., https://example.com/) match only the intended hostname. 

The second test `test_session_get_adapter_prefix_without_trailing_slash` verifies that prefixes without a trailing / (e.g., https://example.com) match both the intended hostname and extended hostnames (e.g., https://example.com.other.com), as warned in the docs. 

Together, these tests ensure the longest prefix match behavior is well-documented and stable.
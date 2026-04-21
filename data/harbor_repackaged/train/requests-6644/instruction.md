Issue: Leading slash in uri followed by column fails

Leading slash in uri followed by column fails.

## Expected Result

```python
requests.get('http://127.0.0.1:10000//v:h')
<Response [200]>
```

## Actual Result

```python
Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/urllib3/util/url.py", line 425, in parse_url
    host, port = _HOST_PORT_RE.match(host_port).groups()  # type: ignore[union-attr]
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'groups'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 73, in get
    return request("get", url, params=params, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 59, in request
    return session.request(method=method, url=url, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/requests/sessions.py", line 589, in request
    resp = self.send(prep, **send_kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/requests/sessions.py", line 703, in send
    r = adapter.send(request, **kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/requests/adapters.py", line 486, in send
    resp = conn.urlopen(
           ^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 711, in urlopen
    parsed_url = parse_url(url)
                 ^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/urllib3/util/url.py", line 451, in parse_url
    raise LocationParseError(source_url) from e
urllib3.exceptions.LocationParseError: Failed to parse: //v:h
```

## Reproduction Steps

```python
import requests
req

PR: Trim excess leading path separators

A URL with excess leading / (path-separator)s would cause urllib3 to attempt to reparse the request-uri as a full URI with a host and port. This bypasses that logic in ConnectionPool.urlopen by replacing these leading /s with just a single /.

Closes #6643
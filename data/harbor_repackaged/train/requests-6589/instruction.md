Issue: The Content-Length header for string `data` counts Unicode characters in the string when it should count encoded bytes

A call like this:

```python
response = requests.post("https://example.com", data="👍👎")
```

auto sets the `Content-Length` header in the request to `2` when it should be `8`.

I hit this issue was making a request with a JSON body to a service I own (running behind AWS API Gateway) and having the service complain that there was no closing brace `}` in the JSON body. I was passing the JSON body into requests as a string to the `data` argument. It turns out that API Gateway ignores any body bytes beyond the `Content-Length` in the request. Turning up detailed logging on API Gateway, I can see the request headers and realized the value in the `Content-Length` header didn't match the number of bytes in the body.

A quick workaround is to encode the string into bytes before passing it into Requests.

This produces a Content-Length header with the correct value of `8`:

```python
response = requests.post("https://example.com", data="👍👎".encode("utf-8"))
```

## Expected Result

On a server receiving a POST from Requests, I expect the `Content-Length` header value to match the number of bytes in the body of the request. See [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110#field.content-length).

## Actual Result

In the specific case where Request's `data` argument is set as a string containing characters which encode into multi-byte UTF-8, the value in the `Content-Length` header is incorrect. Requests appears to be counting the number of Unicode characters in the string instead of the number of bytes that will be sent to the server.

## Reproduction Steps

```python
>>> import requests
>>> thumbs_up_down = "👍👎"
>>> len(thumbs_up_down)
2
>>> len(thumbs_up_down.encode())
8
>>> pending_request = requests.Request("POST", "https://example.com", data=thumbs_up_down)
>>> prepared_request = pending_request.prepare()
>>> prepared_request.headers
{'Content-Length': '2'}
```

I opened a pull request, #6587, that adds a failing unit test th

PR: Enhance `super_len` to count encoded bytes for str

This is a possible fix for issue #6586.

I am not at all confident that this is an appropriate change for Requests. All of the unit tests pass locally for me (specifically `make ci`).
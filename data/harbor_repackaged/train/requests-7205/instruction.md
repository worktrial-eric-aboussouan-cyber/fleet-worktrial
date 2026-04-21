PR: Fix empty netrc entry usage

Prior to Python 3.11, a netrc entry without a username, account, or password entry was treated as malformed and raised a `NetrcParseError` disabling usage. For 3.11+, it now returns an empty tuple `('', '' ,'')` instead. That results in Requests sending an empty entry (`:`) for the value to encode in an Authorization header.

This PR brings Requests back to its intended behavior of ignoring these profiles. Anyone who may have some use case for this, we did not to intend to support this behavior. If you need it going forward, you can pass `auth=('', '')` with your request.
Issue: [BUG] JSONDecodeError can't be deserialized - invalid JSON raises a BrokenProcessPool and crashes the entire process pool

Hi all,

I've stumbled upon a bug in the `requests` library, and have a proposal for a fix.

In short: I have a process pool running tasks in parallel, that are among other things doing queries to third-party APIs. One third-party returns an invalid JSON document as response in case of error.

However, instead of just having a JSONDecodeError as the result of my job, the entire process pool crashes due to a BrokenProcessPool error with the following stack trace:

```
Traceback (most recent call last):
  File "/usr/local/lib/python3.11/concurrent/futures/process.py", line 424, in wait_result_broken_or_wakeup
    result_item = result_reader.recv()
                  ^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/multiprocessing/connection.py", line 251, in recv
    return _ForkingPickler.loads(buf.getbuffer())
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/requests/exceptions.py", line 41, in __init__
    CompatJSONDecodeError.__init__(self, *args)
TypeError: JSONDecodeError.__init__() missing 2 required positional arguments: 'doc' and 'pos'
```

So I'm in a situation where receiving one invalid JSON as response is interrupting all my ongoing tasks because the entire process pool is crashing, and no more tasks can be submitted until the process pool recovered.

## Origin of the bug + Fix

After investigation, this is because the `requests.exception.JSONDecodeError` instances can't be deserialized once they've been serialized via `pickle`. So when the main process is trying to deserialize the error returned by the child process, the main process is crashing with to the error above.

I think this bug has been around for a while, I've found old tickets from different projects mentioning issues that are looking similar: https://github.com/celery/celery/issues/5712

I've pinpointed the bug to the following class: https://github.com/psf/requests/blob/main/src/requests/exceptions.py#L31

PR: Fix #6628 - JSONDecodeError are not deserializable

See issue #6628 for full bug-report

-----

requests.exceptions.JSONDecodeError are not deserializable: calling `pickle.dumps` followed by `pickle.loads` will trigger an error.

This is particularly a problem in a process pool, as an attempt to decode json on an invalid json document will result in the entire process pool crashing.

This is due to the MRO of the `requests.exceptions.JSONDecodeError` class: the `__reduce__` method called when pickling an instance is not the one from the JSON library parent: two out of three args expected for instantiation will be dropped, and the instance can't be deserialised.

By specifying in the class which parent `__reduce__` method should be called, the bug is fixed as all args are carried over in the resulting pickled bytes.
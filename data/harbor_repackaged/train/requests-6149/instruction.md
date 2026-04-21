Issue: ValueError when calling requests.get on windows systems.

<!-- Summary. -->
Using windows I'm getting a ValueError in utils.py file telling that it's failing to parse to int ''. It's because the registry query is returning empty string instead of '0' or '1'.
## Expected Result
The request be successful

## Actual Result
File ...\site-packages\requests\utils.py, line 68, in proxy_bypass_registry proxyEnable = int(winreg.QueryValueEx(internetSettings,
ValueError: invalid literal for int() with base 10: ''

## Reproduction Steps

```python
import requests
url = 'https://api.github.com/events'
r = requests.get(url)
```

Here is the StackOverflow question of more people complaining about this issue and my answer with a solution for the problem

https://stackoverflow.com/a/71770718/2726538

<!-- This command is only available on Requests v2.16.4 and greater. Otherwise,
please provide some basic information about your system (Python version,
operating system, &c). -->

PR: Tolerate bad registry entries in Windows proxy settings

This PR will address #6104. Requests will now handle bad registry entries more gracefully when checking proxy settings from the host. When invalid entries are encountered, the ProxyEnabled setting will be ignored as if they didn't exist rather than throwing an exception.
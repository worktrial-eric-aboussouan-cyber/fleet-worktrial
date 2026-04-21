PR: fix CVE 2024 47081: manual url parsing leads to netloc credentials leak

https://seclists.org/fulldisclosure/2025/Jun/2

Honestly I have no idea why this lib used `netloc` + manual parsing instead of `hostname` as I can see references to `hostname` as early as from [the python 2.6 docs](https://docs.python.org/2.6/library/urlparse.html).
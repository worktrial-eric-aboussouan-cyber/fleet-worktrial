PR: test: Add new test to check netrc auth leak

This patch uses the "hostname" attribute from the parsed url to get the host, instead of trying to calculate the host from netloc that can produce errors when "http://username:password@domain.com" format is used.

This should fix the security issue reported here: [CVE-2024-47081: Netrc credential leak in PSF requests library](
https://seclists.org/oss-sec/2025/q2/204)
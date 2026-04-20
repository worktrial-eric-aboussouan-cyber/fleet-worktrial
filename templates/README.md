# Extras Group Selections

## requests
**Extras chosen:** `socks`
**Why:** The requests repository explicitly includes the `socks` extra in its development and testing dependencies (`requirements-dev.txt`), as well as its `test` dependency group in `pyproject.toml`.
**Quote from `requirements-dev.txt`:**
```text
-e .[socks]
pytest>=2.8.0,<10
```

## click
**Extras chosen:** None
**Why:** The click repository does not define any optional dependencies (extras) in its build configuration. Test dependencies are simply standalone packages defined under a dependency group.
**Quote from `pyproject.toml`:**
```toml
[dependency-groups]
tests = [
    "pytest",
]
```

## flask
**Extras chosen:** `async`, `dotenv`
**Why:** Flask defines `async` and `dotenv` as optional dependencies. Its `tests` dependency group includes the packages `asgiref` and `python-dotenv` which are the underlying implementations for these extras, so we install the package with those extras enabled to test their integrations.
**Quote from `pyproject.toml`:**
```toml
[project.optional-dependencies]
async = ["asgiref>=3.2"]
dotenv = ["python-dotenv"]

[dependency-groups]
tests = [
    "asgiref",
    "greenlet",
    "pytest",
    "python-dotenv",
]
```

## httpx
**Extras chosen:** `brotli`, `cli`, `http2`, `socks`, `zstd`
**Why:** The httpx project explicitly tests against all its optional features. Its primary testing environment configuration file (`requirements.txt`) installs the package in editable mode with all of these extras enabled.
**Quote from `requirements.txt`:**
```text
# We're pinning our tooling, because it's an environment we can strictly control.
# On the other hand, we're not pinning package dependencies, because our tests
# needs to pass with the latest version of the packages.
# Reference: https://github.com/encode/httpx/pull/1721#discussion_r661241588
-e .[brotli,cli,http2,socks,zstd]
```

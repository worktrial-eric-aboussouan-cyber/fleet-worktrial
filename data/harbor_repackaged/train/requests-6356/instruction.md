PR: Allow str/bytes subclasses to be used as header parts

Closes https://github.com/psf/requests/issues/6159 Adapted from https://github.com/nateprewitt/requests/commit/66fcc9c88cf5a53e85322305f41006032744cbe3 but also supports mixed type tuples.
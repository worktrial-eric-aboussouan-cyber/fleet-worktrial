PR: Cleanup extracted file after extract_zipped_path test

With the changes in 66d21cb07bd6255b1280291c4fafb71803cdb3b7 we now create a new extracted file every test run which can clutter the tmp directory. This becomes a problem when running the test suite repeatedly locally. This PR will now enforce cleanup when the test finishes regardless of success.
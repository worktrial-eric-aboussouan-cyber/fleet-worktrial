FROM python:3.11-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

ARG BASE_COMMIT

RUN git clone https://github.com/psf/requests.git /repo
WORKDIR /repo
RUN git checkout cbce031327be4f1b4b5fd041ff4dcaa8efa2ce53

# Install testing dependencies from requests' requirements-dev.txt
# This includes `-e .[socks]` which installs the package in editable mode with the socks extra.
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY eval_script.sh /eval_script.sh
COPY eval_script.sh /eval_script.sh

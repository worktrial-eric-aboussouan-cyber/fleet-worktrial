FROM python:3.11-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

ARG BASE_COMMIT

RUN git clone https://github.com/psf/requests.git /repo
WORKDIR /repo
RUN git checkout a5e7169e759817ca309f8271c3c4fa79393a22f5

# Install testing dependencies from requests' requirements-dev.txt
# This includes `-e .[socks]` which installs the package in editable mode with the socks extra.
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY eval_script.sh /eval_script.sh
COPY eval_script.sh /eval_script.sh

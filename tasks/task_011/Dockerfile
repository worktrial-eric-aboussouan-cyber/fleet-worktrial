FROM python:3.11-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

ARG BASE_COMMIT

RUN git clone https://github.com/psf/requests.git /repo
WORKDIR /repo
RUN git checkout 382fc2c0c6c0ef0874bc65bc1175f97c073e5086

# Install testing dependencies from requests' requirements-dev.txt
# This includes `-e .[socks]` which installs the package in editable mode with the socks extra.
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY eval_script.sh /eval_script.sh
COPY eval_script.sh /eval_script.sh

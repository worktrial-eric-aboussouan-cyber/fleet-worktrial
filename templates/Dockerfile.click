FROM python:3.11-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

ARG BASE_COMMIT

RUN git clone https://github.com/pallets/click.git /repo
WORKDIR /repo
RUN git checkout ${BASE_COMMIT}

# Click doesn't define any extras in optional-dependencies, but requires pytest for tests.
RUN pip install --no-cache-dir -e . pytest
COPY eval_script.sh /eval_script.sh

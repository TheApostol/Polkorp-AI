# POLKORP AI — Fooocus build context
# Referenced by docker-compose.yml's `fooocus` service.
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      git python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /content/app
RUN git clone --depth 1 https://github.com/lllyasviel/Fooocus.git .

RUN python3 -m pip install --no-cache-dir -r requirements_versions.txt

EXPOSE 7865
VOLUME ["/content/app/outputs"]

CMD ["python3", "entry_with_update.py", "--listen", "0.0.0.0", "--port", "7865", "--always-high-vram"]

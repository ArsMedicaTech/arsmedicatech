FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl --no-install-recommends \
    && pip install boto3 --quiet \
    && curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/kubectl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ecr_refresh.py /ecr_refresh.py

ENTRYPOINT ["python", "/ecr_refresh.py"]

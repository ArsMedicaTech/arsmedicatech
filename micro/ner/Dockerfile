FROM python:3.11-slim AS base

# system deps for spaCy CPU wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Install everything in one layer to enable Docker cache.
# en_core_sci_sm is pinned to a direct wheel URL above, so this bakes the
# model into the image (no runtime download in production).
RUN pip install --no-cache-dir -r requirements.txt && pip check

# Verify the model + pipeline are importable at build time, not first request.
RUN python -m spacy validate

COPY ./main.py ./main.py
ENV PYTHONPATH=/app

EXPOSE 5000

# ---------- runtime ----------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]

# AP government assistant (RTI + agriculture) in one container.
#
#   docker build -t ap-assistant .
#   docker run --rm --env-file .env -p 8000:8000 ap-assistant      -> http://localhost:8000
#
# or simply:  docker compose up --build
#
# The image holds everything that runs locally -- Python packages, the embedding
# and reranking models, and both search indexes -- so it starts in ~20 s and needs
# the network only for Groq. The Groq key is never baked in: pass it at run time.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/huggingface \
    TOKENIZERS_PARALLELISM=false

# CPU-only PyTorch first: the default wheel bundles CUDA libraries (several GB) that a
# CPU container never uses. Same version as the development machine.
RUN pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Not root at run time.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /opt/huggingface /app \
    && chown app:app /opt/huggingface /app
USER app
WORKDIR /app

# The two local models, downloaded once at build time:
#   embeddings  -- the "model" field of ingest/chunks*.json (the indexes are built with it)
#   reranker    -- agriculture's "rerank" model in rag/domains.py
# If either changes there, change it here; the offline checks below fail the build otherwise.
ARG EMBED_MODEL=BAAI/bge-small-en-v1.5
ARG RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('${EMBED_MODEL}'); CrossEncoder('${RERANK_MODEL}')"
ENV HF_HUB_OFFLINE=1

# Both search indexes (Chroma, ~50 MB), built from the committed chunk files. Only
# what the build needs is copied first, so editing the rest of the code doesn't
# rebuild the indexes.
COPY --chown=app:app rag/domains.py rag/domains.py
COPY --chown=app:app ingest/build_index.py ingest/chunks.json ingest/chunks_agriculture.json ingest/
RUN python ingest/build_index.py && python ingest/build_index.py --domain agriculture

COPY --chown=app:app rag/ rag/
COPY --chown=app:app eval/ eval/

# Every model the domains are configured to use must load without the network.
RUN python -c "import sys; sys.path.insert(0, 'rag'); import domains; \
from sentence_transformers import CrossEncoder; \
[CrossEncoder(d.rerank['model']) for d in domains.DOMAINS.values() if d.rerank]; \
print('offline model check passed')"

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)"

CMD ["python", "rag/web.py", "--host", "0.0.0.0", "--port", "8000", "--no-browser"]

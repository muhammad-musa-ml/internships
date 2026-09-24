FROM python@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285
# The digest above is what the python 3.13-slim tag resolved to on 2026-09-18,
# read from the registry rather than typed: the manifest index was fetched over
# the Docker Hub v2 API, its docker-content-digest header and its etag both read
# 9d2e5553..., and sha256 of the 10,373 manifest bytes recomputes to the same
# value. Fetching that digest back returned HTTP 200 and a byte-identical body,
# so the reference is known to resolve rather than assumed to.
#
# It is pinned for the same reason postgres and redis are pinned in
# docker-compose.yml: a tag is a moving target, so "the same benchmark" would
# otherwise silently mean different software on a different day. The readable
# name is kept here in a comment because a bare digest tells a reader nothing.

WORKDIR /srv
RUN pip install --no-cache-dir \
      "fastapi==0.115.6" \
      "uvicorn[standard]==0.34.0" \
      "asyncpg==0.30.0" \
      "redis==5.2.1" \
      "orjson==3.10.12"

COPY main.py /srv/main.py
COPY seed.py /srv/seed.py

# Workers are pinned by env and recorded in the results, because throughput is
# meaningless without stating the server's concurrency shape.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-4} --no-access-log"]

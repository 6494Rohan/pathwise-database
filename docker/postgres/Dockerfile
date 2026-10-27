FROM postgis/postgis:17-3.5

# The PostGIS image has no pgvector; add it from the PostgreSQL apt repository the image already uses.
RUN apt-get update \
  && apt-get install -y --no-install-recommends postgresql-17-pgvector \
  && rm -rf /var/lib/apt/lists/*

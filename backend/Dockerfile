# NIRNAY backend — geospatial pipeline + FastAPI. Built for Render (or any host that runs
# a Dockerfile: Railway, Fly.io, a plain VM). This does NOT run on Netlify — see
# ../DEPLOYMENT.md for why and for the frontend-on-Netlify / backend-here split.
FROM python:3.11-slim

# GDAL/GEOS/PROJ: rasterio/shapely/geopandas ship manylinux wheels with these bundled on
# most platforms, but installing the system libs too avoids a surprise source build on an
# unusual host — worth the extra image size for a one-time hackathon deploy.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev libgeos-dev libproj-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY redzone ./redzone
RUN pip install --no-cache-dir -e .

COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# data/ is populated at container start (see docker-entrypoint.sh) so a fresh deploy is
# immediately useful without a separate seeding step.
RUN mkdir -p data/raw data/interim data/processed data/models

EXPOSE 8000
CMD ["./docker-entrypoint.sh"]

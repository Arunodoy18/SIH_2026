#!/usr/bin/env bash
# Runs once per container start: build the synthetic Sikkim seed, train the landslide
# model, run the analytics pipeline, then serve. Render's free tier spins the container
# down when idle and boots a fresh one on the next request, so this can't be a one-time
# manual step — it has to happen automatically every start. Takes a few seconds.
set -euo pipefail

echo "[entrypoint] seeding synthetic Sikkim dataset..."
python -m redzone.seed.generate_sikkim

echo "[entrypoint] training landslide susceptibility model..."
python -m redzone.ml.generate_landslide_inventory
python -m redzone.ml.train_landslide_model

echo "[entrypoint] running the analytics pipeline..."
python -m redzone.pipeline

echo "[entrypoint] starting API on port ${PORT:-8000}..."
exec uvicorn redzone.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"

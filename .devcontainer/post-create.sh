#!/usr/bin/env bash
set -euo pipefail

# Ensure python dependencies installed inside a virtual environment for local tooling
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip

# Install CPU-only PyTorch wheels before the rest of the requirements so we avoid
# pulling in massive GPU builds inside Codespaces. Try the official CPU wheel
# index first and fall back to the default PyPI index when that registry is not
# reachable.
if ! PIP_EXTRA_INDEX_URL= \
  pip install \
    --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.2+cpu \
    torchvision==0.17.2+cpu; then
  echo "[post-create] Falling back to default PyPI for torch CPU wheels." >&2
  PIP_EXTRA_INDEX_URL= \
  pip install \
    --no-cache-dir \
    --index-url https://pypi.org/simple \
    torch==2.2.2 \
    torchvision==0.17.2
fi

pip install -r requirements.txt

deactivate

# Install frontend dependencies
if [ -d "frontend" ]; then
  cd frontend
  npm install
fi

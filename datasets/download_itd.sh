#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
mkdir -p datasets/raw/recognition/itd
curl --fail --location --retry 3 --continue-at - \
  'https://cvit.iiit.ac.in/images/datasets/food_nutrition/ITD.tar.gz' \
  --output datasets/raw/recognition/itd/ITD.tar.gz

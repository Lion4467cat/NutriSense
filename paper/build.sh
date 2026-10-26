#!/usr/bin/env bash
set -euo pipefail

paper_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
tex_bin="$paper_dir/.texlive/2026/bin/x86_64-linux"

if [[ ! -x "$tex_bin/pdflatex" || ! -x "$tex_bin/latexmk" ]]; then
  printf 'Local TeX Live compiler is missing. Run ./setup_texlive.sh from %s first.\n' "$paper_dir" >&2
  exit 127
fi

export PATH="$tex_bin:$PATH"
cd "$paper_dir"
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

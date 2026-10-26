#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
texlive_root="$script_dir/.texlive/2026"
texlive_user="$script_dir/.texlive/user"
tex_bin="$texlive_root/bin/x86_64-linux"

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  printf 'This setup script supports Linux x86_64 only. See https://tug.org/texlive/quickinstall.html for other platforms.\n' >&2
  exit 2
fi

if [[ ! -x "$tex_bin/pdflatex" ]]; then
  work_dir="$(mktemp -d)"
  trap 'rm -rf "$work_dir"' EXIT
  curl --fail --location --retry 3 \
    --output "$work_dir/install-tl-unx.tar.gz" \
    https://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz
  mkdir "$work_dir/installer"
  tar --extract --gzip --file "$work_dir/install-tl-unx.tar.gz" \
    --directory "$work_dir/installer" --strip-components=1
  perl "$work_dir/installer/install-tl" --no-interaction --scheme=minimal \
    --no-doc-install --no-src-install \
    --texdir="$texlive_root" --texuserdir="$texlive_user"
fi

"$tex_bin/tlmgr" install collection-latexrecommended \
  collection-fontsrecommended latexmk cite amsmath graphics xcolor psnfss
"$tex_bin/pdflatex" --version | head -n 1

#!/bin/sh
# Copy web/ into $STAGING_DIR so gh-pages serves the static site at the
# org's root. Pure file copy; no templating.
set -eu

: "${STAGING_DIR:?STAGING_DIR required}"

( cd web && tar c . ) | ( cd "$STAGING_DIR" && tar x )
echo "[site] $(find "$STAGING_DIR" -maxdepth 2 -type f -not -path '*/feed/*' | wc -l) static files staged"

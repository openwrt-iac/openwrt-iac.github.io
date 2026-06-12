#!/bin/sh
# Copy web/ into $STAGING_DIR so gh-pages serves the static site at the
# org's root. Pure file copy; no templating.
set -eu

: "${STAGING_DIR:?STAGING_DIR required}"

( cd web && tar c . ) | ( cd "$STAGING_DIR" && tar x )

# Disable Pages's default Jekyll processing. Without this, Pages runs the
# tree through Jekyll, whose build cache can hold stale output across
# subtree changes. The /uapi/* subtree stayed pinned to its pre-restructure
# content for days after the gh-pages branch had moved on, because Jekyll
# considered the compiled output up to date.
touch "$STAGING_DIR/.nojekyll"

echo "[site] $(find "$STAGING_DIR" -maxdepth 2 -type f -not -path '*/feed/*' | wc -l) static files staged"

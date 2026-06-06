#!/bin/sh
# Pull the latest stable openapi.json shipped with the most recent uapi
# release; place it at $STAGING_DIR/api/openapi.json so Redoc finds it
# same-origin at /api/openapi.json. The OpenAPI spec is checked into the
# uapi repo at build/openapi.json but isn't attached as a release asset;
# we fetch the spec from the tag's tarball instead.
set -eu

: "${STAGING_DIR:?STAGING_DIR required}"

mkdir -p "$STAGING_DIR/api"

latest=$(gh release list --repo openwrt-iac/uapi --exclude-pre-releases \
         --limit 1 --json tagName --jq '.[0].tagName // ""')
if [ -z "$latest" ]; then
  echo "[openapi] no stable uapi release; leaving api/openapi.json untouched"
  exit 0
fi

# Fetch build/openapi.json at the tagged commit. The Contents API returns
# base64 by default; -H Accept:application/vnd.github.raw streams raw bytes.
echo "[openapi] uapi $latest"
gh api -H 'Accept: application/vnd.github.raw' \
       "/repos/openwrt-iac/uapi/contents/build/openapi.json?ref=$latest" \
       > "$STAGING_DIR/api/openapi.json"

bytes=$(wc -c < "$STAGING_DIR/api/openapi.json")
echo "[openapi] wrote $STAGING_DIR/api/openapi.json ($bytes bytes)"

#!/bin/sh
# Pull the latest stable APK from each source in feed.yml, place into the
# staging tree's feed/packages/all/uapi/ directory, then mkndx + sign.
#
# Inputs (env):
#   STAGING_DIR    where to place feed/* (final commit comes from here)
#   APK_BIN        absolute path to the OpenWrt SDK's `apk` binary
#   SIGN_KEY       path to the feed private key (PEM)
#   GH_TOKEN       gh auth token (read access on the source repos suffices)
#
# Reads feed.yml from the repo root (./).
set -eu

: "${STAGING_DIR:?STAGING_DIR required}"
: "${APK_BIN:?APK_BIN required}"
: "${SIGN_KEY:?SIGN_KEY required}"

FEED_DIR="$STAGING_DIR/feed/packages/all/uapi"
mkdir -p "$FEED_DIR"

# Parse feed.yml with a tiny awk; the file is hand-maintained and the shape is
# stable. Each `- repo:` line starts a record; the next `asset_pattern:` line
# closes it. Output one record per line: `<repo>\t<asset_pattern>`.
records=$(awk '
  /^[[:space:]]*-[[:space:]]*repo:/ { sub(/.*repo:[[:space:]]*/, ""); repo=$0; next }
  /^[[:space:]]*asset_pattern:/    { sub(/.*asset_pattern:[[:space:]]*/, ""); gsub(/^['"'"'"]|['"'"'"]$/, "", $0); print repo "\t" $0 }
' feed.yml)

[ -n "$records" ] || { echo "feed.yml: no sources"; exit 1; }

printf '%s\n' "$records" | while IFS="	" read -r repo pattern; do
  [ -z "$repo" ] && continue
  echo "[aggregate] $repo  pattern=$pattern"
  # gh release list with --exclude-pre-releases filters at the source. If a
  # source has no stable release yet, skip it without failing the whole run.
  latest=$(gh release list --repo "$repo" --exclude-pre-releases --limit 1 \
           --json tagName --jq '.[0].tagName // ""' 2>/dev/null || true)
  if [ -z "$latest" ]; then
    echo "[aggregate]   no stable release on $repo, skipping"
    continue
  fi
  echo "[aggregate]   latest tag: $latest"
  gh release download "$latest" --repo "$repo" --pattern "$pattern" \
    --dir "$FEED_DIR" --clobber 2>&1 | sed 's/^/[aggregate]   /'
done

# Sign the index against everything in FEED_DIR.
cd "$FEED_DIR"
ls -la
"$APK_BIN" --allow-untrusted mkndx --output packages.adb \
           --sign-key "$SIGN_KEY" *.apk
echo "[aggregate] wrote $FEED_DIR/packages.adb"

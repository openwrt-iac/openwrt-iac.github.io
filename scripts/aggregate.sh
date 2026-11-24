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
# stable. Each `- repo:` line starts a record, which holds an `asset_pattern:` line
# and may hold an `extra_tags:` line. Output one record per line:
# `<repo>\t<asset_pattern>\t<extra tags, space-separated>`.
records=$(awk '
  function flush() { if (pattern != "") print repo "\t" pattern "\t" extra; repo = pattern = extra = "" }
  /^[[:space:]]*-[[:space:]]*repo:/ { flush(); sub(/.*repo:[[:space:]]*/, ""); repo=$0; next }
  /^[[:space:]]*asset_pattern:/    { sub(/.*asset_pattern:[[:space:]]*/, ""); gsub(/^['"'"'"]|['"'"'"]$/, "", $0); pattern=$0; next }
  /^[[:space:]]*extra_tags:/       { sub(/.*extra_tags:[[:space:]]*/, ""); extra=$0; next }
  END { flush() }
' feed.yml)

[ -n "$records" ] || { echo "feed.yml: no sources"; exit 1; }

printf '%s\n' "$records" | while IFS="	" read -r repo pattern extra; do
  [ -z "$repo" ] && continue
  echo "[aggregate] $repo  pattern=$pattern"
  # gh release list with --exclude-pre-releases filters at the source. If a
  # source has no stable release yet, skip it without failing the whole run.
  # --exclude-drafts matters as much: a deleted tag reverts its release to a draft,
  # and a token that can see drafts would otherwise feed an unpublished build to
  # every operator on the feed. The newest release can fix an older major after the current one
  # shipped, so the feed takes the release that GitHub marks Latest, not the newest.
  latest=$(gh release list --repo "$repo" --exclude-pre-releases --exclude-drafts --limit 100 \
           --json tagName,isLatest --jq 'map(select(.isLatest))[0].tagName // ""' 2>/dev/null || true)
  if [ -z "$latest" ]; then
    echo "[aggregate]   no stable release on $repo, skipping"
    continue
  fi
  echo "[aggregate]   latest tag: $latest"
  gh release download "$latest" --repo "$repo" --pattern "$pattern" \
    --dir "$FEED_DIR" --clobber 2>&1 | sed 's/^/[aggregate]   /'
  # An extra tag keeps an older major installable where the Latest one is not. It must be
  # published and stable, as the Latest one is, and a wrong tag stops the run instead of
  # quietly dropping a package that routers depend on.
  for tag in $extra; do
    stable=$(gh release view "$tag" --repo "$repo" --json isDraft,isPrerelease \
             --jq 'if .isDraft or .isPrerelease then "" else "yes" end' 2>/dev/null || true)
    [ "$stable" = yes ] || { echo "[aggregate]   $tag is not a published stable release of $repo"; exit 1; }
    echo "[aggregate]   extra tag: $tag"
    gh release download "$tag" --repo "$repo" --pattern "$pattern" \
      --dir "$FEED_DIR" --clobber 2>&1 | sed 's/^/[aggregate]   /'
  done
done

# Sign the index against everything in FEED_DIR.
cd "$FEED_DIR"
ls -la
"$APK_BIN" --allow-untrusted mkndx --output packages.adb \
           --sign-key "$SIGN_KEY" *.apk
echo "[aggregate] wrote $FEED_DIR/packages.adb"

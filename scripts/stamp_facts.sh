#!/bin/sh
# Substitute the facts about each package into the staged HTML, from the artifacts the build
# already downloads. Runs after pull_openapi.sh, which is what puts the spec on disk.
#
# These were hand-written and every one of them rotted: the badge said v2.1 against a 2.5.1
# feed, the resource count said 34 against 35 collections, and the install page pinned
# `apk add uapi=2.0.0-r1`, four minors behind anything the feed serves. Each is derivable from
# the release, so none of them should be typed by a human again.
#
# The API prefix is the one that matters most. The site hardcodes /api/v2 in six places, and
# every one of them silently becomes wrong the day uapi 3.0.0 promotes. Reading it from the
# spec's `servers` entry makes that promotion a no-op here.
set -eu

: "${STAGING_DIR:?STAGING_DIR required}"

spec="$STAGING_DIR/uapi/api/openapi.json"
if [ ! -s "$spec" ]; then
	echo "[facts] no staged spec at $spec; pull_openapi.sh must run first" >&2
	exit 1
fi

# The apk revision is not in the spec, so take the pin from the asset the feed actually serves:
# uapi-2.5.1-r1.apk yields 2.5.1-r1. Deriving it as version + "-r1" would be a guess that breaks
# the first time PKG_RELEASE moves.
# `gh release list --json` has no assets field, so resolve the tag first and then view it.
tag=$(gh release list --repo openwrt-iac/uapi --exclude-pre-releases --limit 1 \
      --json tagName --jq '.[0].tagName // ""')
asset=$(gh release view "$tag" --repo openwrt-iac/uapi \
        --json assets --jq '.assets[].name | select(test("^uapi-.*\\.apk$"))' 2>/dev/null | head -1)
apk_pin=$(printf '%s' "$asset" | sed -n 's/^uapi-\(.*\)\.apk$/\1/p')

facts=$(python3 - "$spec" <<'PY'
import json, sys, re
d = json.load(open(sys.argv[1]))
version = d['info']['version']

# "/api/v2" out of "https://{host}/api/v2".
servers = d.get('servers') or []
prefix = re.sub(r'^https?://[^/]+', '', servers[0]['url']) if servers else ''

# A curated resource endpoint is one a client addresses by name: every path that is not an
# infrastructure endpoint and does not take an {id}. Collections and singletons both count,
# which is how docs/resources.md catalogs them. The old hand-written 34 appears to have
# counted only the collections that return an array, and was stale even by that measure.
INFRA = ('/raw', '/schema', '/batch', '/tokens', '/auth', '/metrics',
         '/diagnostics', '/healthz', '/openapi')
resources = [p for p in d['paths'] if not p.startswith(INFRA) and '{' not in p]

print('UAPI_VERSION=%s' % version)
print('UAPI_PREFIX=%s' % prefix)
print('UAPI_RESOURCE_COUNT=%d' % len(resources))
PY
)

eval "$facts"
UAPI_APK_PIN=${apk_pin:-}

[ -n "$UAPI_VERSION" ]        || { echo "[facts] empty version from spec" >&2; exit 1; }
[ -n "$UAPI_PREFIX" ]         || { echo "[facts] no servers[0].url in spec" >&2; exit 1; }
[ -n "$UAPI_APK_PIN" ]        || { echo "[facts] could not read the apk pin from the release assets" >&2; exit 1; }
[ "$UAPI_RESOURCE_COUNT" -gt 0 ] || { echo "[facts] resource count came out zero" >&2; exit 1; }

echo "[facts] uapi $UAPI_VERSION  prefix $UAPI_PREFIX  pin $UAPI_APK_PIN  resources $UAPI_RESOURCE_COUNT"

find "$STAGING_DIR" -name '*.html' -type f | while read -r f; do
	sed -i \
		-e "s|{{UAPI_VERSION}}|$UAPI_VERSION|g" \
		-e "s|{{UAPI_PREFIX}}|$UAPI_PREFIX|g" \
		-e "s|{{UAPI_APK_PIN}}|$UAPI_APK_PIN|g" \
		-e "s|{{UAPI_RESOURCE_COUNT}}|$UAPI_RESOURCE_COUNT|g" \
		"$f"
done

# A placeholder that survives substitution ships to visitors as literal braces, which is worse
# than the stale number it replaced. Fail the build instead.
left=$(grep -rlE '\{\{[A-Z_]+\}\}' "$STAGING_DIR" --include='*.html' 2>/dev/null || true)
if [ -n "$left" ]; then
	echo "[facts] unsubstituted placeholders remain:" >&2
	grep -roE '\{\{[A-Z_]+\}\}' $left 2>/dev/null | sort -u | sed 's/^/  /' >&2
	exit 1
fi

echo "[facts] stamped $(find "$STAGING_DIR" -name '*.html' -type f | wc -l) html files"

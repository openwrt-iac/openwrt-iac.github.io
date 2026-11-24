#!/usr/bin/env python3
"""Latest stable release per major, newest first, as JSON on stdout.

The install steps differ per entry because the feed carries the newest release and only the
older ones that feed.yml lists in `extra_tags`, so another older major has to come from its
GitHub Release. Each entry's API prefix is read from that tag's own spec rather than inferred
from the major number.
"""
import json, re, subprocess, sys

REPO = 'openwrt-iac/uapi'


def feed_extra_tags():
    tags, inside = set(), False
    for line in open('feed.yml'):
        m = re.match(r'\s*-\s*repo:\s*(\S+)', line)
        if m:
            inside = m.group(1) == REPO
        elif inside and re.match(r'\s*extra_tags:', line):
            tags.update(line.split(':', 1)[1].split())
    return tags


def gh(*args):
    return subprocess.run(['gh', *args], capture_output=True, text=True).stdout


tags = gh('release', 'list', '--repo', REPO, '--exclude-pre-releases',
          '--limit', '60', '--json', 'tagName', '--jq', '.[].tagName').split()

extra = feed_extra_tags()
best = {}
for tag in tags:
    m = re.match(r'^v(\d+)\.(\d+)\.(\d+)$', tag)
    if not m:
        continue
    key = tuple(int(x) for x in m.groups())
    if key[0] not in best or key > best[key[0]][0]:
        best[key[0]] = (key, tag)

out = []
for i, major in enumerate(sorted(best, reverse=True)):
    tag = best[major][1]
    raw = gh('api', '-H', 'Accept: application/vnd.github.raw',
             '/repos/%s/contents/build/openapi.json?ref=%s' % (REPO, tag))
    try:
        spec = json.loads(raw)
        version = spec['info']['version']
        prefix = re.sub(r'^https?://[^/]+', '', (spec.get('servers') or [{}])[0].get('url', ''))
    except Exception:
        sys.exit('could not read build/openapi.json at %s' % tag)

    assets = json.loads(gh('release', 'view', tag, '--repo', REPO, '--json', 'assets')
                        or '{}').get('assets', [])
    apk = next((a for a in assets if re.match(r'^uapi-.*\.apk$', a['name'])), None)
    if not apk or not prefix:
        sys.exit('%s has no apk asset or no servers url' % tag)

    out.append({
        'version': version,
        'tag': tag,
        'prefix': prefix,
        'pin': re.sub(r'^uapi-(.*)\.apk$', r'\1', apk['name']),
        'url': apk['url'],
        'from_feed': i == 0 or tag in extra,
    })

if not out:
    sys.exit('no stable releases found')
print(json.dumps(out, separators=(',', ':')))

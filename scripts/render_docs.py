#!/usr/bin/env python3
"""Render each released version's docs/ into the staging tree.

Reads list_versions.py's JSON on stdin and writes $STAGING_DIR/uapi/docs/<version>/*.html plus
an index per version and a top-level index that points at the current release.

Versioned on purpose. 17 of uapi's 22 docs name a specific API major or describe a migration
across one, so a single "latest" copy would hand an operator still on 2.5.x the v3 instructions
that the migration guide exists to stop them following. Pulling each set from its own tag keeps
every page true for the release it documents, and keeps the repo the only place docs are edited:
nothing here is authored, only rendered.
"""
import html as html_mod
import json
import os
import re
import subprocess
import sys

import markdown

REPO = 'openwrt-iac/uapi'
STAGING = os.environ.get('STAGING_DIR')
if not STAGING:
    sys.exit('STAGING_DIR required')


def gh(*args):
    r = subprocess.run(['gh', *args], capture_output=True, text=True)
    return r.stdout


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - uapi {version} docs</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>

<header class="hero">
  <div class="container">
    <div class="brand"><a href="/uapi/" style="color:inherit;border:none;">uapi</a></div>
    <p class="crumb"><a href="/">openwrt-iac</a> / <a href="/uapi/">uapi</a> /
       <a href="/uapi/docs/">docs</a> / {version} / {title}</p>
  </div>
</header>

<section>
  <div class="container docs-body">
{body}
  </div>
</section>

<footer>
  <div class="container">
    <p class="micro">
      Rendered from <code>docs/{source}</code> at tag <code>{tag}</code>. Edits go to the
      <a href="https://github.com/{repo}/blob/{tag}/docs/{source}">repository</a>, never here.
    </p>
  </div>
</footer>

</body>
</html>
"""


def render_markdown(text):
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists'])
    return md.convert(text)


def rewrite_links(text):
    # Intra-doc links are written as `](architecture.md)` in the repo, where they resolve as
    # files. Here they are pages.
    return re.sub(r'\]\((?!https?://)([a-z0-9._-]+)\.md([#)])',
                  lambda m: '](%s.html%s' % (m.group(1), m.group(2)), text)


versions = json.load(sys.stdin)
current = next((v for v in versions if v['from_feed']), versions[0])
written = 0

for v in versions:
    tag, ver = v['tag'], v['version']
    listing = gh('api', '/repos/%s/contents/docs?ref=%s' % (REPO, tag))
    try:
        entries = [e for e in json.loads(listing)
                   if e.get('type') == 'file' and e['name'].endswith('.md')]
    except Exception:
        print('[docs] %s: no docs/ at this tag, skipped' % ver, file=sys.stderr)
        continue

    outdir = os.path.join(STAGING, 'uapi', 'docs', ver)
    os.makedirs(outdir, exist_ok=True)
    pages = []

    for e in sorted(entries, key=lambda x: x['name']):
        raw = gh('api', '-H', 'Accept: application/vnd.github.raw',
                 '/repos/%s/contents/docs/%s?ref=%s' % (REPO, e['name'], tag))
        if not raw.strip():
            sys.exit('[docs] %s/%s came back empty' % (tag, e['name']))
        heading = re.search(r'^#\s+(.+)$', raw, re.M)
        title = heading.group(1).strip() if heading else e['name'][:-3]
        body = render_markdown(rewrite_links(raw))
        out = e['name'][:-3] + '.html'
        with open(os.path.join(outdir, out), 'w') as fh:
            fh.write(PAGE.format(title=html_mod.escape(title), version=html_mod.escape(ver),
                                 body=body, source=e['name'], tag=tag, repo=REPO))
        pages.append((out, title))
        written += 1

    items = '\n'.join('      <li><a href="%s">%s</a></li>' % (html_mod.escape(o), html_mod.escape(t))
                      for o, t in pages)
    index_body = ('<h2>uapi %s documentation</h2>\n'
                  '<p>Rendered from the repository at tag <code>%s</code>. '
                  'These pages describe %s specifically; a different release documents itself.</p>\n'
                  '<ul>\n%s\n</ul>' % (html_mod.escape(ver), tag, html_mod.escape(ver), items))
    with open(os.path.join(outdir, 'index.html'), 'w') as fh:
        fh.write(PAGE.format(title='Documentation', version=html_mod.escape(ver),
                             body=index_body, source='', tag=tag, repo=REPO))

    print('[docs] %s: %d pages' % (ver, len(pages)))

# Top-level index. Lists every version rather than redirecting, so an operator who has not
# crossed a major can find the docs that match what they are running.
links = '\n'.join(
    '      <li><a href="%s/">%s</a>%s</li>' % (html_mod.escape(v['version']),
                                               html_mod.escape(v['version']),
                                               ' - current release' if v['from_feed'] else '')
    for v in versions)
body = ('<h2>Documentation by release</h2>\n'
        '<p>Each set is rendered from that release\'s tag, because most of these pages name a '
        'specific API major. The current release is <strong>%s</strong>, serving its API under '
        '<code>%s</code>.</p>\n<ul>\n%s\n</ul>'
        % (html_mod.escape(current['version']), html_mod.escape(current['prefix']), links))
with open(os.path.join(STAGING, 'uapi', 'docs', 'index.html'), 'w') as fh:
    fh.write(PAGE.format(title='Documentation', version=html_mod.escape(current['version']),
                         body=body, source='', tag=current['tag'], repo=REPO))

print('[docs] %d pages across %d versions' % (written, len(versions)))

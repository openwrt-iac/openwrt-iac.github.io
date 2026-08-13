#!/usr/bin/env python3
"""Render the install-page version picker from list_versions.py's JSON on stdin.

Two parts, selected by argv[1], because only one of them has to be generated:

  select  the <label>/<select> plus the toggle script
  older   an install block per version that is no longer served by the feed

The current release's steps stay in the HTML file, so the primary path a visitor follows is
editable prose rather than a string inside this script. Only the older versions are generated,
and they differ in kind rather than in wording: the feed carries one version, so anything else
is a GitHub Release download and needs neither the signing key nor the repository entry.
"""
import html, json, sys

what = sys.argv[1] if len(sys.argv) > 1 else 'select'
versions = json.load(sys.stdin)
current = next((v for v in versions if v['from_feed']), versions[0])

if what == 'select':
    options = ''.join(
        '<option value="%s"%s>%s%s</option>' % (
            html.escape(v['version']),
            ' selected' if v is current else '',
            html.escape(v['version']),
            ' (current)' if v['from_feed'] else '')
        for v in versions)
    print(
        '<div class="version-picker">\n'
        '  <label for="uapi-version">Version to install</label>\n'
        '  <select id="uapi-version">%s</select>\n'
        '</div>\n'
        '<script>\n'
        '  document.getElementById("uapi-version").addEventListener("change", function (e) {\n'
        '    document.querySelectorAll(".version-steps").forEach(function (b) {\n'
        '      b.hidden = b.dataset.version !== e.target.value;\n'
        '    });\n'
        '  });\n'
        '</script>' % options)
    raise SystemExit(0)

blocks = []
for v in versions:
    if v['from_feed']:
        continue
    blocks.append(
        '<div class="version-steps" data-version="%s" hidden>\n'
        '  <ol>\n'
        '    <li>\n'
        '      <strong>Download the release</strong>\n'
        '<pre><code>wget %s \\\n'
        '     -O /tmp/uapi-%s.apk</code></pre>\n'
        '    </li>\n'
        '    <li>\n'
        '      <strong>Install it</strong>\n'
        '<pre><code>apk add --allow-untrusted /tmp/uapi-%s.apk</code></pre>\n'
        '    </li>\n'
        '  </ol>\n'
        '  <p class="micro">\n'
        '    The feed serves the current release only, so this one comes from its GitHub\n'
        '    Release and needs no signing key or repository entry. It serves its API under\n'
        '    <code>%s</code>, not <code>%s</code>.\n'
        '  </p>\n'
        '</div>' % (
            html.escape(v['version']), html.escape(v['url']), html.escape(v['version']),
            html.escape(v['version']), html.escape(v['prefix']),
            html.escape(current['prefix'])))

print('\n'.join(blocks) if blocks else
      '<!-- only one stable release exists, so there is nothing older to offer -->')

#!/usr/bin/env python3
"""Render the install-page version picker from list_versions.py's JSON on stdin.

Two parts, selected by argv[1], because only one of them has to be generated:

  select  the <label>/<select> plus the toggle script
  older   an install block per version that is no longer served by the feed

The current release's steps stay in the HTML file, so the primary path a visitor follows is
editable prose rather than a string inside this script. Only the older versions are generated,
and they differ in kind rather than in wording: an older version that the feed also serves
installs with a version constraint, and any other is a GitHub Release download that needs
neither the signing key nor the repository entry.
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
            ' (current)' if v is current else ' (also in the feed)' if v['from_feed'] else '')
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

FEED_BLOCK = """<div class="version-steps" data-version="%(version)s" hidden>
  <ol>
    <li>
      <strong>Trust the feed signing key</strong>
<pre><code>uclient-fetch -qO /etc/apk/keys/uapi-feed.pub.pem \\
    https://openwrt-iac.github.io/feed/uapi-feed.pub.pem</code></pre>
    </li>
    <li>
      <strong>Add the feed</strong>
<pre><code>echo 'https://openwrt-iac.github.io/feed/packages/all/uapi/packages.adb' \\
    &gt; /etc/apk/repositories.d/uapi.list
apk update</code></pre>
    </li>
    <li>
      <strong>Install</strong>
<pre><code>apk add 'uapi&lt;%(next_major)d'</code></pre>
    </li>
  </ol>
  <p class="micro">
    The feed serves this release beside %(current)s, for routers that %(current)s does not
    support. apk does not fall back to it on its own, so the version constraint picks it. The
    constraint stays in <code>/etc/apk/world</code>, and <code>apk upgrade</code> then keeps
    this major. A router that already runs it from the feed needs the same command once, or
    <code>apk upgrade</code> fails on %(current)s. It serves its API under
    <code>%(prefix)s</code>, not <code>%(current_prefix)s</code>.
  </p>
</div>"""

blocks = []
for v in versions:
    if v is current:
        continue
    if v['from_feed']:
        blocks.append(FEED_BLOCK % {
            'version': html.escape(v['version']),
            'next_major': int(v['version'].split('.')[0]) + 1,
            'current': html.escape(current['version']),
            'prefix': html.escape(v['prefix']),
            'current_prefix': html.escape(current['prefix'])})
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

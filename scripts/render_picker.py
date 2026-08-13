#!/usr/bin/env python3
"""Render the version picker from list_versions.py's JSON on stdin."""
import html, json, sys

versions = json.load(sys.stdin)

options = ''.join(
    '<option value="%s"%s>%s%s</option>' % (
        html.escape(v['version']),
        ' selected' if i == 0 else '',
        html.escape(v['version']),
        ' (current)' if v['from_feed'] else '')
    for i, v in enumerate(versions))

blocks = []
for i, v in enumerate(versions):
    if v['from_feed']:
        steps = (
            '<p>Served by the signed feed, so apk resolves it directly:</p>\n'
            '<pre><code>apk add uapi</code></pre>\n'
            '<p>To pin this exact build: <code>apk add uapi=%s</code>. '
            'Serves its API under <code>%s</code>.</p>'
            % (html.escape(v['pin']), html.escape(v['prefix'])))
    else:
        steps = (
            '<p>The feed carries only the current release, so fetch this one from its '
            'GitHub Release:</p>\n'
            '<pre><code>wget %s -O /tmp/uapi-%s.apk\n'
            'apk add --allow-untrusted /tmp/uapi-%s.apk</code></pre>\n'
            '<p>Serves its API under <code>%s</code>.</p>'
            % (html.escape(v['url']), html.escape(v['version']),
               html.escape(v['version']), html.escape(v['prefix'])))
    blocks.append('<div class="version-steps" data-version="%s"%s>\n%s\n</div>'
                  % (html.escape(v['version']), '' if i == 0 else ' hidden', steps))

print('<label for="uapi-version">Version</label>\n'
      '<select id="uapi-version">%s</select>\n%s\n'
      '<script>\n'
      '  document.getElementById("uapi-version").addEventListener("change", function (e) {\n'
      '    document.querySelectorAll(".version-steps").forEach(function (b) {\n'
      '      b.hidden = b.dataset.version !== e.target.value;\n'
      '    });\n'
      '  });\n'
      '</script>' % (options, '\n'.join(blocks)))

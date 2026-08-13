#!/bin/sh
# Render each released version's docs/ into the staging tree. Runs after stamp_facts.sh, which
# is what establishes the version list; render_docs.py takes that list on stdin.
#
# The repo stays the only place docs are written: this renders, it never authors. That is also
# why the wiki is disabled on the source repo, since a wiki is a second git repository with no
# review gate and only one "latest" state.
set -eu

: "${STAGING_DIR:?STAGING_DIR required}"

python3 scripts/list_versions.py | python3 scripts/render_docs.py

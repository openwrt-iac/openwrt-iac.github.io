#!/usr/bin/env python3
"""Replace a placeholder in a file with the contents of another file."""
import sys

page, placeholder, block = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(page).read()
open(page, 'w').write(text.replace(placeholder, open(block).read()))

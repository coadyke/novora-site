#!/usr/bin/env python3
"""Bump version to v27 across all files."""
import glob, re, json

NEW_VER = '20260609v27'

for f in sorted(glob.glob('/Users/coady/WorkBuddy/Claw/novora-site/articles/*.html')):
    with open(f) as fh:
        c = fh.read()
    c = re.sub(r'content="20260609v\d+"', f'content="{NEW_VER}"', c)
    with open(f, 'w') as fh:
        fh.write(c)

# Also update index.html
for f in ['/Users/coady/WorkBuddy/Claw/novora-site/index.html']:
    with open(f) as fh:
        c = fh.read()
    c = re.sub(r'content="20260609v\d+"', f'content="{NEW_VER}"', c)
    with open(f, 'w') as fh:
        fh.write(c)

# version.json
with open('/Users/coady/WorkBuddy/Claw/novora-site/version.json', 'w') as fh:
    json.dump({'version': NEW_VER, 'ts': '2026-06-09T23:10:00+08:00'}, fh)

# version.txt
with open('/Users/coady/WorkBuddy/Claw/novora-site/version.txt', 'w') as fh:
    fh.write(NEW_VER + '\n')

print(f'All bumped to {NEW_VER}')

#!/usr/bin/env python3
"""Clean up leftover poster card HTML and CSS from all articles."""

import glob
import re

files = sorted(glob.glob('/Users/coady/WorkBuddy/Claw/novora-site/articles/*.html'))

for f in files:
    with open(f) as fh:
        c = fh.read()

    # Remove orphaned share-card HTML remnants (between </div><!--close share-panel--> and <script>)
    c = re.sub(
        r'</div>\s*<!--\s*close share-panel\s*-->\s*<div class="share-card-body">.*?</div>\s*<script>',
        '</div>\n<script>',
        c,
        flags=re.DOTALL
    )
    # Fallback: remove any orphaned share-card-* lines
    c = re.sub(
        r'\n\s*<div class="share-card-body">.*?</button>\s*\n\s*</div>\s*\n</div>',
        '',
        c,
        flags=re.DOTALL
    )
    # Remove old share-card CSS rules (lines 93-100 area)
    c = re.sub(
        r'\n\s*\.share-card\s*\{[^}]*\}\s*\n\s*\.share-card-img[^}]*\}\s*\n\s*\.share-card-img img[^}]*\}\s*\n\s*\.share-card-body[^}]*\}\s*\n\s*\.share-card-title[^}]*\}\s*\n\s*\.share-card-brand[^}]*\}\s*\n\s*\.share-card-tip[^}]*\}\s*\n\s*\.share-card-close[^}]*\}',
        '',
        c,
        flags=re.DOTALL
    )

    with open(f, 'w') as fh:
        fh.write(c)
    print(f'Cleaned: {f}')

print(f'\nDone! {len(files)} files cleaned.')

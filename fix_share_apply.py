#!/usr/bin/env python3
"""Apply complete share overlay CSS + fix closeShareOverlay to all articles."""

import glob
import re

FULL_CSS = """  /* Share toast & overlay */
  .share-toast { position:fixed; bottom:40px; left:50%; transform:translateX(-50%); background:#0F2747; color:#fff; padding:10px 24px; border-radius:8px; font-size:14px; z-index:10001; opacity:0; transition:opacity .3s; pointer-events:none; white-space:nowrap; }
  .share-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.55); backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px); display:flex; align-items:center; justify-content:center; z-index:10000; opacity:0; pointer-events:none; transition:opacity .25s; }
  .share-overlay.show { opacity:1; pointer-events:auto; }
  .share-panel { background:#fff; border-radius:16px; padding:32px 28px 24px; max-width:400px; width:88vw; text-align:center; box-shadow:0 20px 60px rgba(0,0,0,0.25); }
  .share-panel-icon { font-size:40px; margin-bottom:8px; }
  .share-panel-title { font-size:17px; font-weight:700; color:#0F2747; margin:0 0 6px; }
  .share-panel-sub { font-size:13px; color:#5f6b7a; margin:0 0 20px; line-height:1.6; }
  .share-panel-url { display:flex; gap:8px; align-items:center; background:#f4f6f9; border-radius:10px; padding:10px 14px; font-size:12px; color:#3b4556; word-break:break-all; margin-bottom:16px; }
  .share-panel-copy { display:inline-flex; align-items:center; gap:6px; background:#0F2747; color:#fff; border:none; border-radius:8px; padding:10px 22px; font-size:14px; font-weight:600; cursor:pointer; }
  .share-panel-copy:hover { background:#1a3560; }
  .share-panel-close { display:block; margin:16px auto 0; background:none; border:none; color:#8c97a8; font-size:13px; cursor:pointer; }"""

FILES = sorted(glob.glob('/Users/coady/WorkBuddy/Claw/novora-site/articles/*.html'))

for f in FILES:
    # Skip the already-fixed template
    if 'huzhou-trial-production' in f:
        print(f'SKIP (already fixed): {f}')
        continue

    with open(f) as fh:
        c = fh.read()

    # 1. Replace minimal CSS block with full overlay CSS
    c = re.sub(
        r'  /\* Share toast & overlay \*/\s*\n\s*\.share-toast[^}]*\}',
        FULL_CSS,
        c,
        flags=re.DOTALL
    )

    # 2. Fix closeShareOverlay missing closing brace
    c = re.sub(
        r'(function closeShareOverlay\(\)\{\s*document\.getElementById\([^)]+\)\.classList\.remove\([^)]+\);\s*)\n\s*\n\s*// -- novora logo',
        r'\1}\n\n  // -- novora logo',
        c,
        flags=re.DOTALL
    )

    with open(f, 'w') as fh:
        fh.write(c)
    print(f'Fixed: {f}')

print(f'\nDone!')

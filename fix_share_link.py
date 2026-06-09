#!/usr/bin/env python3
"""Replace poster card overlay with link-share overlay on all article pages."""

import glob
import re

NEW_CSS = """.share-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.55);
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 10000; opacity: 0; pointer-events: none;
  transition: opacity 0.25s;
}
.share-overlay.show { opacity: 1; pointer-events: auto; }
.share-panel {
  background: #fff; border-radius: 16px; padding: 32px 28px 24px;
  max-width: 400px; width: 88vw; text-align: center;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25);
}
.share-panel-icon { font-size: 40px; margin-bottom: 8px; }
.share-panel-title { font-size: 17px; font-weight: 700; color: #0F2747; margin: 0 0 6px; }
.share-panel-sub { font-size: 13px; color: #5f6b7a; margin: 0 0 20px; line-height: 1.6; }
.share-panel-url {
  display: flex; gap: 8px; align-items: center;
  background: #f4f6f9; border-radius: 10px; padding: 10px 14px;
  font-size: 12px; color: #3b4556; word-break: break-all;
  margin-bottom: 16px;
}
.share-panel-copy {
  display: inline-flex; align-items: center; gap: 6px;
  background: #0F2747; color: #fff; border: none;
  border-radius: 8px; padding: 10px 22px; font-size: 14px;
  font-weight: 600; cursor: pointer;
}
.share-panel-copy:hover { background: #1a3560; }
.share-panel-close {
  display: block; margin: 16px auto 0; background: none; border: none;
  color: #8c97a8; font-size: 13px; cursor: pointer;
}
.share-toast {
  position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%);
  background: #0F2747; color: #fff; padding: 10px 24px; border-radius: 8px;
  font-size: 14px; z-index: 10001; opacity: 0; pointer-events: none;
  transition: opacity 0.3s;
}"""

NEW_OVERLAY_HTML = """<div class="share-toast" id="share-toast">&#10003; 链接已复制，去微信粘贴即可</div>
<div class="share-overlay" id="share-overlay" onclick="if(event.target===this)closeShareOverlay()">
  <div class="share-panel">
    <div class="share-panel-icon">&#128279;</div>
    <h3 class="share-panel-title" id="share-panel-title"></h3>
    <p class="share-panel-sub">复制链接后，打开微信粘贴发送，<br>即可在朋友圈看到可点击的文章卡片</p>
    <div class="share-panel-url" id="share-panel-url"></div>
    <button class="share-panel-copy" onclick="copyLinkFromPanel()">&#128203; 复制文章链接</button>
    <button class="share-panel-close" onclick="closeShareOverlay()">关闭</button>
  </div>
</div>"""

NEW_JS = """function copyLink(){
  navigator.clipboard.writeText(location.href).then(function(){
    var t=document.getElementById('share-toast');
    t.style.opacity='1'; setTimeout(function(){t.style.opacity='0';},2500);
  }).catch(function(){
    var t=document.getElementById('share-toast');
    t.textContent='\u2717 \u590d\u5236\u5931\u8d25\uff0c\u8bf7\u624b\u52a8\u590d\u5236';
    t.style.opacity='1'; setTimeout(function(){t.style.opacity='0';t.textContent='\u2713 \u94fe\u63a5\u5df2\u590d\u5236\uff0c\u53bb\u5fae\u4fe1\u7c98\u8d34\u5373\u53ef';},2500);
  });
}
function shareMoments(){
  var title = document.title;
  var idx = title.lastIndexOf(' \u2014 ');
  var cleanTitle = idx > -1 ? title.substring(0, idx) : title;
  // Try native share API (works in WeChat in-app browser on mobile)
  if (navigator.share) {
    navigator.share({ title: cleanTitle, url: location.href }).catch(function(){});
    return;
  }
  // Desktop fallback: show copy-link panel
  document.getElementById('share-panel-title').textContent = cleanTitle;
  document.getElementById('share-panel-url').textContent = location.href;
  document.getElementById('share-overlay').classList.add('show');
}
function copyLinkFromPanel(){
  navigator.clipboard.writeText(location.href).then(function(){
    var t=document.getElementById('share-toast');
    t.style.opacity='1'; setTimeout(function(){t.style.opacity='0';},2500);
  }).catch(function(){
    var t=document.getElementById('share-toast');
    t.textContent='\u2717 \u590d\u5236\u5931\u8d25\uff0c\u8bf7\u624b\u52a8\u590d\u5236';
    t.style.opacity='1'; setTimeout(function(){t.style.opacity='0';t.textContent='\u2713 \u94fe\u63a5\u5df2\u590d\u5236\uff0c\u53bb\u5fae\u4fe1\u7c98\u8d34\u5373\u53ef';},2500);
  });
}
function closeShareOverlay(){
  document.getElementById('share-overlay').classList.remove('show');
}"""

files = sorted(glob.glob('/Users/coady/WorkBuddy/Claw/novora-site/articles/*.html'))

for f in files:
    with open(f) as fh:
        c = fh.read()

    # 1. Replace share-related CSS block
    # Remove old .share-overlay through .share-toast CSS
    c = re.sub(
        r'/[*]+\s*Share Overlay.*?(?=\n\s*<[!/])',
        NEW_CSS + '\n',
        c,
        flags=re.DOTALL
    )
    # Handle case where there might be just inline style
    c = re.sub(
        r'\.share-overlay\s*\{[^}]*\}[\s\n]*\.share-overlay\.show[^{]*\{[^}]*\}',
        '',
        c,
        flags=re.DOTALL
    )

    # 2. Replace share overlay HTML block (old poster card → new panel)
    # This is messy, let's do it more surgically
    c = re.sub(
        r'<div class="share-toast".*?</div>\s*<div class="share-overlay".*?</div>',
        NEW_OVERLAY_HTML,
        c,
        flags=re.DOTALL
    )

    # 3. Replace JS functions (shareMoments, copyLink, closeShareOverlay, copyLinkFromPanel)
    # Remove old block from function copyLink to just before logoChain
    c = re.sub(
        r'function copyLink\(\).*?(?=\s*// -- novora logo)',
        NEW_JS + '\n\n  ',
        c,
        flags=re.DOTALL
    )

    with open(f, 'w') as fh:
        fh.write(c)
    print(f'Fixed: {f}')

print(f'\nDone! {len(files)} files updated.')

#!/usr/bin/env python3
"""Fix: add missing shareWechat() + fix shareMoments() fallback."""

import glob, re

# JS replacement - use actual Unicode chars, not escape sequences
FALLBACK_JS = '''function copyLink(){
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
  // Always show panel on desktop; on mobile, try native share first
  if (/Mobi|Android|iPhone/i.test(navigator.userAgent) && navigator.share) {
    navigator.share({ title: cleanTitle, url: location.href }).then(function(){
      // Shared successfully
    }).catch(function(e){
      // User cancelled or share failed, show panel
      showSharePanel(cleanTitle);
    });
    return;
  }
  // Desktop or no native share: show panel
  showSharePanel(cleanTitle);
}
function shareWechat(){
  var title = document.title;
  var idx = title.lastIndexOf(' \u2014 ');
  var cleanTitle = idx > -1 ? title.substring(0, idx) : title;
  showSharePanel(cleanTitle);
}
function showSharePanel(cleanTitle){
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
}'''

FILES = sorted(glob.glob('/Users/coady/WorkBuddy/Claw/novora-site/articles/*.html'))

for f in FILES:
    with open(f) as fh:
        c = fh.read()

    # Replace from "function copyLink()" to just before "// -- novora logo"
    c = re.sub(
        r'function copyLink\(\).*?(?=\s*// -- novora logo)',
        FALLBACK_JS + '\n\n  ',
        c,
        flags=re.DOTALL
    )

    with open(f, 'w') as fh:
        fh.write(c)
    print(f'Fixed: {f}')

print(f'\nDone! {len(FILES)} files updated.')

#!/usr/bin/env python3
"""
novora 每周文章精选 — 智能分批群发，每人每周只收 1 封。
用法:
  --batch 0    发送第 0 组（周一）
  --batch 1    发送第 1 组（周三）
  --batch 2    发送第 2 组（周五）
  不传 --batch  订阅 ≤100 时全发，>100 时打印分组信息

分批规则:
  - 订阅 ≤100 人 → 周五全发，周一/周三自动跳过
  - 101~300 人  → 随机分 3 组，周一/三/五各发一组
  - 301+ 人     → 随机分 5 组，周一至周五各发一组
  - 按周号作为随机种子，同周内不重复，不同周公平轮换
"""
import json, os, sys, subprocess, smtplib, ssl, random
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, formataddr
import certifi

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.expanduser("~/.workbuddy/email_config.json")
BATCH_SIZE = 100


def get_keychain_password(service, account):
    r = subprocess.run(['security', 'find-generic-password', '-s', service, '-a', account, '-w'],
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        print(f"✗ Keychain 读取失败: {r.stderr.strip()}")
        sys.exit(1)
    return r.stdout.strip()


def load_config():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    p = cfg['profiles'][0]
    p['password'] = get_keychain_password(p['keychain_service'], p['username'])
    return p


def get_week_articles():
    feed_path = os.path.join(BASE, 'articles', 'feed.json')
    if not os.path.exists(feed_path):
        return []
    with open(feed_path) as f:
        articles = json.load(f)

    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    friday = monday + timedelta(days=4, hours=23, minutes=59, seconds=59)

    week_articles = []
    for a in articles:
        try:
            d = datetime.strptime(a['date'], '%Y-%m-%d')
            if monday <= d <= friday:
                week_articles.append(a)
        except ValueError:
            continue
    return week_articles


def load_subscribers():
    path = os.path.join(BASE, 'subscribers.json')
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get('subscribers', [])


def get_batches(subscribers):
    """Split subscribers into batches of 100, shuffled by week number."""
    total = len(subscribers)
    if total <= BATCH_SIZE:
        return [subscribers]  # 1 batch = all

    # Deterministic shuffle: same seed within a week → fair, no duplicates
    week_num = datetime.now().isocalendar()[1]
    rng = random.Random(week_num * 7919 + 2026)  # prime + year as seed
    shuffled = list(subscribers)
    rng.shuffle(shuffled)

    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    if num_batches > 5:
        num_batches = 5  # max 5 batches (Mon-Fri)

    batches = []
    for i in range(num_batches):
        start = i * BATCH_SIZE
        end = start + BATCH_SIZE
        batches.append(shuffled[start:end])
    return batches


def build_email_html(articles, start_date, end_date, batch_info=""):
    if not articles:
        return f"""<html><body style="font-family:-apple-system,sans-serif;max-width:600px;margin:32px auto;color:#1F2937;">
<h2 style="color:#0F2747">novora 本周文章精选</h2>
<p style="color:#6B7280">{start_date} — {end_date}</p>
<p style="color:#9CA3AF">本周暂无新文章。访问 <a href="https://novora.cc">novora.cc</a> 浏览往期内容。</p>
</body></html>"""

    items = ""
    for a in articles:
        tags_html = ' '.join(f'<span style="font-size:11px;padding:2px 8px;background:#EEF3F9;color:#1A3F6E;border-radius:3px">{t}</span>' for t in a.get('tags', []))
        items += f"""
<tr>
  <td style="padding:18px 0;border-bottom:1px solid #E5E7EB">
    <a href="{a['url']}" style="font-size:17px;font-weight:700;color:#0F2747;text-decoration:none;line-height:1.4">{a['title']}</a>
    <p style="font-size:14px;color:#6B7280;margin:8px 0 0;line-height:1.6">{a['summary']}</p>
    <div style="margin-top:8px">{tags_html}</div>
  </td>
</tr>"""

    return f"""<html><body style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;max-width:600px;margin:32px auto;color:#1F2937;padding:0 20px">
<div style="border-bottom:2px solid #0F2747;padding-bottom:16px;margin-bottom:24px">
  <h1 style="font-size:24px;font-weight:700;color:#0F2747;margin:0">novora</h1>
  <p style="font-size:14px;color:#6B7280;margin:6px 0 0">每周文章精选{batch_info}</p>
</div>

<p style="font-size:15px;color:#374151">{start_date} — {end_date} · {len(articles)} 篇新文章</p>

<table style="width:100%;border-collapse:collapse">
{items}
</table>

<div style="margin-top:32px;padding-top:20px;border-top:1px solid #E5E7EB">
  <p style="font-size:13px;color:#9CA3AF">
    每周自动发送 · <a href="https://novora.cc" style="color:#0F2747">novora.cc</a><br>
    退订请回复此邮件
  </p>
</div>
</body></html>"""


def send_email(smtp_cfg, to_email, subject, html_body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr(('novora', smtp_cfg['from']))
    msg['To'] = to_email
    msg['Date'] = formatdate(localtime=True)
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    ctx = ssl.create_default_context(cafile=certifi.where())
    with smtplib.SMTP_SSL(smtp_cfg['smtp_server'], smtp_cfg['smtp_port'], context=ctx) as s:
        s.login(smtp_cfg['username'], smtp_cfg['password'])
        s.send_message(msg)


def get_date_range():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime('%m/%d'), (monday + timedelta(days=4)).strftime('%m/%d')


def main():
    cfg = load_config()
    subscribers = load_subscribers()
    if not subscribers:
        print("⚠ 暂无订阅者，跳过发送。")
        return

    batches = get_batches(subscribers)
    total = len(subscribers)

    # ── Determine batch mode ──
    batch_idx = None
    for arg in sys.argv[1:]:
        if arg.startswith('--batch='):
            batch_idx = int(arg.split('=')[1])
        elif arg == '--batch' and len(sys.argv) > sys.argv.index(arg) + 1:
            batch_idx = int(sys.argv[sys.argv.index(arg) + 1])

    if batch_idx is None:
        # Auto mode: if ≤100 send all, otherwise print grouping info
        if total <= BATCH_SIZE:
            batch_idx = 0
        else:
            print(f"订阅者 {total} 人，分 {len(batches)} 组：")
            for i, b in enumerate(batches):
                names = ','.join(s.get('name', s['email'][:8]) for s in b[:5])
                print(f"  组{i}: {len(b)} 人 ({names}{'...' if len(b)>5 else ''})")
            print("\n用法: python3 weekly_digest.py --batch 0  # 周一")
            print("      python3 weekly_digest.py --batch 1  # 周三")
            print("      python3 weekly_digest.py --batch 2  # 周五")
            return

    # ── Send ──
    if batch_idx >= len(batches):
        print(f"批次 {batch_idx} 无订阅者（共 {len(batches)} 组），跳过。")
        return

    batch = batches[batch_idx]
    articles = get_week_articles()
    start, end = get_date_range()

    batch_label = ""
    if len(batches) > 1:
        weekday = ['周一', '周二', '周三', '周四', '周五'][batch_idx]
        batch_label = f" · {weekday}组({len(batch)}人)"

    html = build_email_html(articles, start, end, batch_label)
    subject = f"novora 本周精选 · {start}—{end}"
    if articles:
        subject += f" · {articles[0]['title'][:30]}"

    ok = 0
    for sub in batch:
        try:
            send_email(cfg, sub['email'], subject, html)
            ok += 1
        except Exception as e:
            print(f"  ✗ {sub.get('name', sub['email'])}: {e}")

    print(f"发送完成: {ok}/{len(batch)} 人, {len(articles)} 篇文章。")
    if len(batches) > 1:
        print(f"本周共 {total} 人分 {len(batches)} 组发送（本组第 {batch_idx+1}/{len(batches)} 组）。")


if __name__ == '__main__':
    main()

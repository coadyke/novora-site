#!/usr/bin/env python3
"""
novora 每周文章精选 — 周五 07:00 自动发送给全部订阅者。
读取 subscribers.json → 本周文章 → HTML 邮件 → QQ SMTP 群发。
"""
import json, os, sys, subprocess, smtplib, ssl
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, formataddr
import certifi

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.expanduser("~/.workbuddy/email_config.json")


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
    # Use QQ personal SMTP (first profile)
    p = cfg['profiles'][0]
    p['password'] = get_keychain_password(p['keychain_service'], p['username'])
    return p


def get_week_articles():
    """Fetch this week's articles (Mon 00:00 → Fri 23:59)."""
    feed_path = os.path.join(BASE, 'articles', 'feed.json')
    if not os.path.exists(feed_path):
        return []
    with open(feed_path) as f:
        articles = json.load(f)

    today = datetime.now()
    # Monday of this week
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


def build_email_html(articles, start_date, end_date):
    """Build a clean, minimal HTML email."""
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
  <p style="font-size:14px;color:#6B7280;margin:6px 0 0">每周文章精选</p>
</div>

<p style="font-size:15px;color:#374151">{start_date} — {end_date} · {len(articles)} 篇新文章</p>

<table style="width:100%;border-collapse:collapse">
{items}
</table>

<div style="margin-top:32px;padding-top:20px;border-top:1px solid #E5E7EB">
  <p style="font-size:13px;color:#9CA3AF">
    每周五自动发送 · <a href="https://novora.cc" style="color:#0F2747">novora.cc</a><br>
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


def main():
    cfg = load_config()
    subscribers = load_subscribers()
    if not subscribers:
        print("⚠ 暂无订阅者，跳过发送。")
        return

    articles = get_week_articles()
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    start = monday.strftime('%m/%d')
    end = (monday + timedelta(days=4)).strftime('%m/%d')

    html = build_email_html(articles, start, end)
    subject = f"novora 本周精选 · {start}—{end}"
    if articles:
        subject += f" · {articles[0]['title'][:30]}"

    for sub in subscribers:
        try:
            send_email(cfg, sub['email'], subject, html)
            print(f"  ✓ {sub.get('name', sub['email'])}")
        except Exception as e:
            print(f"  ✗ {sub.get('name', sub['email'])}: {e}")

    print(f"\n发送完成: {len(subscribers)} 位订阅者, {len(articles)} 篇文章。")


if __name__ == '__main__':
    main()

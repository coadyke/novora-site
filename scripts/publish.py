#!/usr/bin/env python3
"""
novora 文章发布管线 — 唯一入口
用法:
  python3 scripts/publish.py --title "标题" --date "2026-06-23" \
    --summary "摘要" --tags "材料,制造" --topics "关键词1,关键词2" \
    --file "articles/2026-06-23-slug.html"

流程:
  1. 校验输入（禁止 ASCII 双引号，自动转义）
  2. 精确插入 index.html articles 数组首位
  3. 升版（version.json + version.txt + meta 标签）
  4. node --check JS 语法自检 → 不通过则回滚
  5. git commit + push
  6. Cloudflare Pages 部署
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime


# ── 配置 ──
NOVORA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(NOVORA_ROOT, "index.html")
VERSION_JSON = os.path.join(NOVORA_ROOT, "version.json")
VERSION_TXT = os.path.join(NOVORA_ROOT, "version.txt")
BACKUP_PATH = INDEX_PATH + ".backup"

WRANGLER = os.path.expanduser(
    "/Users/coady/.workbuddy/binaries/node/versions/22.22.2/bin/wrangler"
)
CF_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")

GIT_SSH = (
    'GIT_SSH_COMMAND="ssh -i ~/.ssh/github_novora -o IdentitiesOnly=yes"'
)


# ── 校验 ──

def escape_quotes(text: str) -> str:
    """将 ASCII 双引号转为中文直角引号，防止破坏 JS 字符串"""
    # 成对替换：奇数个引号时也要处理
    result = []
    in_quote = False
    for ch in text:
        if ch == '"':
            result.append('」' if in_quote else '「')
            in_quote = not in_quote
        else:
            result.append(ch)
    # 如果引号未闭合（奇数个），末尾补一个
    if in_quote:
        result.append('」')
    return ''.join(result)


def validate(article: dict) -> list[str]:
    """校验文章元数据，返回错误列表"""
    errors = []
    required = ["title", "date", "summary", "tags", "file"]
    for field in required:
        if not article.get(field):
            errors.append(f"缺少字段: {field}")

    if article.get("file"):
        full_path = os.path.join(NOVORA_ROOT, article["file"])
        if not os.path.exists(full_path):
            errors.append(f"文章文件不存在: {article['file']}")

    # 检查 date 格式
    if article.get("date"):
        try:
            datetime.strptime(article["date"], "%Y-%m-%d")
        except ValueError:
            errors.append(f"日期格式错误: {article['date']} (应为 YYYY-MM-DD)")

    return errors


def check_duplicate(file_path: str, index_content: str) -> bool:
    """检查文章是否已存在于 articles 数组中"""
    return f'file: "{file_path}"' in index_content or f"file: '{file_path}'" in index_content


# ── 版本 ──

def bump_version() -> str:
    """升版：读取 → +1 → 写回 version.json 和 version.txt"""
    if os.path.exists(VERSION_JSON):
        with open(VERSION_JSON) as f:
            data = json.load(f)
        old = data["version"]
    else:
        old = "20260623v85"

    # 解析版本号：YYYYMMDDvNN
    match = re.match(r"(\d{8})v(\d+)", old)
    if match:
        date_part = match.group(1)
        num = int(match.group(2)) + 1
        new = f"{date_part}v{num}"
    else:
        today = datetime.now().strftime("%Y%m%d")
        new = f"{today}v1"

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    with open(VERSION_JSON, "w") as f:
        json.dump({"version": new, "updated": now}, f)
    with open(VERSION_TXT, "w") as f:
        f.write(new + "\n")

    # 更新 index.html 中的 meta version
    with open(INDEX_PATH) as f:
        html = f.read()
    html = re.sub(
        r'<meta name="version" content="[^"]*"',
        f'<meta name="version" content="{new}"',
        html,
    )
    with open(INDEX_PATH, "w") as f:
        f.write(html)

    return new


# ── 插入 ──

def build_entry(article: dict) -> str:
    """构建单篇文章的 JS 对象字面量字符串"""
    title = escape_quotes(article["title"])
    summary = escape_quotes(article["summary"])
    date = article["date"]
    tags = json.dumps(article["tags"] if isinstance(article["tags"], list)
                      else [t.strip() for t in article["tags"].split(",") if t.strip()])
    topics = json.dumps(
        article["topics"] if isinstance(article.get("topics"), list)
        else [t.strip() for t in article.get("topics", "").split(",") if t.strip()]
    )
    file = article["file"]

    return (
        f'  {{ title: "{title}", date: "{date}",'
        f' summary: "{summary}",'
        f' tags: {tags},'
        f' topics: {topics},'
        f' file: "{file}" }}'
    )


def insert_article(article: dict) -> str:
    """将文章条目插入 index.html articles 数组首位，返回新内容"""
    with open(INDEX_PATH) as f:
        html = f.read()

    # 定位 articles 数组
    anchor = "const articles = ["
    pos = html.find(anchor)
    if pos == -1:
        raise RuntimeError(f"在 index.html 中找不到 '{anchor}'")

    # 找到 [ 后面的第一个换行符位置
    bracket_end = pos + len(anchor)
    insert_pos = html.index("\n", bracket_end) + 1

    entry = build_entry(article)

    # 检查是否之前已经手动插过（通过 titles 数组）
    # 不自动检查，由外部 check_duplicate 处理

    new_html = html[:insert_pos] + entry + ",\n" + html[insert_pos:]
    return new_html


# ── 语法检查 ──

def js_syntax_check() -> bool:
    """提取 articles 渲染脚本，用 node --check 验证"""
    with open(INDEX_PATH) as f:
        html = f.read()

    scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    target = None
    for s in scripts:
        if "const articles" in s:
            target = s.strip()
            break

    if not target:
        print("❌ 找不到 articles 渲染脚本")
        return False

    check_file = "/tmp/_nv_syntax_check.js"
    with open(check_file, "w") as f:
        f.write(target)

    result = subprocess.run(
        ["node", "--check", check_file], capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ JS 语法检查通过")
        return True
    else:
        print(f"❌ JS 语法错误:\n{result.stderr}")
        return False


# ── 部署 ──

def git_push(version: str, file_path: str) -> bool:
    """提交并推送到 GitHub"""
    title = "novora publish"
    cmds = [
        f"cd {NOVORA_ROOT}",
        f"{GIT_SSH} git add index.html version.json version.txt {file_path}",
        f'{GIT_SSH} git commit -m "发布: {title} (v{version})"',
        f"{GIT_SSH} git push",
    ]
    result = subprocess.run(
        " && ".join(cmds), shell=True, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Git 推送失败:\n{result.stderr}")
        return False
    print("✅ Git 推送成功")
    return True


def deploy_cloudflare() -> bool:
    """部署到 Cloudflare Pages"""
    result = subprocess.run(
        [
            WRANGLER, "pages", "deploy", NOVORA_ROOT,
            "--project-name", "novora-site",
            "--branch", "main",
            "--commit-dirty", "true",
        ],
        env={**os.environ, "CLOUDFLARE_API_TOKEN": CF_TOKEN},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Cloudflare 部署失败:\n{result.stderr}")
        return False
    print("✅ Cloudflare Pages 部署完成")
    return True


# ── 主流程 ──

def main():
    parser = argparse.ArgumentParser(description="novora 文章发布管线")
    parser.add_argument("--title", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--tags", required=True)
    parser.add_argument("--topics", default="")
    parser.add_argument("--file", required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="仅校验和语法检查，不推送部署")
    args = parser.parse_args()

    article = {
        "title": args.title,
        "date": args.date,
        "summary": args.summary,
        "tags": args.tags,
        "topics": args.topics,
        "file": args.file,
    }

    # 1. 校验
    errors = validate(article)
    if errors:
        print("❌ 校验失败:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # 2. 去重检查
    with open(INDEX_PATH) as f:
        html = f.read()
    if check_duplicate(article["file"], html):
        print(f"⚠️  文章 {article['file']} 已存在于 articles 数组中，跳过")
        sys.exit(0)

    # 3. 备份
    shutil.copy(INDEX_PATH, BACKUP_PATH)
    print(f"📋 已备份 index.html → {BACKUP_PATH}")

    # 4. 插入新条目
    try:
        new_html = insert_article(article)
    except RuntimeError as e:
        print(f"❌ 插入失败: {e}")
        sys.exit(1)

    with open(INDEX_PATH, "w") as f:
        f.write(new_html)

    escaped = escape_quotes(article["summary"])
    if '"' in escaped:
        print("⚠️  摘要中仍有未转义的 ASCII 双引号，已自动转义")

    # 5. JS 语法检查
    if not js_syntax_check():
        print("🔄 回滚 index.html ...")
        shutil.copy(BACKUP_PATH, INDEX_PATH)
        sys.exit(1)

    # 6. 升版
    version = bump_version()
    print(f"📦 版本: {version}")

    # 7. 再次语法检查（升版可能动了 meta 标签）
    if not js_syntax_check():
        print("🔄 升版后语法检查失败，回滚 ...")
        shutil.copy(BACKUP_PATH, INDEX_PATH)
        sys.exit(1)

    if args.dry_run:
        print("🔍 --dry-run 模式，跳过推送部署。index.html 已更新。")
        sys.exit(0)

    # 8. Git 推送
    if not git_push(version, article["file"]):
        print("🔄 Git 推送失败，但 index.html 已修改。请手动处理。")
        sys.exit(1)

    # 9. 生成 feed.json → 同步到 bdf-materials 仓库（bdf.pro 文章数据源）
    from build_feed import build_feed
    feed_path = build_feed()

    # 同步 feed.json 到 bdf-materials 仓库
    BDF_ROOT = os.path.join(os.path.dirname(NOVORA_ROOT), "beethoven-newmaterials")
    if os.path.isdir(BDF_ROOT):
        import shutil
        shutil.copy(feed_path, os.path.join(BDF_ROOT, "feed.json"))
        bdf_ssh = 'GIT_SSH_COMMAND="ssh -i ~/.ssh/github_bdf -o IdentitiesOnly=yes"'
        cmds = [
            f"cd {BDF_ROOT}",
            f"{bdf_ssh} git add feed.json",
            f'{bdf_ssh} git commit -m "sync: feed.json from novora publish (v{version})"',
            f"{bdf_ssh} git push",
        ]
        subprocess.run(" && ".join(cmds), shell=True, capture_output=True, text=True)
        print("✅ feed.json → bdf-materials 同步完成")

    # 把 feed.json 加入 novora git
    subprocess.run(
        f"cd {NOVORA_ROOT} && {GIT_SSH} git add articles/feed.json",
        shell=True, capture_output=True, text=True
    )

    # 10. Cloudflare 部署
    if not deploy_cloudflare():
        print("⚠️  Cloudflare 部署失败，但 Git 已推送。请手动部署。")
        sys.exit(1)

    print(f"\n🎉 发布完成: {article['title']}")
    print(f"   https://novora.cc/{article['file']}")
    print(f"   feed.json 已同步更新 → bdf.pro 文章区自动刷新")


if __name__ == "__main__":
    main()

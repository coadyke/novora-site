#!/usr/bin/env python3
"""
从 index.html 的 articles 数组提取所有文章，生成 feed.json
这是 bdf.pro「产业观察」区块的数据源。
publish.py 每次发布新文章后自动调用此脚本。
"""
import json
import os
import re
import sys

NOVORA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(NOVORA_ROOT, "index.html")
FEED_PATH = os.path.join(NOVORA_ROOT, "articles", "feed.json")


def parse_articles(html: str) -> list[dict]:
    """从 index.html 中提取 articles 数组的完整 JavaScript 对象"""
    # 找到 const articles = [ ... ];
    match = re.search(r"const articles\s*=\s*\[(.*?)\];", html, re.DOTALL)
    if not match:
        raise RuntimeError("找不到 articles 数组")

    body = match.group(1)

    # 切分为单个对象字面量
    entries = []
    depth = 0
    current = ""
    in_string = False
    escape_next = False

    for ch in body:
        if escape_next:
            current += ch
            escape_next = False
            continue
        if ch == '\\':
            current += ch
            escape_next = True
            continue
        if ch == '"' and not in_string:
            in_string = True
            current += ch
            continue
        if ch == '"' and in_string:
            in_string = False
            current += ch
            continue
        if in_string:
            current += ch
            continue
        if ch in '[{':
            depth += 1
            current += ch
        elif ch in '}]':
            depth -= 1
            current += ch
        elif ch == ',' and depth == 0:
            entry = current.strip()
            if entry and entry != ']':
                entries.append(entry)
            current = ""
        else:
            current += ch

    # 最后一个
    entry = current.strip()
    if entry and entry != ']':
        entries.append(entry)

    # 解析每个对象
    articles = []
    for entry in entries:
        article = {}
        # 简单字段: title, date, summary, file
        for field in ["title", "date", "summary", "file"]:
            m = re.search(f'{field}:\\s*"((?:[^"\\\\]|\\\\.)*)"', entry)
            if m:
                article[field] = m.group(1)

        # tags 数组
        m_tags = re.search(r'tags:\s*(\[[^\]]*\])', entry)
        if m_tags:
            try:
                article["tags"] = json.loads(m_tags.group(1))
            except json.JSONDecodeError:
                article["tags"] = []

        # topics 数组
        m_topics = re.search(r'topics:\s*(\[[^\]]*\])', entry)
        if m_topics:
            try:
                article["topics"] = json.loads(m_topics.group(1))
            except json.JSONDecodeError:
                article["topics"] = []

        # 构建 URL
        if article.get("file"):
            article["url"] = f"https://novora.cc/{article['file']}"

        if article.get("title"):
            articles.append(article)

    return articles


def build_feed(output_path: str = None) -> str:
    """生成 feed.json，返回文件路径"""
    if output_path is None:
        output_path = FEED_PATH

    with open(INDEX_PATH) as f:
        html = f.read()

    articles = parse_articles(html)

    # 按日期降序
    articles.sort(key=lambda a: a.get("date", ""), reverse=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"✅ feed.json 已生成: {len(articles)} 篇文章 → {output_path}")
    return output_path


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    build_feed(path)

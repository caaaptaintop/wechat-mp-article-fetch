#!/usr/bin/env python3
"""
按帖子方法：用微信内置浏览器请求头拉取「已经有链接」的公众号文章。

适用：收藏夹 / 分享记录里已有一批 mp.weixin.qq.com/s/... 链接。
不适用：从一个公众号名直接翻出全部历史文章。

依赖：
    pip install requests beautifulsoup4 lxml

用法：
    1. 把链接一行一个放进 urls.txt
    2. python wechat_fetch_by_url.py
    3. 结果在 out/<文章标题>/ ：article.md + images/01.xxx 02.xxx ...
"""

from __future__ import annotations

import hashlib
import mimetypes
import random
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

WECHAT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Mobile/15E148 "
        "MicroMessenger/8.0.50(0x1800323d) NetType/WIFI Language/zh_CN"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://mp.weixin.qq.com/",
    "Connection": "keep-alive",
}

ROOT = Path(__file__).resolve().parent
URL_FILE = ROOT / "urls.txt"
OUT_DIR = ROOT / "out"


def slug(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|\s]+", "_", text).strip("_")
    text = re.sub(r"_+", "_", text)
    return (text[:80] or "untitled")


def fetch(url: str) -> str:
    resp = requests.get(url, headers=WECHAT_HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def guess_ext(url: str, content_type: str | None) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        ext = mimetypes.guess_extension(ct) or ""
        if ext == ".jpe":
            ext = ".jpg"
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def download_image(session: requests.Session, url: str, dest_stem: Path) -> Path | None:
    """下载到 dest_stem 同目录，文件名为 stem + 正确后缀。成功返回最终 Path。"""
    try:
        headers = dict(WECHAT_HEADERS)
        headers["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
        resp = session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        ext = guess_ext(url, resp.headers.get("Content-Type"))
        dest = dest_stem.with_suffix(ext)
        dest.write_bytes(resp.content)
        return dest
    except Exception as e:
        print(f"      !! 图片失败 {url[:80]}… ({e})")
        return None


def parse_and_save(html: str, url: str, article_dir: Path) -> dict:
    soup = BeautifulSoup(html, "lxml")

    page_text = soup.get_text(" ", strip=True)
    blocked_hints = ("请在微信客户端打开", "环境异常", "完成验证", "操作频繁")
    if any(h in page_text[:800] for h in blocked_hints) and not soup.select_one("#js_content"):
        raise RuntimeError("被拦截，页面不是正文。可换住宅网络、加大间隔，或改用本机浏览器打开该链接。")

    title = ""
    if soup.select_one("#activity-name"):
        title = soup.select_one("#activity-name").get_text(strip=True)
    elif soup.select_one('meta[property="og:title"]'):
        title = soup.select_one('meta[property="og:title"]').get("content", "").strip()

    author = ""
    if soup.select_one("#js_name"):
        author = soup.select_one("#js_name").get_text(strip=True)

    pub = ""
    if soup.select_one("#publish_time"):
        pub = soup.select_one("#publish_time").get_text(strip=True)

    content = soup.select_one("#js_content")
    if not content:
        raise RuntimeError("找不到 #js_content，链接可能不是公开图文，或需要登录/关注。")

    for img in content.select("img"):
        src = img.get("data-src") or img.get("src") or ""
        if src:
            img["src"] = src

    images_dir = article_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    img_index = 0
    local_by_remote: dict[str, str] = {}

    parts = [f"# {title}", ""]
    meta = " | ".join(x for x in (author, pub, url) if x)
    if meta:
        parts += [meta, ""]

    for node in content.find_all(["p", "h1", "h2", "h3", "section", "img"], recursive=True):
        if node.name == "img":
            src = node.get("src") or ""
            if not src:
                continue
            if src in local_by_remote:
                parts.append(f"![]({local_by_remote[src]})")
                continue
            img_index += 1
            stem = images_dir / f"{img_index:02d}"
            written = download_image(session, src, stem)
            time.sleep(random.uniform(0.3, 0.8))
            if written is not None:
                rel = f"images/{written.name}"
                local_by_remote[src] = rel
                parts.append(f"![]({rel})")
            else:
                parts.append(f"![]({src})")
            continue
        text = node.get_text("\n", strip=True)
        if text:
            parts.append(text)
            parts.append("")

    body = "\n".join(parts).strip() + "\n"
    md_path = article_dir / "article.md"
    md_path.write_text(body, encoding="utf-8")
    return {
        "title": title or "untitled",
        "author": author,
        "published": pub,
        "images": img_index,
        "md": md_path,
    }


def unique_article_dir(title: str, url: str) -> Path:
    base = slug(title or "untitled")
    candidate = OUT_DIR / base
    if not candidate.exists():
        return candidate
    digest = hashlib.md5(url.encode()).hexdigest()[:6]
    return OUT_DIR / f"{base}_{digest}"


def main() -> None:
    if not URL_FILE.exists():
        URL_FILE.write_text(
            "# 每行一个文章链接，例如：\n"
            "# https://mp.weixin.qq.com/s/xxxxxxxx\n",
            encoding="utf-8",
        )
        print(f"已创建 {URL_FILE}，请填入链接后重新运行。")
        return

    urls = []
    for line in URL_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "mp.weixin.qq.com" in line:
            urls.append(line)

    if not urls:
        print("urls.txt 里没有有效的公众号文章链接。")
        return

    OUT_DIR.mkdir(exist_ok=True)
    ok, fail = 0, 0
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        try:
            html = fetch(url)
            # peek title for folder name
            soup = BeautifulSoup(html, "lxml")
            title = ""
            if soup.select_one("#activity-name"):
                title = soup.select_one("#activity-name").get_text(strip=True)
            elif soup.select_one('meta[property="og:title"]'):
                title = soup.select_one('meta[property="og:title"]').get("content", "").strip()
            article_dir = unique_article_dir(title, url)
            article_dir.mkdir(parents=True, exist_ok=True)
            art = parse_and_save(html, url, article_dir)
            print(f"    -> {article_dir.name}/article.md （图片 {art['images']} 张）")
            ok += 1
        except Exception as e:
            print(f"    !! {e}")
            fail += 1
        time.sleep(random.uniform(1.5, 3.5))

    print(f"完成：成功 {ok}，失败 {fail}，输出目录 {OUT_DIR}")


if __name__ == "__main__":
    main()

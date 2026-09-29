# wechat-mp-article-fetch

按「模拟微信内置浏览器请求头」抓取**单篇**微信公众号图文，并落盘为：

```
out/<文章标题>/
  article.md
  images/
    01.png
    02.png
    ...
```

> 不支持从一个公众号名自动翻全部历史列表（公开列表接口已失效）。请自备 `mp.weixin.qq.com/s/...` 链接。

## 安装

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 用法

1. 复制 `urls.txt.example` 为 `urls.txt`，每行一个文章链接。
2. 运行：

```bash
.venv/bin/python wechat_fetch_by_url.py
```

3. 打开 `out/` 查看结果。正文里的图片为相对路径 `images/01.xxx`。

## Agent Skill

仓库根目录 `SKILL.md` 可供 Cursor / Grok Bot 等当作 skill 使用（描述见 frontmatter）。

## 许可

MIT

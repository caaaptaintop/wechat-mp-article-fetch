---
name: 公众号单篇抓取
description: >-
  当用户要抓取单篇微信公众号文章（mp.weixin.qq.com/s/...）并落盘为
  「文章标题文件夹 + article.md + images/01.xxx」时使用。
  不适用于翻公众号全部历史列表。
---

# 公众号单篇抓取

把已有的 `https://mp.weixin.qq.com/s/...` 链接抓成：

`out/<文章标题>/article.md` + `out/<文章标题>/images/01.png`（按出现顺序编号）

## 前置

- Python 3 + venv
- 依赖见 `requirements.txt`
- 脚本：同仓库 `wechat_fetch_by_url.py`

## 步骤

1. 确认用户给的是**公开图文链接**（含 `mp.weixin.qq.com/s/`）。没有链接则先要链接；不要尝试用公众号名拉全量历史。
2. 同目录准备 `urls.txt`（可参考 `urls.txt.example`），每行一个链接。
3. 安装并运行：
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/python wechat_fetch_by_url.py
   ```
4. 检查 `out/<标题>/article.md` 与 `images/01.*`、`02.*`…
5. 若被拦截或找不到 `#js_content`：换网络、加大间隔，或确认链接在浏览器可打开。
6. 把结果路径交给用户。

## 注意

- 只抓已有链接；不能从公众号名翻全部历史。
- 图片下载失败时 md 可能回退为微信图床 URL。
- 勿写入 Cookie / token / 密码。

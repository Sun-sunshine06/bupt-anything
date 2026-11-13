# 文档站维护与部署

站点地址：[bupt-anything 文档](https://sun-sunshine06.github.io/bupt-anything/)。站点使用 Material for MkDocs，由 GitHub Pages 托管。

## 内容来源

现有 `docs/` 文档及根目录的贡献、安全、更新记录和许可证文件是内容来源。快速开始从 README 的对应章节提取；无需维护第二份安装说明。首页维护在 `docs/index.md`。

`scripts/build_docs.py` 使用明确的公开文件清单生成临时文档目录，转换站内链接并生成页面摘要。它不会遍历或发布 `private/`、`artifacts/`、下载文件、凭据或整个工作目录。构建产物 `site/` 不提交到 Git。

新增页面时，更新构建脚本的 `PAGES` 映射（来源、标题、摘要）和 `mkdocs.yml` 导航。保留准确的能力与验证边界，避免只更新营销描述。

## 本地构建与检查

```bash
uv sync --frozen --group docs
uv run --frozen --group docs python scripts/build_docs.py
uv run --frozen --group docs python scripts/check_docs.py
uv run --frozen --group docs python -m http.server 8000 --directory site --bind 127.0.0.1
```

浏览器打开 `http://127.0.0.1:8000`。结束预览时按 Ctrl+C。修改内容后重新构建并刷新页面。

检查覆盖站内页面与资源链接、锚点、唯一页面标题与摘要、规范网址、JSON-LD、搜索索引和站点地图。生产路径还需通过已部署网址验证。

## 自动部署

`.github/workflows/docs.yml` 在 Pull Request 中只构建和检查；推送到 `main` 或手动触发时，在检查通过后部署。部署使用 GitHub Pages 官方 Actions，仅部署作业具有 `pages: write` 和 `id-token: write` 权限，不需要在仓库中保存访问令牌。

GitHub 仓库 Settings → Pages 的 Source 使用 GitHub Actions。修改文档、配置或依赖后，检查 Actions 中的 Documentation 工作流；部署失败时，已发布版本通常仍保留，先查看失败日志再重试。回退内容应提交一个恢复改动，由同一工作流重新部署。

## SEO 与 AI 检索

- 每页有独立标题、内容摘要和 canonical URL；生成绝对地址站点地图 `sitemap.xml`。
- 页面正文以静态 HTML 输出，客户端 JavaScript 主要用于导航、主题和本地搜索。
- 首页提供与可见内容一致的 `SoftwareSourceCode` 结构化数据，内容页提供 `TechArticle` 数据；不添加虚构评分、认证或背书。
- 首页与英文概览使用互相对应的语言链接。常见问题、工具参考和验证范围提供可引用的明确答案。
- `llms.txt` 是可选的精简阅读索引，不代表搜索引擎或 AI 平台一定会读取，也不保证收录、排名或引用。
- 当前为 GitHub Pages 项目站点，没有自定义域名；项目子路径下的 `robots.txt` 无法控制域名根路径的爬虫规则，因此不放置误导性配置。

站点上线不等于已被索引。维护者可在完成站点所有权验证后，将 `https://sun-sunshine06.github.io/bupt-anything/sitemap.xml` 提交给搜索引擎站长工具，并观察真实的搜索与引用表现。本项目不会自动创建分析账号或添加访客跟踪。

参考：[Google AI 搜索说明](https://developers.google.com/search/docs/appearance/ai-features)、[GitHub Pages 工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。

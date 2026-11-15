"""Build the public documentation from an explicit list of repository sources."""

import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from mkdocs.commands.build import build
from mkdocs.config import load_config

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://sun-sunshine06.github.io/bupt-anything/"
REPO_URL = "https://github.com/Sun-sunshine06/bupt-anything"
# output: (source, title, description). Only these public sources enter the site.
PAGES = {
    "index.md": ("docs/index.md", "北邮校园 MCP Server 与 CLI", "bupt-anything 是北邮非官方开源校园工具箱，通过本地 MCP 与 CLI 查询课表、空教室、教学云作业和资料。"),
    "getting-started.md": ("README.md", "安装与首次查询", "从克隆项目、uv 安装、配置移动教务和教学云账号，到执行第一次查询和连接 MCP 客户端。"),
    "mcp.md": ("docs/mcp.md", "MCP 客户端接入", "配置本地 stdio MCP 服务、设置项目路径和账号别名，并检查 bupt-anything 工具连接状态。"),
    "faq.md": ("docs/faq.md", "常见问题：北邮 MCP 与教学云查询", "了解 bupt-anything 的适用人群、学校账号要求、MCP 兼容性、系统支持和只读功能边界。"),
    "tools.md": ("docs/tools.md", "工具目录与查询示例", "查阅 25 个校园工具的用途、消息通知与未开始作业发现、CLI 示例、分页及结构化返回约定。"),
    "attendance.md": ("docs/attendance.md", "考勤查询边界", "了解本人历史考勤与当前签到活动的只读查询范围，以及不提供的二维码和签到提交功能。"),
    "diagnostics.md": ("docs/diagnostics.md", "连接检查与诊断", "区分离线检查和真实账号联调，使用只输出状态与数量的诊断脚本安全排查连接问题。"),
    "validation.md": ("docs/validation.md", "验证范围与已知限制", "查看 bupt-anything 已验证的真实场景、合成测试覆盖和尚未充分验证的平台与接口样本。"),
    "architecture.md": ("docs/architecture.md", "架构与接口状态", "了解 CLI 与 MCP 共用业务逻辑、凭据与会话管理、数据流、结果契约及模块扩展边界。"),
    "contributing.md": ("CONTRIBUTING.md", "参与贡献", "配置开发环境、运行离线检查，并按合成样例、接口证据与隐私要求提交改动。"),
    "security.md": ("SECURITY.md", "安全、隐私与漏洞报告", "了解凭据存储、查询数据流向、敏感信息保护以及非公开安全漏洞报告方式。"),
    "changelog.md": ("CHANGELOG.md", "更新记录", "查阅 BUPT Agent 的版本变更、已实现能力与发布状态。"),
    "sources.md": ("docs/sources.md", "来源与致谢", "核对校园协议研究与参考项目的来源、版本、许可证及待核对事项。"),
    "releasing.md": ("docs/releasing.md", "版本发布流程", "了解干净发布版本、敏感信息检查、源码归档与私有开发历史隔离要求。"),
    "documentation.md": ("docs/documentation.md", "文档站维护与部署", "在本地构建和检查文档，通过 GitHub Actions 部署 GitHub Pages，维护搜索与 AI 检索所需内容。"),
    "license.md": ("LICENSE", "GPL-3.0-only 许可证", "bupt-anything 源代码的 GNU General Public License version 3 完整许可文本。"),
    "overview.en.md": ("docs/overview.en.md", "BUPT campus MCP server and CLI", "An unofficial, read-only campus toolkit for Beijing University of Posts and Telecommunications: features, setup, MCP integration and privacy."),
}


def rewrite_links(body, source):
    destinations = {(ROOT / value[0]).resolve(): name for name, value in PAGES.items()}
    destinations[ROOT / "docs/getting-started.md"] = "getting-started.md"

    def replace(match):
        target = match[1]
        parsed = urlsplit(target)
        if parsed.scheme or target.startswith(("#", "//")):
            return match[0]
        resolved = (source.parent / parsed.path).resolve()
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        if resolved == ROOT / "README.md":
            destination = "getting-started.md" if fragment else "index.md"
        elif resolved in destinations:
            destination = destinations[resolved]
        else:
            # Source/configuration links belong on GitHub, never on a nonexistent site path.
            relative = resolved.relative_to(ROOT).as_posix()
            if not resolved.is_file():
                raise ValueError(f"Missing documentation target: {relative}")
            destination = f"{REPO_URL}/blob/main/{relative}"
        return f"]({destination}{fragment})"

    return re.sub(r"\]\(([^)]+)\)", replace, body)


def main():
    with tempfile.TemporaryDirectory(prefix="bupt-docs-") as temporary:
        stage = Path(temporary)
        for output, (source_name, title, description) in PAGES.items():
            source = ROOT / source_name
            body = source.read_text(encoding="utf-8")
            if output == "getting-started.md":
                body = "# 快速开始\n\n" + body.split("## 快速开始\n", 1)[1].split(
                    "## 使用边界与隐私\n", 1
                )[0]
                body = body.replace("\n### ", "\n## ")
            if output == "license.md":
                body = "# GPL-3.0-only 许可证\n\n```text\n" + body + "\n```\n"
            body = rewrite_links(body, source)
            metadata = {"title": title, "description": description}
            if output == "overview.en.md":
                metadata["lang"] = "en"
            frontmatter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
            (stage / output).write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")
        shutil.copytree(ROOT / "docs/assets", stage / "assets")
        # An optional concise reading index, not a search ranking or AI inclusion requirement.
        lines = [
            "# bupt-anything", "",
            "> Unofficial BUPT campus MCP server and CLI. University operations are read-only.",
            "", "Python package: bupt-agent. MCP command: bupt-agent-mcp.",
            f"Source: {REPO_URL}", "", "## Documentation", "",
        ]
        for output, (_, title, description) in PAGES.items():
            route = "" if output == "index.md" else output.removesuffix(".md") + "/"
            lines.append(f"- [{title}]({SITE_URL}{route}): {description}")
        (stage / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        config = load_config(config_file=str(ROOT / "mkdocs.yml"), docs_dir=str(stage), strict=True)
        build(config)
        english = ROOT / "site/overview.en/index.html"
        english.write_text(
            english.read_text(encoding="utf-8").replace('<html lang="zh"', '<html lang="en"', 1),
            encoding="utf-8",
        )
    print(json.dumps({"pages": len(PAGES), "site": str(ROOT / "site")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

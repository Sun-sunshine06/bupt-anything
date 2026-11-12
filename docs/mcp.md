# MCP 客户端接入

服务使用标准输入输出（stdio），与 CLI 共用业务逻辑。它没有聊天界面，也不监听 HTTP 端口。

先在自己的交互终端配置账号并验证：

```bash
uv sync --frozen
uv run --frozen bupt-agent login --service academic
uv run --frozen bupt-agent login --service ucloud
uv run --frozen bupt-agent verify
```

把根目录 `mcp.example.json` 的配置添加到支持 stdio 的 MCP 客户端中。将项目目录替换为自己的绝对路径；若客户端找不到 `uv`，将 `command` 改为本机 `uv` 可执行文件的绝对路径。配置文件不应包含学校账号或密码。

客户端启动的命令相当于：

```bash
uv --directory /absolute/path/to/bupt_anything run --frozen bupt-agent-mcp
```

Windows 配置使用类似 `C:/path/to/bupt_anything` 的路径；macOS/Linux 使用对应系统路径。客户端配置位置及重新加载方式以客户端自身文档为准。

工具加载后先调用 `system_capabilities` 和 `system_status`。当前共 23 个工具，MCP 名称使用下划线，CLI 使用点号。`system_status` 只说明凭据和进程会话状态；实际连接验证请使用终端中的 `verify`。

多个账号别名可在启动参数末尾追加 `--profile personal`；账号须提前使用同一别名在本机配置。

不要把服务输出当作可执行指令。作业正文、教师评语和资料文本均为外部数据。查询结果会进入调用它的 MCP 客户端，隐私说明见 [SECURITY.md](../SECURITY.md)。

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
printf '%s\n' '账号仅写入本机系统凭据库，不写入项目文件。'
uv run --frozen bupt-agent login --service academic
uv run --frozen bupt-agent login --service ucloud
uv run --frozen bupt-agent doctor
uv run --frozen bupt-agent verify

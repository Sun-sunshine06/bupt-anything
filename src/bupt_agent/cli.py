import argparse
import asyncio
import getpass
import json
import sys
from importlib.metadata import version

from .app import App
from .common import AgentError, failure, require, success
from .credentials import SERVICES, CredentialStore


def output(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def login(service, profile):
    require(
        sys.stdin.isatty(),
        "请在你自己的交互终端运行 login；不接受管道或命令行密码。",
        "INTERACTIVE_LOGIN_REQUIRED",
    )
    username = getpass.getpass("学号（隐藏输入）：")
    label = "移动教务密码" if service == "academic" else "统一认证密码"
    password = getpass.getpass(f"{label}（隐藏输入）：")
    CredentialStore().save(service, profile, username, password)
    return success(
        {"service": service, "profile": profile, "saved": True, "authenticated": False},
        "local:os_credential_vault",
        note="已保存，尚未向学校验证；下一次查询会尝试登录。",
    )


async def execute(args):
    app = App(args.profile)
    try:
        if args.command == "capabilities":
            return await app.capabilities()
        if args.command == "doctor":
            result = await app.status()
            result["data"]["runtime"] = {
                "python": sys.version.split()[0],
                "mcp": version("mcp"),
                "transport": "stdio",
                "network_checked": False,
            }
            return result
        if args.command == "verify":
            checks = {}
            for service, tool_name in (
                ("academic", "academic.classrooms"),
                ("ucloud", "ucloud.courses"),
            ):
                result = await app.invoke(tool_name)
                checks[service] = (
                    {"ok": True, "read_verified": True, "checked_at": result["meta"]["fetched_at"]}
                    if result["ok"]
                    else {"ok": False, "error": result["error"]}
                )
            if not all(check["ok"] for check in checks.values()):
                return {
                    "ok": False,
                    "data": checks,
                    "error": {
                        "code": "VERIFICATION_INCOMPLETE",
                        "message": "部分系统未验证通过，见各系统状态。",
                    },
                }
            return success(checks, "live:school_read_checks")
        params = json.loads(args.args)
        require(isinstance(params, dict), "--args 必须是 JSON 对象。")
        return await app.invoke(args.tool, params)
    finally:
        await app.close()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="BUPT Agent：本地校园工具（输出 JSON）")
    parser.add_argument("--profile", default="default")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    sub.add_parser("doctor")
    sub.add_parser("verify", help="实际验证两套学校读取链路，只输出状态，不打印私人数据")
    for command in ("login", "logout"):
        p = sub.add_parser(command)
        p.add_argument("--service", choices=SERVICES, required=True)
    p = sub.add_parser("call")
    p.add_argument("tool")
    p.add_argument("--args", default="{}", help="JSON 对象；不包含密码或 token")
    args = parser.parse_args()
    try:
        if args.command == "login":
            result = login(args.service, args.profile)
        elif args.command == "logout":
            CredentialStore().delete(args.service, args.profile)
            result = success(
                {"deleted": True, "service": args.service}, "local:os_credential_vault"
            )
        else:
            result = asyncio.run(execute(args))
    except AgentError as error:
        result = failure(error)
    except json.JSONDecodeError:
        result = failure(AgentError("INVALID_INPUT", "--args 不是有效 JSON。"))
    except (KeyboardInterrupt, EOFError):
        result = failure(AgentError("CANCELLED", "操作已取消。"))
    output(result)
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()

# bupt-anything — BUPT campus MCP server and CLI

[中文首页](../README.md) · [FAQ (Chinese)](faq.md) · [MCP setup (Chinese)](mcp.md)

**bupt-anything is an unofficial, open-source campus toolkit for Beijing University of Posts and Telecommunications (BUPT).** It exposes campus queries through a local Model Context Protocol (MCP) server and a command-line interface. The package and CLI are named `bupt-agent` (BUPT Agent); the MCP entry point is `bupt-agent-mcp`.

Source repository: [Sun-sunshine06/bupt-anything](https://github.com/Sun-sunshine06/bupt-anything). License: [GPL-3.0-only](../LICENSE). The project is not affiliated with or endorsed by the university.

## Supported features

- Academic information: class schedules, terms, grades, exams, and today's available classrooms at the Xitucheng and Shahe campuses.
- UCloud teaching platform: courses, pending activities, assignment requirements, the user's submission records, teacher feedback, and peer reviews assigned to the user.
- Course materials: resource listings, preview links, downloads from verified university domains, and text extraction from PDF, DOCX, PPTX and TXT files downloaded by this tool.
- Attendance: read-only attendance history and current attendance activities.
- Campus information: public shuttle and competition information; today's study-slot suggestions based on class schedules, exams and classroom availability.

There are 23 tools. Run `uv run bupt-agent capabilities` for tool definitions. See the [tool reference](tools.md) and [validation scope](validation.md) for details and coverage limits.

## Getting started

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/). The project requires Python 3.12+. On Windows, run these commands in Git Bash:

```bash
git clone https://github.com/Sun-sunshine06/bupt-anything.git
cd bupt-anything
uv sync --frozen
uv run bupt-agent doctor
uv run bupt-agent login --service academic
uv run bupt-agent login --service ucloud
uv run bupt-agent verify
uv run bupt-agent call academic.schedule
```

Enter credentials interactively in your terminal. Academic login uses the mobile academic system password; UCloud uses the university's unified authentication password. The default dependency index is the Tsinghua PyPI mirror; see the [installation guide](../README.md#快速开始) for switching to PyPI.

For an AI client supporting local stdio MCP, copy [mcp.example.json](../mcp.example.json), replace the project directory with your absolute path, and reload the client. The client provides the model and chat interface; this project provides the tools.

## Status and privacy

This is an early development release. Windows with Git Bash has been validated; macOS and Linux credential backends are implemented, but end-to-end setup still needs validation. University API changes may affect functionality.

University operations are read-only. The project does not generate or parse attendance QR codes, submit attendance, submit assignments, or submit peer-review scores. It does not automate CAPTCHA/MFA or perform OCR on scanned documents. Classroom queries and study planning cover the current day in Beijing time and do not include personal calendars.

Credentials are stored in the operating system credential vault and used to authenticate with the corresponding services. Query results are displayed by the CLI or passed to the MCP client. Review your client's data handling before connecting a model provider. See [security and privacy](../SECURITY.md).

## Contributing

Bug reports, compatibility feedback, documentation improvements and pull requests are welcome. Follow the [contribution guide](../CONTRIBUTING.md), use synthetic test data, and never publish credentials or private academic content. Report vulnerabilities through the [private reporting process](../SECURITY.md).

# 来源与第三方说明

本项目按 GPL-3.0-only 分发；完整文本见根目录 LICENSE。以下区分协议/设计参考与运行时依赖，不宣称拥有上游代码或学校资料。

## 来源核对（2026-11-12）

| 项目 | 用途 | 检查时许可证 | 核对版本 |
|---|---|---|---|
| [Nemoyuzx/where_to_study](https://github.com/Nemoyuzx/where_to_study) | 教务/CAS 协议与公开信息源 | [GPL-3.0](https://github.com/Nemoyuzx/where_to_study/blob/main/LICENSE) | `114195057404339fbde575c916775b398b696fb7` |
| [YouXam/ucloud](https://github.com/YouXam/ucloud) | 教学云课程、待办、作业与资源协议 | [GPL-3.0](https://github.com/YouXam/ucloud/blob/main/LICENSE) | `1c0a1dfdf39337b2fc80752c4e802f8b65b66328` |
| [YouXam/ucloud-bot](https://github.com/YouXam/ucloud-bot) | 工作流设计参考，未引入其机器人实现 | [GPL-3.0](https://github.com/YouXam/ucloud-bot/blob/main/LICENSE) | `942fdead75de050bbaab07eaa184b20f6cd4af1f` |
| [uarix/ucloud-Evolved](https://github.com/uarix/ucloud-Evolved) | 资源树和下载预览协议 | [MIT](https://github.com/uarix/ucloud-Evolved/blob/main/LICENSE) | `67878916315ca02963f43020dfb18e9f4ea8ccc0` |
| [Yokumii/bupt-api-collected](https://github.com/Yokumii/bupt-api-collected) | 教务/教学云字段与提交记录读取线索 | [Apache-2.0](https://github.com/Yokumii/bupt-api-collected/blob/main/LICENSE) | `96bdc8faa21172773fa938f18b2a1b7e44bb843f` |
| [llcc01/ucloud-check](https://github.com/llcc01/ucloud-check) | 当前课堂与活动只读协议 | 未发现明确许可证 | `12f128462b5c19b71424073e15a61b03f0ea69b6` |
| [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | 运行时依赖，版本固定于 uv.lock | [MIT](https://github.com/modelcontextprotocol/python-sdk/blob/main/LICENSE) | `使用版本见 uv.lock` |

表中的版本是此次来源核对快照，不能冒充最初开发时的参考版本。除 `llcc01/ucloud-check` 已有确切记录外，早期参考提交未完整记录。GitHub 的 GPL-3.0 检测标签不代表已确认上游的 only/or-later 细节，应以各文件声明为准。

## 已有引用定位

- `where_to_study/src-tauri/src/{config,classrooms,schedule,academic,assignments}.rs` 与 `where-to-study-core/src/public_queries.rs`。
- `YouXam/ucloud/src/{auth,crawler,worker}.ts`。
- `ucloud-Evolved/ucloud-Evolved.user.js`。
- `llcc01/ucloud-check` 的 `12f128462b5c19b71424073e15a61b03f0ea69b6`：`src/req.tsx`、`src/App.tsx`，仅用于当前活动查询协议与字段核对。

现有实现记录将上述项目列为协议/字段/设计参考，发布包不附带其源码。不能据此推断所有代码已完成逐行原创性审查。尤其 `llcc01/ucloud-check` 未发现明确许可证，不能据此复制、移植或重新分发其代码；公开前应复核实现来源，若存在代码借用须取得许可或替换。此项属于发布前人工核对项。

## 运行时依赖

httpx、mcp、keyring、platformdirs、beautifulsoup4、pypdf、tzdata 的名称和版本以 pyproject.toml / uv.lock 为准。它们由安装工具独立下载，不在仓库中附带其源码；其许可证仍各自适用。

## 数据源

- 学校查询仅连接适配器中核验的 HTTPS 主机。
- 班车：https://where-to-study.cn/api/shuttle-bus
- 竞赛：https://nemoyuzx.github.io/contest-ddl/data/competitions.json

公开信息由第三方整理，抓取时间不等于更新时间。学校返回的数据、课件与用户内容不受本项目代码许可证自动授权。

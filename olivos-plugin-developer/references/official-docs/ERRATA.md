# OlivOS 开发文档勘误

快照来自 `OlivOS-Team/OlivOSDoc`，逐字同步，**不代表示例可直接运行**。
下面这些是已知的文档与源码不一致之处，写代码时以源码契约为准。

判定原则一句话：**文档的签名与目标版本的源码冲突时，信源码。**

## 1. `get_group_*` 示例漏了必需参数

| 文档示例 | 实际签名 | 源码位置 |
| --- | --- | --- |
| `plugin_event.get_group_info()` | `get_group_info(group_id, host_id=None, no_cache=False, ...)` | `OlivOS/core/core/API.py:2947` |
| `plugin_event.get_group_member_info()` | `get_group_member_info(group_id, user_id, host_id=None, ...)` | `OlivOS/core/core/API.py:3067` |
| `plugin_event.get_group_member_list()` | `get_group_member_list(group_id, host_id=None, ...)` | `OlivOS/core/core/API.py:3140` |

`api.md` 里这三处示例是无参调用，照抄会在 Python 参数绑定阶段直接 `TypeError`。
上游已在 `OlivOS-Team/OlivOSDoc#27` 提交修复；同步到修复后的版本后可以删掉本节。

同时注意说明文字也有串行：`get_group_member_list` 被写成「用于获取群列表」，
`get_group_member_info` 被写成「获取群信息」。

## 2. `UserModule.md` 示例里的 `proc.log`

用户模块示例写的是小写 `proc.log(0, ...)`，但回调参数名是 `Proc`，
同一文件与 `API.md` 其余位置都写作 `Proc.log`。按 `Proc.log` 写。

## 3. 快照内的链接已规范化

`references/official-docs/markdown/` 里的文档名是小写，上游写的是 `WebUI.md`、
`API.md`、`Schedule.md`、`/DevPlugin/UserModule/#_3` 这类大小写敏感或站内路由的写法。
同步脚本会把这些链接改写成快照内可达的目标（未收录的文档指向上游 GitHub，
站内路由指向 `https://doc.olivos.wiki`），所以**不要手工修改快照文件的链接**——
下次同步会被覆盖，要改就改 `scripts/sync_upstreams.py`。

## 发现新错误时

1. 先在目标版本的源码里确认真实签名或行为，别只对比另一篇文档。
2. 影响插件写法的，补进本文件。
3. 属于上游文档写错的，提 PR 到 `OlivOS-Team/OlivOSDoc`；合并并同步后删掉本文件的对应条目。

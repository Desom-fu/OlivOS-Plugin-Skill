# OlivOS Plugin Developer Skill 发布文档

## 概述

`olivos-plugin-developer` 是面向 OlivOS Python 插件开发的 Codex skill。它用于根据用户需求创建、修改、审查或解释 OlivOS 插件，尤其适合 OlivOS 插件模板、框架事件、插件 API、消息格式、用户模块、OlivaDiceCore 集成、跑团规则插件和 QQ 机器人插件开发场景。

该 skill 的核心原则是“以本地资料为准”。在生成插件代码前，它会优先参考随 skill 打包的 OlivOS 官方文档快照和三套本地模板，避免凭记忆臆造 API、事件、消息结构或 OlivaDiceCore 扩展点。

## 适用场景

- 从需求生成新的 OlivOS 插件目录和核心代码。
- 基于官方 native 模板实现极简独立插件。
- 基于 light plugin 模板实现常规复杂插件，包括多命令、配置、GUI、持久化、自定义回复词和权限控制。
- 基于 rule plugin 模板实现强依赖 OlivaDiceCore 的 TRPG 规则扩展、人物卡或骰系行为。
- 审查现有 OlivOS 插件是否遵守事件入口、消息格式、配置读写和异常隔离约束。
- 解释 OlivOS 插件结构、生命周期事件、消息模式、用户配置数据库和主动发消息方式。

## 论坛发布链接

[OlivOS 论坛发布帖](https://forum.olivos.run/d/917-olivos-skill)

## 下载

最新自动打包 release：

[olivos-plugin-developer-latest](https://github.com/Desom-fu/OlivOS-Plugin-Skill/releases/tag/olivos-plugin-developer-latest)

### 官方文档快照

本 skill 内置 OlivOS 官方开发文档 Markdown 快照，来源记录见 `references/official-docs/SOURCES.md`。

- 来源仓库：`https://github.com/OlivOS-Team/OlivOSDoc`
- 分支：`main`
- 对应快照的 commit 和日期见 `olivos-plugin-developer/references/official-docs/SOURCES.md`。

内置文档包括：

- `template.md`：插件目录结构、`app.json` 字段、菜单注册、资源目录和 OPK 打包格式。
- `event.md`：OlivOS 框架事件、事件入口原型、`plugin_event`/`Proc` 参数、消息事件、通知事件、请求事件和元事件。
- `api.md`：`plugin_event` 与 `Proc` 常用接口，包括发送、回复、阻塞、撤回、群管理、请求处理、列表查询、文件、公告、合并转发和 OneBot 相关扩展接口。
- `message.md`：`old_string`、`olivos_string`、`olivos_para` 三种消息模式，以及 OP/CQ 码、转义规则、图片、语音、回复、at、合并转发等消息类型。
- `user-module.md`：`Proc.database` 用户配置数据库、用户/群/基础配置读写接口、`pkl` 使用规则，以及 IOStream 输入流说明。
- `webui.md`：来自 `docs/DevPlugin/WebUI.md` 的插件 WebUI 开发接口文档，包含 `webui_config`、消息桥、`Event.menu` 请求处理、`send('webui', ...)` 回包、沙箱限制和打包要求；不是 `docs/User/WebUI.md` 使用指南。

### 自动同步与打包

每 6 小时检查上游，收到 `desom-templates-updated` 事件时也会检查。同步范围包括上述 6 份开发文档、已收录的模板文件、官方模板 `OlivOSPluginTemplate/webui/` 下的网页资源，以及 Light 模板的 `YourPluginName/webui.py` 和 `YourPluginName/webui/`（包含新增文件）。
每 30 分钟检查上游，支持在 GitHub Actions 手动触发，收到 `desom-templates-updated` 事件时也会检查。同步范围包括上述 6 份开发文档、已收录的模板文件、官方模板 `OlivOSPluginTemplate/webui/` 下的网页资源，以及 Light 模板的 `YourPluginName/webui.py` 和 `YourPluginName/webui/`（包含新增文件）。

只有收录的文档或模板实际内容变化时，自动同步才会提交、打包并更新 release。上游仅增加提交、修改其他文件或改变 commit hash/日期时，不更新来源记录、不打包。`SOURCES.md` 记录最近一次快照内容更新时的上游版本，文档与模板分别判断；自动变更检测会忽略这两份来源记录，并识别尚未跟踪的新增文件。普通 push 也不会因只有来源记录变化而打包；手动触发打包工作流仍可重建 release。

本地回归检查：`python -m unittest discover -s tests -v`。

### 模板

模板来源记录见 `assets/templates/SOURCES.md`。

- `official-native`：来自 `OlivOS-Team/OlivOSPluginTemplate`，仓库 `https://github.com/OlivOS-Team/OlivOSPluginTemplate`。
- `light-plugin`：来自 `Desom-OlivaDice-Plugin/示例/LightPluginTemplate`，仓库 `https://github.com/0Desom0/Desom-OlivaDice-Plugin/tree/main/示例/LightPluginTemplate`。
- `rule-plugin`：来自 `Desom-OlivaDice-Plugin/示例/Desom's_OVO_PluginTemplate`，仓库 `https://github.com/0Desom0/Desom-OlivaDice-Plugin/tree/main/示例/Desom's_OVO_PluginTemplate`。

## 模板能力

### Official Native 模板

路径：`assets/templates/official-native/`

这是 OlivOS 官方最小插件模板，本地收录 `app.json`、`__init__.py`、`main.py`、`webui/index.html` 和 lint 配置。它演示了标准 `main.Event` 入口、`init`、`init_after`、`private_message`、`group_message`、`poke`、`save`、`menu` 等事件，通过伪事件对象进行主动发消息的 `send_message_force` 写法，以及 WebUI 页面与 Python 间的请求和回包。

适合需求简单、命令少、无复杂配置和存储、无桌面 GUI，或只需要简单 WebUI 页面的插件。WebUI 不要求 Node.js、npm 或额外 Web 服务；完整通信需在 OlivOS 宿主中验证。

### Light Plugin 模板

路径：`assets/templates/light-plugin/`

这是常规复杂插件的默认首选模板。它把职责拆分为：

- `main.py`：只保留 OlivOS 事件入口。
- `message.py`：负责命令解析、开关判断、权限判断和回复组织。
- `utils.py`：负责日志、异常隔离、文件读写、目录初始化、bot 配置、群链、OP at 解析、命令解析、骰主/群管权限、OlivaDiceCore 可用性检查、主动发送和回复封装。
- `gui.py`：提供 Tkinter 配置面板，包括全局配置、Bot 配置、回复词管理和骰主列表管理。
- `config.py`：保存静态常量、默认配置、命令前缀和数据目录定义。
- `message_custom.py`：保存默认自定义回复、变量、帮助文档和 GUI 说明。
- `function.py`：预留纯业务逻辑模块。

它支持全局开关、Bot 级开关、按原始 bot hash 保存 `bot_config.json`、按 linked bot hash 共享 `storage`、`message_custom.json` 和 `message_variable.json`。如果环境存在 OlivaDiceCore，会尝试识别主从 bot 群链、骰主权限、群启用状态，并可把回复写入 OlivaDiceLogger 钩子。

适合多命令、配置、GUI、持久化、自定义回复词、权限控制，以及可选接入 OlivaDiceCore 的插件。

### Rule Plugin 模板

路径：`assets/templates/rule-plugin/`

这是面向 OlivaDiceCore 的规则插件模板，`app.json` 默认使用 `old_string` 消息模式，优先级建议小于 `20000`。模板包含：

- `main.py`：转发初始化、私聊、群聊、菜单等事件。
- `msgReply.py`：核心命令解析和回复处理位置。
- `msgCustom.py`：自定义回复、默认变量和帮助文档。
- `msgCustomManager.py`：向 OlivaDiceCore 与可选 OlivaDiceNativeGUI 注入自定义回复、帮助文档和 GUI 说明。

适合 TRPG 规则扩展、人物卡、骰系命令、需要 OlivaDiceCore 的 `replyMsg`、`msgCustomManager`、骰主体系或 bot on/off 体系的插件。

## 模板选择规则

skill 会选择“足够完成需求的最轻模板”：

- 无 OlivaDiceCore 依赖，功能极简，命令少于 3 个或只需简单 WebUI，且没有桌面 GUI 或复杂存储：选择 Official Native。
- 可以独立运行，但包含多命令、配置、GUI、存储、自定义回复或权限管理：选择 Light Plugin。
- 强依赖 OlivaDiceCore，涉及 TRPG 规则、人物卡、自定义回复注入或骰系生态：选择 Rule Plugin。

## 本地安装（多客户端同步）

仓库内的 `olivos-plugin-developer/` 是唯一真源，各客户端的个人 skill 目录都由脚本从该目录镜像同步，避免多份副本各自漂移。

双击仓库根目录的 `install-skill.bat`，或直接运行：

```bash
python scripts/install_skill.py            # 安装 / 更新全部已支持的客户端
python scripts/install_skill.py --verify   # 只核对现有安装，不写入
python scripts/install_skill.py --dry-run  # 预览将要执行的动作
python scripts/install_skill.py --only codex,claudecode,grok,antigravity,agents
python scripts/install_skill.py --skip workbuddy,dsh
```

同步目标（相对用户主目录）：

| 客户端 | skills 目录 |
| --- | --- |
| Agents 约定（Codex / Grok / Antigravity 都会扫描） | `~/.agents/skills/` |
| Codex | `~/.codex/skills/` |
| Claude Code | `~/.claude/skills/` |
| Grok CLI | `~/.grok/skills/` |
| Antigravity（全局 customization） | `~/.gemini/config/skills/` |
| WorkBuddy | `~/.workbuddy/skills/` |
| DSH | `~/.dsh/skills/` |
| QoderWork CN | `~/.qoderworkcn/skills/` |

覆盖旧副本前会先把它移到系统临时目录备份；安装完成后逐文件比对 SHA-256，缺失、多余或内容不一致都会把该客户端标记为 `FAIL` 并以非零退出码结束。

## 使用方式

用户可以直接描述插件需求，例如：

```text
使用 olivos-plugin-developer 写一个 OlivOS 插件：
群聊里输入 .hello 时回复“你好”，私聊也可用，不依赖 OlivaDiceCore。
```

也可以要求修改、审查或解释现有插件：

```text
用 olivos-plugin-developer 审查这个 OlivOS 插件的事件入口和消息解析是否正确。
```

当需求不完整时，skill 只会询问避免错误实现所必需的最少信息，例如插件名称、是否依赖 OlivaDiceCore、命令格式或数据是否需要持久化。

## 输出规范

当用户提供具体插件需求时，skill 的最终回答固定包含：

1. `需求分析`：概括核心行为与重要约束。
2. `模板选择`：说明选择哪套模板，以及为什么它是最轻合适选择。
3. `代码实现`：给出完整文件树和核心代码。
4. `部署说明`：说明配置路径、依赖、运行注意事项和验证步骤。

默认使用中文回答。生成代码面向 Python 3.11，并遵守模板中的 flake8 和 Ruff 约束。

## 开发约束

- 只使用本地文档、模板、官方来源或用户本地项目中确证存在的 API。
- 不臆造 OlivOS 事件、`plugin_event` 方法、消息段结构或 OlivaDiceCore 接口。
- 写插件前必须先读取所选模板的实际文件，再改名、替换 namespace 和实现业务。
- `app.json` 需要维护正确的 `namespace`、`message_mode`、`compatible_svn`、`priority`、`support` 和菜单事件。
- 事件入口必须放在插件命名空间下的 `main.Event` 类中，签名为 `def method_name(plugin_event, Proc):`。
- 文件 I/O、网络请求、配置读写和消息解析应使用 `try/except` 隔离错误，避免插件异常拖垮 OlivOS 宿主。
- 消息处理应按 `message_mode` 使用对应格式：CQ 码、OP 码或 OlivOS 消息段。
- `Proc.database` 适合轻量配置项，不适合作为高频大体量业务数据存储。
- 涉及 OlivaDiceCore 时，只使用模板或源代码中已有的扩展点与函数。

## 数据与配置约定

官方文档规定源码开发模式下插件位于 `plugin/app/<namespace>/`。插件资源目录 `data` 会在 `init` 与 `init_after` 之间复制到 `plugin/data/<namespace>/data`。

light 模板进一步约定：

- 全局配置：`plugin/data/YourPluginName/global_config.json`
- 原始 Bot 配置：`plugin/data/YourPluginName/<raw_bot_hash>/bot_config.json`
- linked Bot 回复词：`plugin/data/YourPluginName/<linked_bot_hash>/message_custom.json`
- linked Bot 变量：`plugin/data/YourPluginName/<linked_bot_hash>/message_variable.json`
- linked Bot 存储目录：`plugin/data/YourPluginName/<linked_bot_hash>/storage/`

这种设计让每个 bot 保持独立开关，同时允许主从 bot 共享回复词、变量和业务存储。

## 质量标准

模板内置 lint 约束：

- flake8：`max-line-length = 120`，忽略 `E203`，允许 `*/__init__.py` 出现 `F401`。
- Ruff：4 空格缩进、单引号、目标 Python 3.11、规则集 `E`、`W`、`F`、`I`、`B`、`C4`、`UP`。

生成代码应保持导入有序、避免无用 import，注释应简洁说明生命周期、配置、消息解析、权限和持久化行为。

## 发布清单

本次 skill 包含以下内容：

- `SKILL.md`：skill 主说明、触发场景、模板决策树、响应格式和开发守则。
- `agents/openai.yaml`：界面展示名称、短描述和默认提示词。
- `references/official-docs/`：OlivOS 官方开发文档 Markdown 快照及来源记录。
- `assets/templates/official-native/`：官方最小插件模板。
- `assets/templates/light-plugin/`：常规复杂插件模板。
- `assets/templates/rule-plugin/`：OlivaDiceCore 规则插件模板。
- `RELEASE.zh-CN.md`：中文发布文档。

## 已知边界

- 在线文档只作为缺失或刷新本地资料时的后备来源。
- 如果用户需求依赖未收录、未验证或项目中不存在的接口，skill 会说明缺口，并给出最接近的安全实现路径。
- 对强平台特性的 OneBot 扩展接口，应按文档中的支持平台与协议说明处理兼容性。
- OPK 打包本质是插件源码目录 zip 后改后缀为 `.opk`，具体 CI 流程应参考官方模板工作流。

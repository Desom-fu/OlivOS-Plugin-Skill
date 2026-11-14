# OlivOS 插件开发速查

主入口只留判断规则，翻手册时才读这一页。

## 生命周期事件

```
init          → 模块导入后立即触发（不看优先级）
init_after    → 所有模块导入完成后触发（严格按优先级）
message/notify → 运行期事件，按优先级流过插件
save          → 插件即将被重载时触发（持久化）
menu          → 菜单项被点击时触发（严格按优先级）
```

所有事件回调签名：`def method_name(plugin_event, Proc):`

## app.json

必须是 UTF-8 无 BOM。从 PowerShell 写要用显式无 BOM 编码器
（`[System.IO.File]::WriteAllText($path, $json, [System.Text.UTF8Encoding]::new($false))`），
不要用 Windows PowerShell 5.1 的 `-Encoding UTF8`。写完检查首字节不是 `EF BB BF`。

```json
{
  "name": "PluginName",
  "author": "Author",
  "namespace": "YourPluginName",
  "message_mode": "olivos_string",
  "info": "Brief description",
  "version": "1.0.0",
  "svn": 1,
  "compatible_svn": 190,
  "priority": 30000,
  "support": [
    {"sdk": "onebot", "platform": "qq", "model": "all"},
    {"sdk": "all", "platform": "all", "model": "all"}
  ],
  "menu_config": [
    {"title": "Menu Title", "event": "YourPluginName_Menu_001"}
  ]
}
```

可调字段（按需求改，改完在交付说明里写清为什么）：

| 字段 | 什么时候要动 |
| --- | --- |
| `name` / `info` / `version` / `svn` | 换插件名、描述、版本迭代 |
| `author` | 用户自己的署名 |
| `namespace` | 只在新插件首次改名时；必须与目录名逐字符一致 |
| `priority` | 需要排在 OlivaDiceCore（`20000`）之前或之后时 |
| `message_mode` | 需要 CQ 码（`old_string`）或消息段（`olivos_para`）时 |
| `compatible_svn` | 目标宿主版本明确要求时 |
| `support` | 只支持特定平台 / 协议时 |
| `menu_config` / `webui_config` | 加或删配置入口；**不做界面就要一起删掉** |

## 消息模式

- `old_string`：CQ 码 `[CQ:type,key=value]`，CoolQ / OneBot v11 兼容
- `olivos_string`：OP 码 `[OP:type,key=value]`，OlivOS 跨平台推荐
- `olivos_para`：消息段结构 `OlivOS.messageAPI.Message_templet`，复杂图文

## 无事件上下文时主动发消息

```python
import OlivOS


def send_message_force(botHash, send_type, target_id, message, Proc, pluginName):
    if Proc is not None and botHash in Proc.Proc_data['bot_info_dict']:
        plugin_event = OlivOS.API.Event(
            OlivOS.contentAPI.fake_sdk_event(
                bot_info=Proc.Proc_data['bot_info_dict'][botHash],
                fakename=pluginName
            ),
            Proc.log
        )
        plugin_event.send(send_type, target_id, message)
```

## 优先级

OlivOS 数值越小越先执行。OlivaDiceCore 默认 `20000`；无冲突的规则插件用 `20020`，
让 Core 先处理。想覆盖 Core 的同类命令就把优先级放到 Core 之前。

# OPK 资源生命周期

只在交付 `.opk`、或插件要读自带静态资源（HTML/JSON/图片/字体）时读这一页。

- OPK 插件从 `plugin/tmp/<namespace>/` 导入。宿主会在 `init` 之后、`init_after` 之前清掉这个解包目录，所以**不要假设 `__file__` 旁边的路径在运行期仍然可读**。
- 需要 Python 读取的静态资源（HTML 模板、JSON、Markdown、图片、清单元数据），要在模块导入或 `init` 阶段就把内容读进内存，或者走宿主支持的资源释放机制。只保留路径不算数。
- 运行期才用到的 Python 子模块，也要在清理前先 import；等到某条命令或某个菜单点击时才第一次 import，会失败。
- `data/` 下的文件由宿主在 `init` 与 `init_after` 之间复制到 `plugin/data/<namespace>/data`，之后从那个位置读。注册过的 WebUI 资源由宿主缓存并直接提供，不需要读进 Python 内存。
- 可写的用户配置与业务数据一律放在解包目录之外。
- 依赖自带资源的插件，必须在解包目录已被清掉的状态下验证第一次命令、菜单动作或渲染；只在源码目录里跑通，不证明 OPK 兼容。

细节见 `references/official-docs/markdown/template.md` 与 `webui.md`。

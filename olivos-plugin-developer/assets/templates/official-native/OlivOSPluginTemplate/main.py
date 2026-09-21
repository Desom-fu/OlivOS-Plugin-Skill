import os
import OlivOS
import OlivOSPluginTemplate  # noqa: F401

gProc = None

gPluginName = 'OlivOS插件默认模板'


class Event(object):
    def init(plugin_event, Proc):
        # 初始化流程
        pass

    def init_after(plugin_event, Proc):
        # 初始化后处理流程
        # 区别是前面的初始化流程不基于优先级
        # 而本流程基于优先级
        global gProc
        gProc = Proc
        ensure_webui_assets(Proc)

    def private_message(plugin_event, Proc):
        # 私聊消息事件入口
        unity_reply(plugin_event, Proc)

    def group_message(plugin_event, Proc):
        # 群消息事件入口
        unity_reply(plugin_event, Proc)

    def poke(plugin_event, Proc):
        # 戳一戳事件入口
        poke_reply(plugin_event, Proc)

    def save(plugin_event, Proc):
        # 插件卸载时执行的保存流程
        pass

    def menu(plugin_event, Proc):
        # 插件菜单事件监听
        if plugin_event.data.namespace == 'OlivOSPluginTemplate':
            if isinstance(getattr(plugin_event.data, 'webui', None), dict):
                webui_reply(plugin_event)
                return
            if plugin_event.data.event == 'OlivOSPluginTemplate_Menu_001':
                pass
            elif plugin_event.data.event == 'OlivOSPluginTemplate_Menu_002':
                pass


def webui_reply(plugin_event):
    # 网页请求也通过 menu 分发，使用原事件回包以保留会话隔离。
    request_id = plugin_event.data.webui.get('request_id')
    if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
        return

    payload = getattr(plugin_event.data, 'payload', None)
    if plugin_event.data.event != 'OlivOSPluginTemplate_WebUI_Echo':
        response = {'ok': False, 'error': '未知的 WebUI 事件'}
    elif not isinstance(payload, dict) or not isinstance(payload.get('text'), str):
        response = {'ok': False, 'error': '消息必须为文本'}
    elif not payload['text'].strip() or len(payload['text']) > 200:
        response = {'ok': False, 'error': '请输入 1 至 200 字的消息'}
    else:
        response = {'ok': True, 'text': payload['text'], 'plugin': gPluginName}

    plugin_event.send('webui', request_id, response)


def unity_reply(plugin_event, Proc):
    # 被动回复消息示例
    if (
        plugin_event.data.message == '/bot'
        or plugin_event.data.message == '.bot'
        or plugin_event.data.message in [
            # app.json 中 compatible_svn < 190 的格式
            f"[OP:at,id={str(plugin_event.base_info['self_id'])}] .bot",
            # app.json 中 compatible_svn >= 190 的格式
            f"[OP:at,id={str(plugin_event.base_info['self_id'])}],name={plugin_event.data.sender['name']} .bot"
        ]
    ):
        plugin_event.reply('OlivOSPluginTemplate')
    # 主动发送消息示例
    elif plugin_event.data.message == '你好':
        # 新增 QQGuildV2 路由
        flag_from_qq_Guild = getattr(plugin_event.data, 'extend', {}).get('flag_from_qq', False)
        if plugin_event.plugin_info['func_type'] == 'group_message':
            send_message_force(
                plugin_event.bot_info.hash,
                'group',
                plugin_event.data.group_id,
                '我好',
                flag_from_qq_Guild
            )
        elif plugin_event.plugin_info['func_type'] == 'private_message':
            send_message_force(
                plugin_event.bot_info.hash,
                'private',
                plugin_event.data.user_id,
                '我不好',
                flag_from_qq_Guild
            )


def poke_reply(plugin_event, Proc):
    # 戳一戳回复消息示例
    if plugin_event.data.target_id == plugin_event.base_info['self_id']:
        plugin_event.reply('OlivOSPluginTemplate')
    elif plugin_event.data.target_id == plugin_event.data.user_id:
        plugin_event.reply('OlivOSPluginTemplate')
    elif plugin_event.data.group_id == -1:
        plugin_event.reply('OlivOSPluginTemplate')


# 主动发送消息示例实现
def send_message_force(botHash, send_type, target_id, message, flag_from_qq_Guild=False):
    Proc = gProc
    if (
        Proc is not None
        and botHash in Proc.Proc_data['bot_info_dict']
    ):
        pluginName = gPluginName
        plugin_event = OlivOS.API.Event(
            OlivOS.contentAPI.fake_sdk_event(
                bot_info=Proc.Proc_data['bot_info_dict'][botHash],
                fakename=pluginName
            ),
            Proc.log
        )
        if flag_from_qq_Guild:
            extend = getattr(plugin_event.data, 'extend', {}) or {}
            extend.update(
                flag_from_qq=True, flag_from_direct=send_type == 'private', reply_msg_id=None
            )
            plugin_event.data.extend = extend
        plugin_event.send(send_type, target_id, message)


# WebUI 静态资源的内存快照：OPK 插件由宿主解包到 plugin/tmp 下，该目录随时可能被宿主
# 清理；只有模块导入这一刻能保证文件还在，所以在这里把 webui/ 整体读进内存。
_webui_assets = {}


def load_webui_assets() -> None:
    """模块导入时调用：把 webui/ 下的静态资源读进内存。"""
    global _webui_assets
    if _webui_assets:
        return
    root = os.path.join(_webui_root(Proc), 'webui')
    if not os.path.isdir(root):
        return
    for dir_path, _, file_names in os.walk(root):
        for file_name in file_names:
            full_path = os.path.join(dir_path, file_name)
            key = os.path.relpath(full_path, root).replace(os.sep, '/')
            try:
                with open(full_path, 'rb') as handle:
                    _webui_assets[key] = handle.read()
            except OSError:
                continue


def _webui_root(Proc=None):
    """优先使用宿主注册的 webui_root，它与 /plugin/<namespace>/ 路由同源。

    .opk 插件的解包目录可能被宿主清理或改名，此时只有宿主记录的路径是权威的；
    取不到时才退回本模块所在目录（文件夹模式）。
    """
    fallback = os.path.dirname(os.path.abspath(__file__))
    if Proc is None:
        return fallback
    models = getattr(Proc, 'plugin_models_dict', None)
    if not isinstance(models, dict):
        return fallback
    info = models.get(__name__.split('.')[0])
    root = info.get('webui_root') if isinstance(info, dict) else None
    if isinstance(root, str) and root and os.path.isdir(root):
        return os.path.abspath(root)
    return fallback


def ensure_webui_assets(Proc=None) -> None:
    """WebUI 资源兜底：解包目录被宿主清理后，把缺失文件从内存快照写回。

    宿主已为 /plugin/<namespace>/ 注册好 webui_root，这里只补文件、不改路径。
    不要用文件锁阻止宿主清理 —— 那会让宿主的目录清理中途失败、留下残缺目录，
    反而导致页面 404。
    """
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webui')
    restored = 0
    try:
        for key, content in list(_webui_assets.items()):
            target = os.path.join(root, *key.split('/'))
            if os.path.isfile(target):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as handle:
                handle.write(content)
            restored += 1
    except OSError as error:
        if Proc is not None:
            Proc.log(4, 'WebUI 资源兜底失败: %s' % error)
        return
    if restored and Proc is not None:
        Proc.log(2, 'WebUI 资源已从内存快照恢复 %d 个文件' % restored)


load_webui_assets()

# nonebot-plugin-info

NoneBot2「功能」菜单插件：扫描**全部已加载插件**的 `__plugin_meta__.extra`，按分类出菜单图
（可选 htmlkit），渲染不可用时自动降级为纯文本。

- 每个插件只需在自己的 `__plugin_meta__.extra` 里补几行元数据，菜单就自动收录它；
- 没补元数据的插件（`metadata is None`）**直接跳过**，`type="library"` 的工具库不展示；
- 渲染永远只是锦上添花：**任何渲染失败都只回退纯文本，绝不表现成「命令没反应」**。

## 命令

| 命令          | 作用                                         |
| ------------- | -------------------------------------------- |
| `功能`        | 出分类菜单（图；渲染不可用时发文本菜单）     |
| `功能 <名字>` | 看某个插件的详情（名字支持模糊/子串匹配）    |
| `功能 -d`     | 详细菜单（每个插件带说明与全部命令，纯文本） |

- **只有「功能」这一个命令词，没有任何别名**。别名的坑：`菜单` 会与 lingchu-bot 等插件
  已注册的同名命令撞车，`help/帮助` 同理。要加词就在插件配置里定，别在本插件里硬编码。
- **不加 `to_me()`**：qbot 这类生态里命令都是直接发（`COMMAND_START=["", "/"]`），
  要求 @bot 会让人以为「命令没反应」。
- `<名字>` 匹配顺序：精确 → 忽略大小写 → 子串。查不到会明确回「没有找到「xx」这个功能」；
  详细模式用 `功能 -d`（`--detail` 同义），没有独立的第二个命令入口。

## 安装

```bash
uv add nonebot-plugin-info            # 只装插件本体
uv add "nonebot-plugin-info[htmlkit]" # 需要出图时再装渲染依赖（可选）
```

`nonebot-plugin-htmlkit` 是 **C++ 扩展**（litehtml），装之前先确认目标机器有预编译 wheel
（Linux 需要 `manylinux_2_34` 及以上 + fontconfig + 中文字体），否则中文会渲染成方块。
**不装也完全可用**：菜单/详情自动走纯文本。

## 插件作者怎么补元数据

```python
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="抽奖",
    description="群内抽奖小游戏",
    usage="抽奖 / 抽奖 -h",
    type="application",
    extra={
        # 分类名；缺省「功能」
        "menu_type": "群内小游戏",
        # 命令表：字符串 / {"command": ...} / {"command": ..., "desc": ...} 三种写法都吃
        "commands": [
            {"command": "抽奖", "desc": "开始抽奖"},
            {"command": "抽奖列表", "desc": "查看已开奖记录"},
        ],
        "introduction": "一句话介绍",  # 可选；缺省用 metadata.description
        "order": 10,                  # 可选；分类内排序，数字小的在前，缺省 100
        "is_show": True,              # 可选；False = 不进菜单（详情仍可按名字查到）
    },
)
```

字段与 zhenxun 的 `PluginExtraData` 对齐（`menu_type` / `commands` / `introduction` /
`order` / `is_show`），所以从 zhenxun 搬过来的元数据可以直接复用。写错的元数据（命令表里
塞了数字、`order` 写成字符串）**只跳过那一项**，不会让整个菜单挂掉。

分类顺序：按每组内最小 `order` 升序；组内按 `(order, name)` 升序。

## 本插件自己的元数据

本插件也按同一套规范写自己的 `extra`：`is_show=False`（照 zhenxun，帮助插件自己不进菜单，
否则菜单里会出现「功能」自己），`commands` 列出上面三条用法，`menu_type` 不给 → 落在「功能」。

## 部署（宿主以 git 子模块引入）

插件一律**以 git 子模块**挂载，不拷贝源码、不用 `pip install -e .`：

```bash
cd <宿主仓库>
git submodule add https://github.com/xinvxueyuan/nonebot-plugin-info.git vendor/nonebot-plugin-info
# 宿主的 [tool.nonebot].plugin_dirs 加一行：
#   "vendor/nonebot-plugin-info/src/plugins"
systemctl restart <宿主服务>
```

验收：按 MainPID 过滤日志确认 `Succeeded to load plugin`，并核对子模块 SHA 与期望一致。

## 开发

```bash
export PYTEST_ADDOPTS="--basetemp=$TMPDIR/info_t"   # 本机 Windows 需要（默认临时目录 ACL 坑）
ENV='env -u UV_PYTHON -u UV_PROJECT_ENVIRONMENT -u SSL_CERT_FILE -u VIRTUAL_ENV -u PYTHONPATH'
$ENV uv sync
$ENV uv run ruff check src/ tests/
$ENV uv run ruff format --check src/ tests/
$ENV uv run pyright
$ENV uv run pytest tests/ -q
$ENV uv run python scripts/mutation_check.py   # 变异检验：改坏关键行为必须让测试变红
```

结构与职责：

| 文件          | 职责                                                      |
| ------------- | --------------------------------------------------------- |
| `collect.py`  | `collect_from()` / `classify()` / `find_plugin()`（**纯函数**，不依赖 nonebot 运行时） |
| `render.py`   | 菜单/详情 HTML 与文本降级、`render_html()`（htmlkit 惰性导入，失败返回 `None`） |
| `handle.py`   | 命令「功能」的注册与三条分支                               |
| `__init__.py` | `__plugin_meta__` + 导入 handle 完成注册                   |

## 已知限制

- 菜单数据是**加载时快照**：改了插件 `__plugin_meta__` 要重启宿主才生效（NoneBot 的正常语义）。
- `功能` 是裸词，群里聊到「功能」二字也会触发菜单图（qbot 生态都是裸词触发，代价一致）。
  真要收紧就得加 `to_me()`，但那会让命令「看起来没反应」——本插件按用户口径选择不加。
- 出图依赖宿主装了 htmlkit + 中文字体；没装就是纯文本，功能不受影响。

## 更新日志

见 [CHANGELOG.md](CHANGELOG.md)。

## License

MIT

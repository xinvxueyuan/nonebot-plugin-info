# nonebot-plugin-info

NoneBot2 功能菜单插件（qbot 宿主以 git 子模块引入）：扫描全部已加载插件的 `__plugin_meta__.extra`，按分类出菜单图与插件详情（htmlkit 出图，失败自动回退纯文本）。

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](pyproject.toml)

> **qbot 插件** · 宿主仓库：[xinvxueyuan/qbot](https://github.com/xinvxueyuan/qbot)

> - 只实现「功能」一个命令词、**不带任何别名**（`菜单` 会与 lingchu-bot 等插件已注册的同名命令撞车，`help`/`帮助` 同理）；
> - **不加 `to_me()`**：qbot 生态命令都是直接发（`COMMAND_START=["", "/"]`），要求 @bot 会让人以为「命令没反应」；
> - 渲染永远只是锦上添花：**任何渲染失败都只回退纯文本**，绝不表现成「命令没反应」。

## 功能特性

- 扫描**全部已加载插件**的 `__plugin_meta__.extra`，按分类出菜单图（可选 htmlkit），渲染不可用时自动降级为纯文本。
- 每个插件只需在自己的 `__plugin_meta__.extra` 里补几行元数据，菜单就自动收录它。
- 没补元数据的插件（`metadata is None`）**直接跳过**；`type="library"` 的工具库不展示。
- 按名字查详情：匹配顺序 精确 → 忽略大小写 → 子串；`is_show=False` 的隐藏插件也查得到（用户点名就给）。
- 分类顺序：组间按组内最小 `order` 升序，组内按 `(order, name)` 升序；`menu_type` 缺省「功能」，`order` 缺省 `100`。
- 宿主侧菜单信息覆盖（`INFO_EXTRA_OVERRIDES`）：不改第三方插件一行，也能补分类 / 排序 / 命令说明（见「配置」）。

### 已知限制

- 菜单数据是**加载时快照**：改了插件 `__plugin_meta__` 要重启宿主才生效（NoneBot 的正常语义）。
- `功能` 是裸词，群里聊到「功能」二字也会触发菜单图（qbot 生态都是裸词触发，代价一致）。真要收紧就得加 `to_me()`，但那会让命令「看起来没反应」——本插件按用户口径选择不加。
- 出图依赖宿主装了 htmlkit + 中文字体；没装就是纯文本，功能不受影响。

## 安装

### 依赖

- 运行依赖：`nonebot2 >= 2.5.0`、`nonebot-adapter-onebot >= 2.4.6`（`requires-python >= 3.10`）。
- 可选依赖（`htmlkit` extra，出图用）：`nonebot-plugin-htmlkit == 0.1.0rc5`。
- 开发依赖：`dev`（`pytest`、`pytest-asyncio`）、`lint`（`ruff`、`pyright`）。

### 接入宿主

- 安装（宿主以 git 子模块引入）：

```bash
git submodule add -b main https://github.com/xinvxueyuan/nonebot-plugin-info.git vendor/nonebot-plugin-info
git -C vendor/nonebot-plugin-info checkout <钉定 SHA>
```

- 宿主 `[tool.nonebot] plugin_dirs` 加一行 `vendor/nonebot-plugin-info/src/plugins`（仓库实际布局 `src/plugins/nonebot_plugin_info`）。

插件一律**以 git 子模块**挂载，不拷贝源码、不用 `pip install -e .`；更新子模块 SHA 后 `systemctl restart <宿主服务>`。验收：按 MainPID 过滤日志确认 `Succeeded to load plugin`，并核对子模块 SHA 与期望一致。

`nonebot-plugin-htmlkit` 是 **C++ 扩展**（litehtml），装之前先确认目标机器有预编译 wheel（Linux 需要 `manylinux_2_34` 及以上 + fontconfig + 中文字体），否则中文会渲染成方块。**不装也完全可用**：菜单 / 详情自动走纯文本。

## 配置

| 键 | 默认 | 说明 |
|---|---|---|
| `INFO_EXTRA_OVERRIDES` | `{}`（无覆盖） | 宿主侧菜单信息覆盖：键 = 插件**模块短名**（如 `nonebot_plugin_parser_lite`）或 `metadata.name`；值只认 `menu_type` / `order` / `commands` / `introduction` / `is_show` 五个键，其余忽略。 |

**不改第三方插件一行**，也能给它补菜单信息 —— 写在本插件自己的配置里（`.env` 里是 JSON 字符串）：

```bash
INFO_EXTRA_OVERRIDES={"nonebot_plugin_parser_lite": {"menu_type": "功能", "order": 30, "commands": [{"command": "发送链接 / BV号", "desc": "自动解析并回图（含小程序卡片）"}]}}
```

- 键 = 插件**模块短名**（`nonebot_plugin_parser_lite`）或 `metadata.name`（「链接分享解析 Lite 版」）；模块名优先（显示名可能随上游变）。
- 值只认五个键：`menu_type` / `order` / `commands` / `introduction` / `is_show`——其余键忽略（覆盖不该改掉 `is_library` 之类的语义）。
- 典型用途：第三方插件（源码不归我们）没有菜单元数据 → 补一条触发说明，菜单里就不会出现空挡；也可用它临时改分类 / 排序 / 隐藏。

## 使用 / 命令

| 命令 | 别名 | 说明 |
|---|---|---|
| `功能` | 无 | 出分类菜单（图；渲染不可用时发文本菜单） |
| `功能 <名字>` | 无 | 看某个插件的详情（图 / 文本；名字支持模糊 / 子串匹配） |
| `功能 -d` | `功能 --detail` | 详细菜单（每个插件带说明与全部命令，纯文本） |

- **只有「功能」这一个命令词，没有任何别名**；要加词就在插件配置里定，别在本插件里硬编码。
- 查不到会明确回「没有找到「xx」这个功能」；详细模式只由 `功能 -d`（`--detail` 同义）进入，没有独立的第二个命令入口。
- 实现上只有 `handle.py` 一处 `on_command("功能", block=True)` + `CommandArg()`：`功能`、`功能 <名字>`、`功能 -d` 是同一个入口的三条分支。

## 开发与测试

```bash
uv run python -m pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run python scripts/mutation_check.py   # 变异检验：改坏关键行为必须让测试变红
```

- 测试目录 `tests/`：`test_collect.py` / `test_handle.py` / `test_render.py` / `test_overrides.py` / `test_smoke.py`（另有 `conftest.py`）；`pyproject.toml` 里 `asyncio_mode = "auto"`、`testpaths = ["tests"]`。
- 变异检验共 6 个变异体（隐藏插件泄漏 / 插件名不转义 / 渲染失败抛异常 / 分类不排序 / 模糊查询失效 / 宿主覆盖失效），每个都必须被测试捕获。
- 本机 Windows 注意：跑 pytest 前 `export PYTEST_ADDOPTS="--basetemp=$TMPDIR/info_t"`（默认临时目录 ACL 坑）；uv 命令建议套 `env -u UV_PYTHON -u UV_PROJECT_ENVIRONMENT -u SSL_CERT_FILE -u VIRTUAL_ENV -u PYTHONPATH`。

### 结构与职责

| 文件 | 职责 |
|---|---|
| `collect.py` | `collect_from()` / `classify()` / `find_plugin()`（**纯函数**，不依赖 nonebot 运行时） |
| `render.py` | 菜单 / 详情 HTML 与文本降级、`render_html()`（htmlkit 惰性导入，失败返回 `None`） |
| `handle.py` | 命令「功能」的注册与三条分支 |
| `__init__.py` | `__plugin_meta__` + 导入 handle 完成注册 |

### 插件作者怎么补元数据

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
        "order": 10,  # 可选；分类内排序，数字小的在前，缺省 100
        "is_show": True,  # 可选；False = 不进菜单（详情仍可按名字查到）
    },
)
```

字段与 zhenxun 的 `PluginExtraData` 对齐（`menu_type` / `commands` / `introduction` / `order` / `is_show`），所以从 zhenxun 搬过来的元数据可以直接复用。写错的元数据（命令表里塞了数字、`order` 写成字符串）**只跳过那一项**，不会让整个菜单挂掉。分类顺序：按每组内最小 `order` 升序；组内按 `(order, name)` 升序。

### 本插件自己的元数据

本插件也按同一套规范写自己的 `extra`：`is_show=False`（照 zhenxun，帮助插件自己不进菜单，否则菜单里会出现「功能」自己），`commands` 列出上面三条用法，`menu_type` 不给 → 落在「功能」。

### 更新日志

见 [CHANGELOG.md](CHANGELOG.md)（当前 `0.1.1`，遵循 Keep a Changelog + 语义化版本）。

## 许可证与相关仓库

MIT —— `pyproject.toml` 的 `license` 字段声明 MIT；**仓库未附 `LICENSE` 文件**，以 `pyproject.toml` 为准。

- 宿主仓库：[xinvxueyuan/qbot](https://github.com/xinvxueyuan/qbot)（以 git 子模块挂在 `vendor/nonebot-plugin-info`，`plugin_dirs` 中已启用）
- [xinvxueyuan/nonebot-plugin-waifu](https://github.com/xinvxueyuan/nonebot-plugin-waifu) 与
  [xinvxueyuan/nonebot-plugin-lottery](https://github.com/xinvxueyuan/nonebot-plugin-lottery)：
  两者都在 `__plugin_meta__.extra` 里给了 `menu_type`，是本插件菜单的实际内容来源（本插件只读元数据，不改它们一行）
- `nonebot-plugin-htmlkit`：可选出图依赖（`htmlkit` extra，PyPI 分发），不装则菜单 / 详情回退纯文本

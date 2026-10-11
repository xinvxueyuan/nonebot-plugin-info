"""收集已加载插件的帮助元数据（纯函数 collect_from，便于无 nonebot 运行时测试）。"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

logger = logging.getLogger("nonebot_plugin_info")

#: 缺省分类名（对齐 zhenxun：menu_type 为空 → 「功能」）
DEFAULT_MENU: Final[str] = "功能"
#: 缺省排序位（数字小的在前；未声明排最后）
DEFAULT_ORDER: Final[int] = 100

#: 宿主侧覆盖**只允许**碰这些键（菜单语义）—— 其余键一律忽略，
#: 覆盖不该顺手改掉别的语义（`is_library` 由 `metadata.type` 决定）。
_OVERRIDABLE: Final[frozenset[str]] = frozenset({
    "menu_type",
    "order",
    "commands",
    "introduction",
    "is_show",
})


def _module_short(module: str) -> str:
    """`vendor.…plugins.nonebot_plugin_x` → `nonebot_plugin_x`（配置里写短名）。"""
    return module.rsplit(".", 1)[-1]


def _pick_override(
    overrides: Mapping[str, Mapping[str, Any]] | None,
    *,
    module: str,
    name: str,
) -> dict[str, Any]:
    """按**模块短名 → metadata.name** 的顺序找覆盖条目，只留下菜单键。

    两边都匹配不到返回 `{}`（等于没配）。同名条目同时存在时**模块名优先**
    —— 显示名可能随上游改，模块名不会。
    """
    if not overrides:
        return {}
    raw = overrides.get(_module_short(module)) or overrides.get(name)
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if k in _OVERRIDABLE}


@dataclass(frozen=True)
class CommandItem:
    command: str
    desc: str = ""


@dataclass(frozen=True)
class PluginItem:
    name: str
    module: str
    menu_type: str
    description: str
    usage: str
    commands: tuple[CommandItem, ...] = ()
    order: int = DEFAULT_ORDER
    is_show: bool = True
    is_library: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def parse_commands(raw: Any) -> tuple[CommandItem, ...]:
    """吃三种写法：'抽奖' / {'command': '抽奖'} / {'command': '抽奖', 'desc': '...'}。

    非法项**跳过不抛**（插件作者写错元数据不能让整个菜单挂掉）。
    """
    if not isinstance(raw, list | tuple):
        return ()
    out: list[CommandItem] = []
    for entry in raw:
        if isinstance(entry, str) and entry.strip():
            out.append(CommandItem(command=entry.strip()))
        elif isinstance(entry, dict):
            cmd = entry.get("command")
            if isinstance(cmd, str) and cmd.strip():
                desc = entry.get("desc")
                out.append(
                    CommandItem(
                        command=cmd.strip(),
                        desc=desc.strip() if isinstance(desc, str) else "",
                    )
                )
    return tuple(out)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """取字段：dict 用 get，其它对象用 getattr。

    真实 metadata 是 dataclass，测试里传 SimpleNamespace / dict 也行。
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def collect_from(
    plugins: Iterable[Any],
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[PluginItem]:
    """把 `Plugin` 列表规整成 PluginItem 列表。

    - `plugin.metadata is None` → 跳过（无元数据的插件不展示，如未补 meta 的第三方）
    - `metadata.type == "library"` → is_library=True（is_show 强制 False）
    - extra 里的 menu_type/introduction/order/is_show 缺省值与 zhenxun 对齐
    - `overrides`：**宿主侧菜单信息覆盖**（`Config.info_extra_overrides`）——
      给不改源码的第三方插件补菜单字段；键 = 模块短名或 metadata.name
    """
    items: list[PluginItem] = []
    for p in plugins:
        meta = getattr(p, "metadata", None)
        if meta is None:
            continue
        module = str(getattr(p, "module_name", ""))
        extra = _get(meta, "extra", None)
        if not isinstance(extra, dict):
            extra = {}
        extra = {
            **extra,
            **_pick_override(
                overrides, module=module, name=str(_get(meta, "name", "") or module)
            ),
        }
        is_library = _get(meta, "type", None) == "library"
        menu_type = extra.get("menu_type")
        if not isinstance(menu_type, str) or not menu_type.strip():
            menu_type = DEFAULT_MENU
        introduction = extra.get("introduction")
        if not isinstance(introduction, str) or not introduction.strip():
            introduction = str(_get(meta, "description", "") or "")
        order = extra.get("order")
        if not isinstance(order, int):
            order = DEFAULT_ORDER
        is_show = extra.get("is_show")
        if not isinstance(is_show, bool):
            is_show = True
        if is_library:
            is_show = False
        items.append(
            PluginItem(
                name=str(_get(meta, "name", "") or module),
                module=module,
                menu_type=menu_type.strip(),
                description=str(introduction),
                usage=str(_get(meta, "usage", "") or ""),
                commands=parse_commands(extra.get("commands")),
                order=order,
                is_show=is_show,
                is_library=is_library,
                extra=extra,
            )
        )
    return items


def collect_plugins(
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[PluginItem]:
    """从 nonebot 取全部已加载插件。

    薄封装：无 nonebot 运行时的测试请直接用 `collect_from`。
    `overrides` 缺省时读插件配置的 `INFO_EXTRA_OVERRIDES`（宿主侧菜单覆盖）。
    """
    from nonebot.plugin import get_loaded_plugins

    if overrides is None:
        from .config import plugin_config

        overrides = plugin_config.info_extra_overrides
    return collect_from(get_loaded_plugins(), overrides=overrides)


def classify(items: list[PluginItem]) -> dict[str, list[PluginItem]]:
    """按 menu_type 分组 → 组内按 (order, name) 排序；返回只含 is_show=True 的项。

    分组顺序：按组内最小 order 排（稳定、可测）。
    """
    groups: dict[str, list[PluginItem]] = {}
    for it in items:
        if not it.is_show:
            continue
        groups.setdefault(it.menu_type, []).append(it)
    for v in groups.values():
        v.sort(key=lambda x: (x.order, x.name))
    return dict(sorted(groups.items(), key=lambda kv: min(i.order for i in kv[1])))


def find_plugin(items: list[PluginItem], query: str) -> PluginItem | None:
    """按名字精确 → 不区分大小写 → 子串 的优先级匹配。

    只查 is_show 的？**不**：详情能查到隐藏插件——用户点名查就给他。
    """
    q = query.strip()
    if not q:
        return None
    for it in items:
        if it.name == q:
            return it
    ql = q.lower()
    for it in items:
        if it.name.lower() == ql:
            return it
    for it in items:
        if ql in it.name.lower():
            return it
    return None

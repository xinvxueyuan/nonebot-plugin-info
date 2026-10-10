"""收集已加载插件的帮助元数据（纯函数 collect_from，便于无 nonebot 运行时测试）。"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger("nonebot_plugin_info")

#: 缺省分类名（对齐 zhenxun：menu_type 为空 → 「功能」）
DEFAULT_MENU: Final[str] = "功能"
#: 缺省排序位（数字小的在前；未声明排最后）
DEFAULT_ORDER: Final[int] = 100


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


def collect_from(plugins: Iterable[Any]) -> list[PluginItem]:
    """把 `Plugin` 列表规整成 PluginItem 列表。

    - `plugin.metadata is None` → 跳过（无元数据的插件不展示，如未补 meta 的第三方）
    - `metadata.type == "library"` → is_library=True（is_show 强制 False）
    - extra 里的 menu_type/introduction/order/is_show 缺省值与 zhenxun 对齐
    """
    items: list[PluginItem] = []
    for p in plugins:
        meta = getattr(p, "metadata", None)
        if meta is None:
            continue
        extra = _get(meta, "extra", None)
        if not isinstance(extra, dict):
            extra = {}
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
                name=str(_get(meta, "name", "") or getattr(p, "module_name", "")),
                module=str(getattr(p, "module_name", "")),
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


def collect_plugins() -> list[PluginItem]:
    """从 nonebot 取全部已加载插件。

    薄封装：无 nonebot 运行时的测试请直接用 `collect_from`。
    """
    from nonebot.plugin import get_loaded_plugins

    return collect_from(get_loaded_plugins())


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

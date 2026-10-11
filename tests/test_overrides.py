"""宿主侧菜单信息覆盖（`INFO_EXTRA_OVERRIDES`）。

**为什么要有它**（用户 2026-10-11 拍板）：第三方插件（如「链接分享解析 Lite 版」）
没有 `menu_type` / `commands`，而它**不能**被改源码 —— 于是由信息插件在自己的配置里
给它补菜单元数据，菜单里就不会再出现空挡。

覆盖键先按**模块短名**匹配（`vendor.…plugins.nonebot_plugin_x` → `nonebot_plugin_x`），
再按 `metadata.name` 匹配；只允许覆盖菜单相关键（menu_type / order / commands /
introduction / is_show），其余键忽略 —— 覆盖不该偷偷改别的语义（如 `is_library`）。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from nonebot.plugin import PluginMetadata

from nonebot_plugin_info.collect import collect_from
from nonebot_plugin_info.config import Config

_PARSER_MODULE = "vendor.nonebot-plugin-parser-lite.src.nonebot_plugin_parser_lite"


def _plugin(
    *,
    module: str,
    name: str | None = None,
    extra: dict[str, Any] | None = None,
    ptype: str | None = "application",
) -> SimpleNamespace:
    return SimpleNamespace(
        module_name=module,
        metadata=PluginMetadata(
            name=name or module,
            description="一句话介绍",
            usage="用法",
            type=ptype,
            extra=extra if extra is not None else {},
        ),
    )


def _parser_plugin(**kw: Any) -> SimpleNamespace:
    """第三方插件的样子：有 metadata、extra 里只有作者/版本，没有菜单字段。"""
    return _plugin(
        module=_PARSER_MODULE,
        name="链接分享解析 Lite 版",
        extra={"author": "sokoko-org", "version": "1.3.8rc7"},
        **kw,
    )


_OVERRIDE = {
    "nonebot_plugin_parser_lite": {
        "menu_type": "功能",
        "order": 30,
        "commands": [{"command": "发送链接 / BV号", "desc": "自动解析并回图"}],
    }
}


def test_override_supplies_menu_fields_by_module_short_name():
    """按模块短名命中：菜单字段真的落到 PluginItem 上（不再是空挡）。"""
    (it,) = collect_from([_parser_plugin()], overrides=_OVERRIDE)
    assert it.menu_type == "功能"
    assert it.order == 30
    assert [c.command for c in it.commands] == ["发送链接 / BV号"]
    assert it.commands[0].desc == "自动解析并回图"


def test_override_supplies_menu_fields_by_display_name():
    """按 `metadata.name` 也要能命中（配置里写中文名更直观）。"""
    (it,) = collect_from(
        [_parser_plugin()],
        overrides={"链接分享解析 Lite 版": {"menu_type": "工具", "order": 7}},
    )
    assert it.menu_type == "工具"
    assert it.order == 7


def test_override_only_touches_menu_keys():
    """只认菜单键：`is_library` 之类的语义键不许被覆盖悄悄改掉，未知键也不进 extra。"""
    (it,) = collect_from(
        [_parser_plugin()],
        overrides={
            "nonebot_plugin_parser_lite": {
                "menu_type": "功能",
                "foo": 1,
                "is_library": True,
                "is_show": False,
            }
        },
    )
    assert it.menu_type == "功能"
    assert it.is_library is False
    assert it.is_show is False  # is_show 本身是允许覆盖的菜单键
    assert "foo" not in it.extra
    assert "is_library" not in it.extra


def test_override_untouched_for_other_plugins():
    """没命中覆盖的插件一个字段都不变（覆盖不是全局副作用）。"""
    other = _plugin(
        module="vendor.x.src.plugins.nonebot_plugin_other",
        name="别的插件",
        extra={"menu_type": "管理", "order": 5},
    )
    items = collect_from([_parser_plugin(), other], overrides=_OVERRIDE)
    got = {it.name: it for it in items}
    assert got["别的插件"].menu_type == "管理"
    assert got["别的插件"].order == 5
    assert got["别的插件"].commands == ()
    assert got["链接分享解析 Lite 版"].order == 30


def test_override_empty_or_missing_is_noop():
    """没配覆盖（默认）时行为与从前完全一致。"""
    items = collect_from([_parser_plugin()], overrides=None)
    assert items[0].menu_type == "功能"  # 缺省分类
    assert items[0].order == 100  # 缺省排序
    assert items[0].commands == ()


def test_config_default_overrides_is_empty():
    """配置默认值为空 dict（生产用 INFO_EXTRA_OVERRIDES 覆盖）。"""
    assert Config().info_extra_overrides == {}

"""冒烟：插件能被导入、元数据在位。"""

from __future__ import annotations


def test_plugin_imports_and_meta_name():
    import nonebot_plugin_info as p

    assert p.__plugin_meta__.name == "功能"


def test_plugin_meta_type_and_adapters():
    """类型是 application（library 会被 collect 判成隐藏）；只声明 onebot v11。"""
    import nonebot_plugin_info as p

    meta = p.__plugin_meta__
    assert meta.type == "application"
    assert meta.supported_adapters == {"nonebot.adapters.onebot.v11"}


def test_plugin_hides_itself_from_menu():
    """照 zhenxun：help 插件自己不进菜单（is_show=False），否则菜单里会有自己的条目。"""
    import nonebot_plugin_info as p

    assert p.__plugin_meta__.extra["is_show"] is False


def test_plugin_lists_its_own_usage_in_extra():
    """本插件自己的帮助信息按 extra 规范写（menu_type 不给 → 默认「功能」）。"""
    import nonebot_plugin_info as p

    extra = p.__plugin_meta__.extra
    assert "menu_type" not in extra
    commands = extra["commands"]
    assert [c["command"] for c in commands] == [
        "功能",
        "功能 <名字>",
        "功能 -d",
    ]
    assert all(c["desc"] for c in commands)

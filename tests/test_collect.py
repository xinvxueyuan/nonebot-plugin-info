"""collect 纯函数：元数据规整、分组排序、查找优先级。

**不需要 nonebot 运行时**：被测的是 `collect_from(plugins)`（吃任何长得像 Plugin 的
对象），`collect_plugins()` 只是 `get_loaded_plugins()` 的薄封装。替身用**真实的**
`Plugin` / `PluginMetadata`（生产就是这两个类），只在个别边界用例里用 SimpleNamespace。
"""

from __future__ import annotations

from types import ModuleType, SimpleNamespace

from nonebot.plugin.model import Plugin, PluginMetadata


def _plugin(
    metadata: PluginMetadata | None = None,
    *,
    name: str = "nonebot_plugin_demo",
    module_name: str = "",
) -> Plugin:
    return Plugin(
        name=name,
        module=ModuleType(name),
        module_name=module_name or name,
        manager=None,
        metadata=metadata,
    )


def _meta(**kw: object) -> PluginMetadata:
    base: dict[str, object] = {
        "name": "抽奖",
        "description": "群内抽奖小游戏",
        "usage": "抽奖",
    }
    base.update(kw)
    return PluginMetadata(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------- parse_commands


def test_parse_commands_three_shapes():
    """Commands 元素兼容三种写法：纯字符串 / dict / dict+desc。"""
    from nonebot_plugin_info.collect import parse_commands

    got = parse_commands([
        "抽奖",
        {"command": "再来一次"},
        {"command": "换一只", "desc": "重新抽"},
    ])
    assert [c.command for c in got] == ["抽奖", "再来一次", "换一只"]
    assert [c.desc for c in got] == ["", "", "重新抽"]


def test_parse_commands_skips_garbage():
    """插件作者写错元数据不能让整个菜单挂掉：非法项**跳过不抛**。"""
    from nonebot_plugin_info.collect import parse_commands

    got = parse_commands([
        123,
        None,
        "",
        "   ",
        {"desc": "没有 command"},
        {"command": None},
        {"command": "   "},
        [],
        {"command": "抽奖", "desc": "有效项"},
    ])
    assert [c.command for c in got] == ["抽奖"]
    assert got[0].desc == "有效项"


def test_parse_commands_non_sequence_returns_empty():
    from nonebot_plugin_info.collect import parse_commands

    assert parse_commands("抽奖") == ()
    assert parse_commands(None) == ()
    assert parse_commands({"command": "抽奖"}) == ()
    assert parse_commands(()) == ()


def test_parse_commands_strips_whitespace_and_coerces_desc():
    from nonebot_plugin_info.collect import parse_commands

    got = parse_commands(["  抽奖  ", {"command": " 换一只 ", "desc": 42}])
    assert [c.command for c in got] == ["抽奖", "换一只"]
    assert got[1].desc == ""  # desc 不是 str → 空串，不能把 42 塞进去


# ---------------------------------------------------------------- collect_from


def test_collect_skips_none_metadata():
    """没有 `__plugin_meta__` 的插件不展示（也不能让收集器抛）。"""
    from nonebot_plugin_info.collect import collect_from

    plugins = [_plugin(None), _plugin(_meta(), name="nonebot_plugin_lottery")]
    items = collect_from(plugins)
    assert [i.name for i in items] == ["抽奖"]


def test_collect_library_hidden():
    """type=library（工具库）强制 is_show=False，不进菜单。"""
    from nonebot_plugin_info.collect import collect_from

    (it,) = collect_from([_plugin(_meta(type="library"))])
    assert it.is_library is True
    assert it.is_show is False


def test_collect_defaults():
    """无 extra → 分类「功能」、order=100、is_show=True、描述取插件 description。"""
    from nonebot_plugin_info.collect import collect_from

    (it,) = collect_from([_plugin(_meta(), name="nonebot_plugin_lottery")])
    assert it.menu_type == "功能"
    assert it.order == 100
    assert it.is_show is True
    assert it.is_library is False
    assert it.description == "群内抽奖小游戏"
    assert it.usage == "抽奖"
    assert it.module == "nonebot_plugin_lottery"
    assert it.commands == ()


def test_collect_introduction_overrides_description():
    from nonebot_plugin_info.collect import collect_from

    (it,) = collect_from([_plugin(_meta(extra={"introduction": "一句话介绍"}))])
    assert it.description == "一句话介绍"


def test_collect_reads_extra_fields():
    from nonebot_plugin_info.collect import collect_from

    extra = {
        "menu_type": "群内小游戏",
        "order": 10,
        "is_show": False,
        "commands": ["抽奖"],
    }
    (it,) = collect_from([_plugin(_meta(extra=extra))])
    assert it.menu_type == "群内小游戏"
    assert it.order == 10
    assert it.is_show is False
    assert [c.command for c in it.commands] == ["抽奖"]
    assert it.extra == extra


def test_collect_blank_menu_type_falls_back_to_default():
    from nonebot_plugin_info.collect import collect_from

    for blank in ("", "   ", None, 123):
        (it,) = collect_from([_plugin(_meta(extra={"menu_type": blank}))])
        assert it.menu_type == "功能", blank


def test_collect_bad_scalar_types_fall_back():
    """Order 非 int、is_show 非 bool → 取缺省值（不能把 "no" 当 False）。"""
    from nonebot_plugin_info.collect import collect_from

    (it,) = collect_from([
        _plugin(_meta(extra={"order": "1", "is_show": "no", "introduction": 7}))
    ])
    assert it.order == 100
    assert it.is_show is True
    assert it.description == "群内抽奖小游戏"


def test_collect_non_dict_extra_is_ignored():
    from nonebot_plugin_info.collect import collect_from

    (it,) = collect_from([_plugin(_meta(extra=None))])
    assert it.menu_type == "功能"
    assert it.extra == {}


def test_collect_name_falls_back_to_module_name():
    """metadata.name 为空时用模块名兜底（不能让菜单里出现空条目）。"""
    from nonebot_plugin_info.collect import collect_from

    (it,) = collect_from([_plugin(_meta(name=""), name="nonebot_plugin_x")])
    assert it.name == "nonebot_plugin_x"
    assert it.module == "nonebot_plugin_x"


# ---------------------------------------------------------------- classify


def test_classify_groups_and_sorts():
    """按 menu_type 分组，组内 (order, name) 排序。"""
    from nonebot_plugin_info.collect import classify, collect_from

    def one(name: str, menu: str, order: int) -> Plugin:
        return _plugin(
            _meta(name=name, extra={"menu_type": menu, "order": order}), name=name
        )

    plugins = [
        one("b", "功能", 5),
        one("a", "功能", 5),
        one("z", "功能", 1),
        one("x", "群内小游戏", 3),
    ]
    groups = classify(collect_from(plugins))
    assert list(groups) == ["功能", "群内小游戏"]
    assert [i.name for i in groups["功能"]] == ["z", "a", "b"]
    assert [i.name for i in groups["群内小游戏"]] == ["x"]


def test_classify_excludes_hidden():
    """is_show=False（含 library）不进菜单。"""
    from nonebot_plugin_info.collect import classify, collect_from

    plugins = [
        _plugin(_meta(name="hidden", extra={"is_show": False}), name="hidden"),
        _plugin(_meta(name="lib", type="library"), name="lib"),
        _plugin(_meta(name="shown"), name="shown"),
    ]
    groups = classify(collect_from(plugins))
    assert [i.name for i in groups["功能"]] == ["shown"]


def test_classify_group_order_by_min_order():
    """组间顺序 = 组内最小 order（稳定、可测）。"""
    from nonebot_plugin_info.collect import classify, collect_from

    def one(name: str, menu: str, order: int) -> Plugin:
        return _plugin(
            _meta(name=name, extra={"menu_type": menu, "order": order}), name=name
        )

    plugins = [
        one("f1", "功能", 50),
        one("m1", "管理", 5),
        one("g1", "群内小游戏", 10),
        one("f0", "功能", 1),
    ]
    groups = classify(collect_from(plugins))
    assert list(groups) == ["功能", "管理", "群内小游戏"]


def test_classify_empty_input():
    from nonebot_plugin_info.collect import classify

    assert classify([]) == {}


# ---------------------------------------------------------------- find_plugin


def test_find_plugin_priority():
    """精确 > 不区分大小写 > 子串；查不到 / 空串 → None。"""
    from nonebot_plugin_info.collect import collect_from, find_plugin

    items = collect_from([
        _plugin(_meta(name="抽奖"), name="p1"),
        _plugin(_meta(name="Pixiv-小说"), name="p2"),
        _plugin(_meta(name="另一个抽奖机"), name="p3"),
    ])
    assert find_plugin(items, "抽奖").name == "抽奖"
    assert find_plugin(items, " pixiv-小说 ").name == "Pixiv-小说"
    assert find_plugin(items, "抽奖机").name == "另一个抽奖机"
    assert find_plugin(items, "不存在的功能") is None
    assert find_plugin(items, "   ") is None


def test_find_plugin_can_find_hidden():
    """详情要能查到隐藏插件（用户点名查就给他），别跟着菜单一起过滤掉。"""
    from nonebot_plugin_info.collect import collect_from, find_plugin

    items = collect_from([_plugin(_meta(extra={"is_show": False}), name="功能")])
    it = find_plugin(items, "抽奖")
    assert it is not None
    assert it.is_show is False


def test_plugin_item_is_frozen():
    """PluginItem/CommandItem 是 frozen dataclass：收集结果不该被下游就地改。"""
    import dataclasses

    from nonebot_plugin_info import collect

    (it,) = collect.collect_from([_plugin(_meta())])
    assert dataclasses.is_dataclass(it)
    try:
        it.name = "改坏了"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("PluginItem 必须 frozen —— 就地改收集结果会污染后续分组")


def test_collect_from_accepts_any_iterable():
    """吃的是 Iterable（set / 生成器都行）——`get_loaded_plugins()` 返回的就是 set。"""
    from nonebot_plugin_info.collect import collect_from

    rows = (_plugin(_meta()),)
    assert len(collect_from(set(rows))) == 1
    assert len(collect_from(iter(rows))) == 1


def test_collect_from_accepts_attribute_style_objects():
    """真 metadata 是 dataclass，也容忍 SimpleNamespace / dict 形态（同一取值器）。"""
    from nonebot_plugin_info.collect import collect_from

    fake = SimpleNamespace(
        module_name="nb.fake",
        metadata={"name": "假插件", "description": "d", "type": "application"},
    )
    (it,) = collect_from([fake])
    assert it.name == "假插件"
    assert it.description == "d"

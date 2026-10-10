"""命令「功能」：接线（单命令词、**无别名**）、菜单/详情/详细模式、降级路径。

⚠️ 口径（用户 2026-10-11 拍板）：**只实现「功能」一个命令词**，不要 help/帮助/菜单 别名
（「菜单」会与 lingchu-bot 已注册的「菜单」撞车），也没有独立的「详细帮助」入口。
所以本文件里有两条**反向守卫**：matcher 注册的命令词只有「功能」，且不再有别名候选词。
"""

from __future__ import annotations

import ast
import asyncio
import pathlib

import pytest

GROUP = 1094538078
ME = 10001
SRC = pathlib.Path(__file__).resolve().parents[1] / "src/plugins/nonebot_plugin_info"
HANDLE_SRC = SRC / "handle.py"


# ---------------------------------------------------------------- 替身与工具


class _FinishedError(Exception):
    """`Matcher.finish()` 的替身异常（真身抛 `FinishedException`，中断 handler）。"""


class _FakeMatcher:
    def __init__(self) -> None:
        self.sent: list[object] = []

    async def finish(self, message: object = None, **kwargs: object) -> None:
        self.sent.append(message)
        raise _FinishedError


def _items():
    from nonebot_plugin_info.collect import CommandItem, PluginItem

    def one(name, menu, order, desc, cmds):
        return PluginItem(
            name=name,
            module=f"m_{name}",
            menu_type=menu,
            description=desc,
            usage=f"{name} 用法",
            order=order,
            commands=tuple(CommandItem(c, d) for c, d in cmds),
        )

    return [
        one("抽奖", "群内小游戏", 10, "群内抽奖小游戏", [("抽奖", "开始抽奖")]),
        one("次元图", "功能", 20, "随机图片", [("次元图", "随机图片")]),
    ]


def _event(text: str):
    from nonebot.adapters.onebot.v11 import GroupMessageEvent
    from nonebot.adapters.onebot.v11.event import Sender

    return GroupMessageEvent(
        time=1,
        self_id=3128682634,
        post_type="message",
        sub_type="normal",
        user_id=ME,
        message_type="group",
        message=[{"type": "text", "data": {"text": text}}],
        raw_message=text,
        font=0,
        message_id=42,
        sender=Sender(user_id=ME, nickname="u", role="member"),
        group_id=GROUP,
    )


def _bot():
    import nonebot
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    return Bot(Adapter(nonebot.get_driver()), self_id="3128682634")


def _strip_command(text: str) -> str:
    """模拟真实 `CommandArg` 的注入内容：剥掉命令词（含 `/` 前缀）与随后的空白。

    ⚠️ 把**整条消息**当 args 传会把「功能」自己当成插件名去查（→「没有找到「功能」」）。
    """
    body = text.strip()
    for start in ("/", ""):
        if body.startswith(f"{start}功能"):
            body = body[len(start) + len("功能") :]
            break
    return body.strip()


def _call(monkeypatch, text, *, items=None, render_html=None):
    """直接调 handler（`text` 是**整条消息**）；返回 fake matcher 的已发送列表。"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_info import handle

    monkeypatch.setattr(
        handle, "collect_plugins", lambda: _items() if items is None else items
    )
    if render_html is not None:
        monkeypatch.setattr(handle, "render_html", render_html)
    matcher = _FakeMatcher()
    args = Message(_strip_command(text))
    with pytest.raises(_FinishedError) as exc:
        asyncio.run(handle._h_func(matcher, _event(text), args))
    assert isinstance(exc.value, _FinishedError)
    return matcher.sent


# ---------------------------------------------------------------- 反向守卫：命令词


def test_matcher_registers_exactly_one_command_word():
    """反向守卫：注册的命令词只有「功能」，**别名集合为空**。"""
    from nonebot.rule import CommandRule

    from nonebot_plugin_info import handle

    cmds = [
        c.call.cmds
        for c in handle.func_cmd.rule.checkers
        if isinstance(c.call, CommandRule)
    ]
    assert cmds == [(("功能",),)], f"命令词/别名不符：{cmds}"


def test_only_gongneng_triggers_and_no_alias_word_does():
    """行为级守卫：真 TrieRule + CommandRule 解析 —— 别名候选词一个都不许触发。"""
    from nonebot.rule import TrieRule

    from nonebot_plugin_info import handle

    def matches(text):
        event = _event(text)
        state: dict[str, object] = {}
        TrieRule.get_value(_bot(), event, state)
        return asyncio.run(handle.func_cmd.rule(_bot(), event, state))

    for hit in (
        "功能",
        "/功能",
        "功能 抽奖",
        "功能 -d",
        "功能 不存在的功能",
        # ⚠️ 真实 nonebot 语义：`on_command` 未设 force_whitespace 时，
        # 「功能」后紧接内容也算命令 + 参数（「功能菜单」→ 参数「菜单」）。
        # 这不是别名，只是参数解析；别名候选词（下表）才必须不命中。
        "功能菜单",
    ):
        assert matches(hit), f"应命中：{hit}"
    for miss in (
        "help",
        "/help",
        "帮助",
        "菜单",
        "详细帮助",
        "菜单 抽奖",
        "介绍下功能",
    ):
        assert not matches(miss), f"不该命中：{miss}"


def test_on_command_call_has_no_aliases_and_no_extra_entry():
    """静态守卫：handle.py 里 `on_command` **只有一个**调用、且不带 aliases 参数。"""
    tree = ast.parse(HANDLE_SRC.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "on_command"
    ]
    assert len(calls) == 1, "「功能」必须是唯一的 on_command 入口"
    kwargs = {kw.arg for kw in calls[0].keywords}
    assert "aliases" not in kwargs
    assert kwargs == {"priority", "block"}


def test_no_detail_help_entry_left_in_source():
    """静态守卫：独立的「详细帮助」入口已按用户要求删除，不许再加回来。"""
    tree = ast.parse(HANDLE_SRC.read_text(encoding="utf-8"))
    strings = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert not [s for s in strings if "详细帮助" in s]


def test_priority_and_block_pinned():
    """接线参数（priority/block）只写在装饰器里，必须静态钉住。"""
    from nonebot_plugin_info import handle

    assert handle.func_cmd.priority == 8
    assert handle.func_cmd.block is True


def test_handler_annotations_are_runtime_resolvable():
    """NoneBot 按**注解**注入 —— 注解挪进 TYPE_CHECKING 会生产静默失效。"""
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
    from nonebot.dependencies import get_typed_signature
    from nonebot.matcher import Matcher

    from nonebot_plugin_info import handle

    anns = {
        name: param.annotation
        for name, param in get_typed_signature(handle._h_func).parameters.items()
    }
    assert anns["matcher"] is Matcher
    assert anns["_event"] is GroupMessageEvent
    assert anns["args"] is Message


# ---------------------------------------------------------------- 三条路径


def test_no_args_sends_menu_image(monkeypatch):
    """无参数 → 出图（收到 image 段）。"""

    async def png(html: str) -> bytes:
        assert "功能菜单" in html
        return b"PNG"

    sent = _call(monkeypatch, "功能", render_html=png)
    assert len(sent) == 1
    assert getattr(sent[0], "type", None) == "image"


def test_render_fail_falls_back_to_text(monkeypatch):
    """渲染失败（返回 None）→ 纯文本菜单，**不是「命令没反应」**。"""

    async def broken(html: str) -> None:
        return None

    sent = _call(monkeypatch, "功能", render_html=broken)
    text = str(sent[0])
    assert "功能菜单" in text
    assert "【群内小游戏】" in text and "【功能】" in text
    assert "抽奖" in text and "次元图" in text
    assert "发「功能 <名字>」看详情" in text


def test_detail_by_name_text(monkeypatch):
    """「功能 抽奖」→ 详情（渲染不可用时是文本详情）。"""

    async def broken(html: str) -> None:
        return None

    sent = _call(monkeypatch, "功能 抽奖", render_html=broken)
    text = str(sent[0])
    assert text.splitlines()[0] == "抽奖"
    assert "群内抽奖小游戏" in text
    assert "· 抽奖 — 开始抽奖" in text


def test_detail_by_name_image(monkeypatch):
    """详情也要走图（渲染可用时）。"""

    async def png(html: str) -> bytes:
        assert "抽奖" in html and "群内抽奖小游戏" in html
        return b"PNG"

    sent = _call(monkeypatch, "功能 抽奖", render_html=png)
    assert getattr(sent[0], "type", None) == "image"


def test_detail_by_name_is_fuzzy(monkeypatch):
    """按名字查询走 find_plugin 的模糊匹配（子串）。"""

    async def broken(html: str) -> None:
        return None

    sent = _call(monkeypatch, "功能 抽", render_html=broken)
    assert str(sent[0]).splitlines()[0] == "抽奖"


def test_unknown_name_replies_not_found(monkeypatch):
    """查不到 → 明确回「没有找到」，不能沉默。"""

    async def broken(html: str) -> None:
        return None

    sent = _call(monkeypatch, "功能 不存在的功能", render_html=broken)
    assert "没有找到" in str(sent[0])
    assert "不存在的功能" in str(sent[0])


def test_dash_d_flag_shows_detail_menu(monkeypatch):
    """`功能 -d` → 详细菜单（不是当作插件名查询，也不能回「没有找到」）。"""

    async def broken(html: str) -> None:
        return None

    sent = _call(monkeypatch, "功能 -d", render_html=broken)
    text = str(sent[0])
    assert "没有找到" not in text
    assert "【群内小游戏】" in text
    assert "群内抽奖小游戏" in text  # 详细模式带 description
    assert "· 抽奖 — 开始抽奖" in text


def test_double_dash_detail_flag(monkeypatch):
    """`功能 --detail` 与 `-d` 等价。"""

    async def broken(html: str) -> None:
        return None

    sent = _call(monkeypatch, "功能 --detail", render_html=broken)
    text = str(sent[0])
    assert "没有找到" not in text
    assert "群内抽奖小游戏" in text


def test_detail_flag_with_name_queries_that_plugin(monkeypatch):
    """`功能 抽奖 -d` → 仍按名字查询（标志只剥掉、不当成名字）。"""

    async def broken(html: str) -> None:
        return None

    sent = _call(monkeypatch, "功能 抽奖 -d", render_html=broken)
    assert str(sent[0]).splitlines()[0] == "抽奖"


def test_empty_collection_still_replies(monkeypatch):
    """一个可展示插件都没有时也要回一条可用菜单（不能空响应）。"""

    async def broken(html: str) -> None:
        return None

    sent = _call(monkeypatch, "功能", items=[], render_html=broken)
    assert "功能菜单" in str(sent[0])


# ---------------------------------------------------------------- 真实管线


def test_real_pipeline_end_to_end(monkeypatch):
    """**真路径**：handle_event + 真 TrieRule 解析 + 真 matcher → 收到降级文本菜单。"""
    from nonebot.message import handle_event

    from nonebot_plugin_info import handle

    async def broken(html: str) -> None:
        return None  # 本机没装 htmlkit，生产里这条也是「渲染不通」的真降级路径

    monkeypatch.setattr(handle, "render_html", broken)
    monkeypatch.setattr(handle, "collect_plugins", lambda: _items())

    bot = _bot()
    sent: list[object] = []

    async def fake_call_api(api: str, **kwargs: object) -> dict[str, int]:
        sent.append(kwargs.get("message"))
        return {"message_id": 1}

    monkeypatch.setattr(bot, "call_api", fake_call_api)
    asyncio.run(handle_event(bot, _event("功能")))

    assert len(sent) == 1, f"应当只发一条消息，实际 {sent}"
    text = str(sent[0])
    assert "功能菜单" in text
    assert "【群内小游戏】" in text and "【功能】" in text
    assert "抽奖" in text and "次元图" in text


def test_real_pipeline_detail_by_name(monkeypatch):
    """真路径下的「功能 抽奖」：handler 收到 CommandArg 并回该插件详情。"""
    from nonebot.message import handle_event

    from nonebot_plugin_info import handle

    async def broken(html: str) -> None:
        return None

    monkeypatch.setattr(handle, "render_html", broken)
    monkeypatch.setattr(handle, "collect_plugins", lambda: _items())

    bot = _bot()
    sent: list[object] = []

    async def fake_call_api(api: str, **kwargs: object) -> dict[str, int]:
        sent.append(kwargs.get("message"))
        return {"message_id": 1}

    monkeypatch.setattr(bot, "call_api", fake_call_api)
    asyncio.run(handle_event(bot, _event("功能 抽奖")))

    assert len(sent) == 1
    assert str(sent[0]).splitlines()[0] == "抽奖"


def test_real_pipeline_ignores_alias_words(monkeypatch):
    """真路径下别名候选词不触发（用户要求：info 只实现「功能」）。"""
    from nonebot.message import handle_event

    bot = _bot()
    sent: list[object] = []

    async def fake_call_api(api: str, **kwargs: object) -> dict[str, int]:
        sent.append(kwargs.get("message"))
        return {"message_id": 1}

    monkeypatch.setattr(bot, "call_api", fake_call_api)
    for text in ("help", "帮助", "菜单", "详细帮助"):
        asyncio.run(handle_event(bot, _event(text)))
    assert sent == []

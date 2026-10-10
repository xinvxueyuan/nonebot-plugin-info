"""render 纯函数：转义、字段齐全、分组顺序、文本降级、渲染失败一律返回 None。

**不装 htmlkit 也能跑**：`_load_htmlkit()` 惰性 import，测试 monkeypatch 它即可。
"""

from __future__ import annotations

import asyncio
import importlib.util
import re

import pytest

from nonebot_plugin_info.collect import CommandItem, PluginItem


def _item(
    name: str,
    *,
    menu: str = "功能",
    description: str = "一句话介绍",
    usage: str = "用法",
    commands: tuple[CommandItem, ...] = (),
) -> PluginItem:
    return PluginItem(
        name=name,
        module=f"m_{name}",
        menu_type=menu,
        description=description,
        usage=usage,
        commands=commands,
    )


def _groups() -> dict[str, list[PluginItem]]:
    return {
        "群内小游戏": [
            _item(
                "今日老婆",
                menu="群内小游戏",
                description="从群友里抽一位当老婆",
                commands=(
                    CommandItem("今日老婆", "从群友里抽一位当老婆"),
                    CommandItem("换一只"),
                ),
            )
        ],
        "功能": [
            _item("次元图", commands=(CommandItem("次元图", "随机图片"),)),
            _item("抽奖"),
        ],
    }


# ---------------------------------------------------------------- menu html


def test_build_menu_html_escapes():
    """插件名/命令/分组名都是插件作者写的文本，含 `<` 不转义会破坏版面甚至注入标记。"""
    from nonebot_plugin_info import render

    groups = {"功能<script>": [_item("<b>x</b>", commands=(CommandItem("<i>y</i>"),))]}
    html = render.build_menu_html(groups)
    assert "<b>x</b>" not in html
    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert "<i>y</i>" not in html
    assert "&lt;i&gt;y&lt;/i&gt;" in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_build_menu_html_contains_all():
    """所有分组名、插件名、命令名都要在（缺一个就是菜单漏项）。"""
    from nonebot_plugin_info import render

    html = render.build_menu_html(_groups())
    for needle in (
        "【群内小游戏】",
        "【功能】",
        "今日老婆",
        "次元图",
        "抽奖",
        "换一只",
        "发「功能 &lt;名字&gt;」看详情",
    ):
        assert needle in html, f"菜单缺字段：{needle}"


def test_build_menu_html_group_order_preserved():
    """分组渲染顺序与传入 dict 一致（classify 已排好序，渲染层不能再排序）。"""
    from nonebot_plugin_info import render

    html = render.build_menu_html(_groups())
    assert html.index("【群内小游戏】") < html.index("【功能】")
    assert html.index("今日老婆") < html.index("次元图")


def test_build_menu_html_empty_groups():
    """一个可展示的插件都没有时也要出内容（不能是空白页）。"""
    from nonebot_plugin_info import render

    html = render.build_menu_html({})
    assert "还没有可展示的功能" in html
    assert render.build_menu_text({}).startswith("功能菜单")


def test_build_menu_html_is_wellformed_shell():
    """出图用的 HTML 外壳固定：charset utf-8 + 内联 CSS（litehtml 不解析外部资源）。"""
    from nonebot_plugin_info import render

    html = render.build_menu_html(_groups())
    assert html.startswith("<!DOCTYPE html>")
    assert "<meta charset='utf-8'>" in html
    assert "<style>" in html
    assert html.rstrip().endswith("</html>")


# ---------------------------------------------------------------- detail html


def test_build_detail_html_fields():
    """详情页：名字 / 描述 / usage / 每条命令 + desc 一个不少。"""
    from nonebot_plugin_info import render

    it = _item(
        "抽奖",
        description="群内抽奖小游戏",
        usage="抽奖 / 抽奖 -h",
        commands=(CommandItem("抽奖", "开始抽奖"), CommandItem("抽奖列表")),
    )
    html = render.build_detail_html(it)
    for needle in (
        "抽奖",
        "群内抽奖小游戏",
        "抽奖 / 抽奖 -h",
        "开始抽奖",
        "抽奖列表",
        "命令",
    ):
        assert needle in html, f"详情缺字段：{needle}"


def test_build_detail_html_without_usage_and_commands():
    from nonebot_plugin_info import render

    html = render.build_detail_html(_item("空插件", usage="", commands=()))
    assert "（无命令）" in html
    assert "空插件" in html


def test_build_detail_html_escapes():
    from nonebot_plugin_info import render

    it = _item("<b>坏名字</b>", description="<script>x</script>", usage="<u>u</u>")
    html = render.build_detail_html(it)
    assert "<b>坏名字</b>" not in html
    assert "<script>" not in html
    assert "<u>u</u>" not in html
    assert "&lt;b&gt;坏名字&lt;/b&gt;" in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "&lt;u&gt;u&lt;/u&gt;" in html


# ---------------------------------------------------------------- text fallback


def test_build_menu_text_equivalent():
    """文本降级与图字段一致（逐个字段断言，不是只看开头）。"""
    from nonebot_plugin_info import render

    text = render.build_menu_text(_groups())
    assert text.splitlines()[0] == "功能菜单"
    for needle in (
        "【群内小游戏】",
        "【功能】",
        "今日老婆",
        "换一只",
        "次元图",
        "抽奖",
    ):
        assert needle in text, f"文本菜单缺字段：{needle}"
    assert "发「功能 <名字>」看详情" in text
    assert "<div" not in text and "<span" not in text
    # 顺序与分组顺序一致
    assert text.index("【群内小游戏】") < text.index("【功能】")


def test_build_menu_text_marks_missing_commands():
    from nonebot_plugin_info import render

    text = render.build_menu_text({"功能": [_item("无命令插件", commands=())]})
    assert "（无命令）" in text


def test_build_detail_text_fields():
    """详情文本与图字段一致；无 usage / 无命令时也不能崩。"""
    from nonebot_plugin_info import render

    it = _item(
        "抽奖",
        description="群内抽奖小游戏",
        usage="抽奖",
        commands=(CommandItem("抽奖", "开始抽奖"), CommandItem("抽奖列表")),
    )
    text = render.build_detail_text(it)
    assert text.splitlines()[0] == "抽奖"
    assert "群内抽奖小游戏" in text
    assert "抽奖" in text
    assert "· 抽奖 — 开始抽奖" in text
    assert "· 抽奖列表" in text

    bare = render.build_detail_text(_item("空插件", usage="", commands=()))
    assert "空插件" in bare
    assert "命令：" in bare


def test_build_detail_text_does_not_escape():
    """文本降级走的是 QQ 纯文本，**不能**把 &lt; 这类实体发给用户。"""
    from nonebot_plugin_info import render

    text = render.build_detail_text(_item("<b>x</b>", description="含 < 与 & 的说明"))
    assert "<b>x</b>" in text
    assert "&lt;" not in text


# ---------------------------------------------------------------- htmlkit 接线


def test_render_html_calls_html_to_pic_with_max_width(monkeypatch):
    """渲染契约：`html_to_pic(html, max_width=MAX_WIDTH)`；MAX_WIDTH 必须 ≥ 卡片宽。"""
    from nonebot_plugin_info import render

    calls: dict[str, object] = {}

    async def fake(html: str, **kwargs: object) -> bytes:
        calls["html"] = html
        calls["kwargs"] = kwargs
        return b"PNG"

    monkeypatch.setattr(render, "_load_htmlkit", lambda: fake)
    got = asyncio.run(render.render_html("<html>hi</html>"))
    assert got == b"PNG"
    assert calls["html"] == "<html>hi</html>"
    assert calls["kwargs"] == {"max_width": render.MAX_WIDTH}
    assert render.MAX_WIDTH == 640
    assert render.MAX_WIDTH >= render.MENU_WIDTH + 2 * 14


def test_render_html_returns_none_on_exception(monkeypatch):
    """**失败返回 None 且不抛** —— 抛出去会表现成「命令没反应」。"""
    from nonebot_plugin_info import render

    def boom() -> object:
        raise RuntimeError("litehtml 炸了")

    monkeypatch.setattr(render, "_load_htmlkit", boom)
    assert asyncio.run(render.render_html("<html/>")) is None


def test_render_html_none_when_html_to_pic_raises(monkeypatch):
    """失败发生在 `await html_to_pic(...)` 里时同样只 warning + None。"""
    from nonebot_plugin_info import render

    async def boom(html: str, **kwargs: object) -> bytes:
        raise ValueError(f"坏 HTML: {html} {kwargs}")

    monkeypatch.setattr(render, "_load_htmlkit", lambda: boom)
    assert asyncio.run(render.render_html("<html/>")) is None


def test_render_html_none_when_htmlkit_missing():
    """真实 ImportError 路径（本机不装 htmlkit）：走真身 _load_htmlkit，None 且不抛。"""
    from nonebot_plugin_info import render

    if importlib.util.find_spec("nonebot_plugin_htmlkit") is not None:
        pytest.skip("本机装了 htmlkit，跳过「依赖缺失」路径")
    assert asyncio.run(render.render_html("<html/>")) is None


# ---------------------------------------------------------------- CSS 硬约束


def test_css_pins_cjk_font_and_has_no_flex_gap():
    """渲染器（litehtml）不是 Chromium：`gap` 不生效、必须显式声明 CJK 字体。"""
    from nonebot_plugin_info import render

    stripped = re.sub(r"/\*.*?\*/", "", render._CSS, flags=re.DOTALL)
    assert "gap:" not in stripped
    assert "display: flex" not in stripped
    assert "WenQuanYi" in stripped or "Noto Sans CJK SC" in stripped
    assert f"width: {render.MENU_WIDTH}px" in stripped

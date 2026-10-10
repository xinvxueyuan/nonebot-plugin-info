"""命令「功能」：菜单 / 详情 / 详细模式（-d）。

⚠️ 口径（用户 2026-10-11 拍板）：**只实现「功能」这一个命令词，不带任何别名**。
原计划里的 help/帮助/菜单 别名与那个独立入口都已删除 —— 「菜单」会与 lingchu-bot
已注册的「菜单」命令撞车。详细模式只由 `功能 -d` / `功能 --detail` 进入。

不加 `to_me()`：qbot 生态（`COMMAND_START=["", "/"]`）里命令都是直接发、无需 @bot，
加了 @ 反而会变成「命令没反应」。

渲染是锦上添花：`render_html` 返回 None（没装 htmlkit / litehtml 失败）就发纯文本，
绝不让渲染问题表现成「命令没反应」。
"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from .collect import classify, collect_plugins, find_plugin
from .render import (
    build_detail_html,
    build_detail_menu_text,
    build_detail_text,
    build_menu_html,
    build_menu_text,
    render_html,
)

#: 取一个不与其它插件冲突的中间值（qbot 里 lingchu 等吃更小/更大的优先级）
PRIORITY: int = 8

#: 详细模式的标志位（剥掉后剩下的文本仍按插件名查询）
DETAIL_FLAGS: tuple[str, ...] = ("-d", "--detail")

func_cmd = on_command("功能", priority=PRIORITY, block=True)


@func_cmd.handle()
async def _h_func(
    matcher: Matcher, _event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    """「功能」的三个分支：详细菜单 / 某个插件详情 / 菜单。

    ⚠️ `_event` 只用于**限定事件类型**（依赖注入按注解匹配、不看形参名），
    未使用所以带下划线前缀。
    """
    text = args.extract_plain_text().strip()
    detail = False
    for flag in DETAIL_FLAGS:
        if text.endswith(flag):
            detail = True
            text = text[: -len(flag)].strip()

    items = collect_plugins()

    if detail and not text:
        await matcher.finish(build_detail_menu_text(classify(items)))

    if text:
        it = find_plugin(items, text)
        if it is None:
            await matcher.finish(f"没有找到「{text}」这个功能")
        png = await render_html(build_detail_html(it))
        if png is not None:
            await matcher.finish(MessageSegment.image(png))
        await matcher.finish(build_detail_text(it))

    groups = classify(items)
    png = await render_html(build_menu_html(groups))
    if png is not None:
        await matcher.finish(MessageSegment.image(png))
    await matcher.finish(build_menu_text(groups))

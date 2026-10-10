"""功能菜单渲染（nonebot-plugin-htmlkit，**可选依赖**）。

三条铁律（照 nonebot-plugin-waifu 的 render.py 实测结论）：

1. 任何失败只 warning 并返回 `None` —— 调用方回退纯文本，绝不表现成「命令没反应」；
2. 所有插件可控文本必须 `html.escape`（插件名/描述/命令都是别人写的元数据）；
3. **litehtml 不是 Chromium**：`dpi` 无效、`max_width` 是**上限而不是缩放器**、flex 的
   `gap` **不生效**。所以宽度/字号/间距全部显式写死、间距只用 `margin`，字体必须显式
   声明 CJK，否则宿主默认 `sans-serif` 不含中文字形时整张图是方块。
"""

from __future__ import annotations

import html as html_mod
import logging
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from .collect import PluginItem

logger = logging.getLogger("nonebot_plugin_info")

#: 卡片宽度；`MAX_WIDTH` 必须 ≥ 卡片宽 + body padding（否则被压扁）。
MENU_WIDTH: Final[int] = 560
MAX_WIDTH: Final[int] = 640

_CSS: Final[str] = f"""
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 14px; background: #f5f6fa;
    font-family: "WenQuanYi Zen Hei", "Noto Sans CJK SC", "Microsoft YaHei",
                 "PingFang SC", sans-serif;
  }}
  .card {{
    width: {MENU_WIDTH}px; background: #ffffff; border-radius: 12px;
    padding: 18px 20px; border: 1px solid #e3e6ef;
  }}
  .title {{
    font-size: 22px; font-weight: bold; color: #2b2f3a;
    padding-left: 10px; border-left: 5px solid #5b6cff; margin-bottom: 12px;
  }}
  .sec {{ font-size: 16px; font-weight: bold; color: #5b6cff; margin: 14px 0 6px 0; }}
  .row {{ margin: 6px 0 0 8px; }}
  .pname {{ font-size: 15px; font-weight: bold; color: #2b2f3a; }}
  .cmds {{ font-size: 13px; color: #6b7280; margin: 2px 0 0 12px; }}
  .desc {{ font-size: 13px; color: #444a55; margin: 6px 0 2px 0; }}
  .hint {{ font-size: 12px; color: #9aa0ac; margin-top: 14px; }}
"""


def _esc(s: str) -> str:
    """转义可能含尖括号/引号的插件文本。"""
    return html_mod.escape(s, quote=True)


def _commands_inline(it: PluginItem) -> str:
    """菜单里一行显示的命令名（「 / 」分隔）。"""
    return " / ".join(c.command for c in it.commands) or "（无命令）"


def build_menu_html(groups: dict[str, list[PluginItem]]) -> str:
    """菜单页 HTML（**纯函数**）。groups 为 `classify()` 的返回（顺序即渲染顺序）。"""
    parts: list[str] = []
    for menu, items in groups.items():
        parts.append(f'<div class="sec">【{_esc(menu)}】</div>')
        parts.extend(
            f'<div class="row"><span class="pname">{_esc(it.name)}</span>'
            f'<div class="cmds">{_esc(_commands_inline(it))}</div></div>'
            for it in items
        )
    body = "\n".join(parts) if parts else '<div class="desc">还没有可展示的功能</div>'
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        f"{_CSS}</style></head>"
        f'<body><div class="card"><div class="title">功能菜单</div>{body}'
        '<div class="hint">发「功能 &lt;名字&gt;」看详情</div></div></body></html>'
    )


def build_detail_html(it: PluginItem) -> str:
    """详情页 HTML（**纯函数**）。"""
    cmd_rows = (
        "".join(
            f'<div class="cmds">· {_esc(c.command)}'
            + (f" — {_esc(c.desc)}" if c.desc else "")
            + "</div>"
            for c in it.commands
        )
        or '<div class="cmds">（无命令）</div>'
    )
    usage = f'<div class="desc">{_esc(it.usage)}</div>' if it.usage else ""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        f"{_CSS}</style></head>"
        f'<body><div class="card"><div class="title">{_esc(it.name)}</div>'
        f'<div class="desc">{_esc(it.description)}</div>{usage}'
        f'<div class="sec">命令</div>{cmd_rows}'
        "</div></body></html>"
    )


def build_menu_text(groups: dict[str, list[PluginItem]]) -> str:
    """菜单纯文本等价物（渲染不可用时发送；字段与图一致）。"""
    lines = ["功能菜单"]
    for menu, items in groups.items():
        lines.append(f"【{menu}】")
        lines.extend(f"  {it.name}：{_commands_inline(it)}" for it in items)
    lines.append("发「功能 <名字>」看详情")
    return "\n".join(lines)


def build_detail_text(it: PluginItem) -> str:
    """详情纯文本等价物（**不转义** —— 发给用户的正文不能出现 `&lt;`）。"""
    lines = [it.name, it.description]
    if it.usage:
        lines.append(it.usage)
    lines.append("命令：")
    lines.extend(
        "  · " + c.command + (f" — {c.desc}" if c.desc else "") for c in it.commands
    )
    return "\n".join(lines)


def build_detail_menu_text(groups: dict[str, list[PluginItem]]) -> str:
    """详细菜单（`功能 -d`）：每个插件带一句话说明 + 全部命令与说明。"""
    lines: list[str] = ["功能菜单（详细）"]
    for menu, items in groups.items():
        lines.append(f"【{menu}】")
        for it in items:
            lines.append(f"  {it.name}：{it.description}")
            lines.extend(
                "    · " + c.command + (f" — {c.desc}" if c.desc else "")
                for c in it.commands
            )
    lines.append("发「功能 <名字>」看详情")
    return "\n".join(lines)


def _load_htmlkit() -> Any:
    """惰性取 `html_to_pic`（**单独抽出来**，测试可 monkeypatch，不必真装 htmlkit）。"""
    from nonebot_plugin_htmlkit import (  # pyright: ignore[reportMissingImports]
        html_to_pic,
    )

    return html_to_pic


async def render_html(html: str) -> bytes | None:
    """渲染 PNG；**任何失败只 warning 并返回 None**（调用方回退纯文本）。"""
    try:
        html_to_pic = _load_htmlkit()
        return await html_to_pic(html, max_width=MAX_WIDTH)
    except Exception as e:
        logger.warning("功能菜单渲染失败，回退纯文本: %s: %s", type(e).__name__, e)
        return None

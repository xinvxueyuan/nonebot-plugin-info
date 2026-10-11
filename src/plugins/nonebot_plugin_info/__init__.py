"""信息插件（命令「功能」）：扫描已加载插件的元数据出分类帮助。"""

from __future__ import annotations

from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="功能",
    description="查看全部插件功能菜单与详情（读取各插件 __plugin_meta__.extra）",
    usage=(
        "功能            查看功能菜单\n"
        "功能 <名字>     查看某个功能的详情\n"
        "功能 -d         详细菜单"
    ),
    type="application",
    homepage="https://github.com/xinvxueyuan/nonebot-plugin-info",
    supported_adapters={"nonebot.adapters.onebot.v11"},
    config=Config,
    extra={
        # 隐藏自己（照 zhenxun：help 插件 is_show=False）——否则菜单里会多一条
        # 「功能」自己，看着像重影。但详情仍能按名字查到它（用户点名就给）。
        "is_show": False,
        # 本插件自己的帮助信息（按 extra 规范：menu_type 不给 → collect 默认「功能」）
        "introduction": "查看全部插件功能菜单与详情（读 __plugin_meta__.extra）",
        "commands": [
            {"command": "功能", "desc": "查看功能菜单"},
            {"command": "功能 <名字>", "desc": "查看某个功能的详情"},
            {"command": "功能 -d", "desc": "详细菜单（含每个功能的说明与命令）"},
        ],
    },
)

# 导入即注册命令（`__all__` 里列出来，免得 ruff 判成未使用导入）
from . import handle

__all__ = ["__plugin_meta__", "handle"]

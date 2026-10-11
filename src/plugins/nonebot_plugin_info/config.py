"""信息插件配置（环境变量前缀 `INFO_`）。

目前只有一个旋钮：**宿主侧菜单信息覆盖** —— 给那些**不能改源码**的第三方插件
补 `menu_type` / `order` / `commands` 等菜单元数据（用户 2026-10-11 拍板：
「不改第三方一行，覆盖写在信息插件自己的配置里」），菜单里就不会再出现空挡。

`.env` 里是 JSON 字符串（NoneBot 对复杂类型键走 `json.loads`）；
完整写法与生产实例见 README 的「宿主侧菜单信息覆盖」一节。
"""

from __future__ import annotations

from typing import Any, Final

from nonebot import get_plugin_config
from pydantic import BaseModel, Field

#: 覆盖允许触碰的键（与 collect._OVERRIDABLE 一致；写在这里是为了配置文档可读）。
OVERRIDABLE_KEYS: Final[tuple[str, ...]] = (
    "menu_type",
    "order",
    "commands",
    "introduction",
    "is_show",
)


class Config(BaseModel):
    """信息插件配置。"""

    info_extra_overrides: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "宿主侧菜单信息覆盖（不改第三方插件源码）：键 = 插件模块短名"
            "（如 nonebot_plugin_parser_lite）或 metadata.name；值只认 "
            f"{'/'.join(OVERRIDABLE_KEYS)}，其余键忽略。写法见 README。"
        ),
    )


plugin_config: Config = get_plugin_config(Config)

__all__ = ["OVERRIDABLE_KEYS", "Config", "plugin_config"]

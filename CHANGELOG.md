# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-10-11

首版。

### 新增

- 命令「功能」：菜单出图（htmlkit 可选）——扫描全部已加载插件的 `__plugin_meta__.extra`，
  按 `menu_type` 分组渲染，组间按组内最小 `order` 排、组内按 `(order, name)` 排。
- 命令「功能 <名字>」：插件详情（图/文本），名字匹配 精确 → 忽略大小写 → 子串；
  查不到明确回「没有找到「xx」这个功能」；**能查到 `is_show=False` 的隐藏插件**
  （用户点名查就给，不跟着菜单一起过滤）。
- 命令「功能 -d」/「功能 --detail」：详细菜单（纯文本，每个插件带一句话说明与全部命令）。
- 文本降级：渲染不可用（没装 htmlkit / litehtml 失败）时自动发纯文本等价菜单与详情，
  **绝不抛异常、绝不表现成「命令没反应」**。
- 元数据规范（字段对齐 zhenxun 的 `PluginExtraData`）：`menu_type` / `commands`
  （三种写法：字符串、`{"command": ...}`、`{"command": ..., "desc": ...}`）/
  `introduction` / `order` / `is_show`；`type="library"` 的工具库不进菜单；
  非法元数据只跳过该项、不让菜单挂掉。
- 本插件自己的元数据：`is_show=False`（帮助插件自己不进菜单）、`commands` 列出三条用法。

### 变更

- **命令词只有「功能」，不带任何别名**（`help` / `帮助` / `菜单` 全部不收）：
  `菜单` 会与宿主（lingchu-bot 等）已注册的同名命令撞车。
- **不加 `to_me()`**：qbot 生态的命令都是裸词直接发，要求 @bot 会表现成「命令没反应」。
- 详细模式只由 `功能 -d` / `功能 --detail` 进入，**没有独立的第二个命令入口**。

### 已知限制

- 菜单数据是加载时快照，改插件元数据需重启宿主。
- 「功能」是裸词，群里聊到这两个字也会触发菜单（裸词触发生态的共同代价）。
- 出图需要宿主装 htmlkit + 中文字体；没装走纯文本。

[0.1.0]: https://github.com/xinvxueyuan/nonebot-plugin-info/releases/tag/v0.1.0

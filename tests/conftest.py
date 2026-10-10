"""pytest 全局初始化。

**为什么必须有这个文件**：本包的 `__init__.py` 是 NoneBot 插件入口，模块级会调用
`on_command()`（经 `handle`）。测试 `import nonebot_plugin_info` 会先执行它 ——
没有初始化过的 driver 会抛 `ValueError: NoneBot has not been initialized.`，
而 conftest 最先被 pytest 导入，正好赶在前面。

⚠️ `COMMAND_START` 含**空串**（生产 qbot 里裸词直接触发）。空串**不能**用
`nonebot.init(COMMAND_START=["", "/"])` 传（pydantic 会丢掉空字符串，只剩 `{'/'}`），
必须走环境变量 JSON 反序列化。
"""

import os

import nonebot
from nonebot.adapters.onebot.v11 import Adapter

os.environ.setdefault("COMMAND_START", '["", "/"]')

# 用 none 驱动：单元测试不需要任何服务器/客户端，省掉 fastapi+uvicorn 那一坨。
nonebot.init(driver="~none", log_level="WARNING")
nonebot.get_driver().register_adapter(Adapter)

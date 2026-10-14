"""变异检验：把每处关键行为**故意改坏**，确认对应测试真的变红。

没红过的断言只是装饰 —— 它可能断言了恒真条件、或读错了属性名，
这两种情况在正常代码上都是绿的。用法：

    env -u UV_PYTHON ... uv run python scripts/mutation_check.py
"""

# ruff: noqa: T201  # 这是命令行脚本：print 就是它的输出通道

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "src/plugins/nonebot_plugin_info"
COLLECT = PKG / "collect.py"
RENDER = PKG / "render.py"

# ⚠️ 不要加 `--no-cov`（本仓未装 pytest-cov，会报 unrecognized arguments）
TESTS = ["tests/", "-q", "-p", "no:cacheprovider", "-x"]

#: 剔除会干扰子进程的环境变量（本机 uv 约定）。
_DROP_ENV = (
    "UV_PYTHON",
    "UV_PROJECT_ENVIRONMENT",
    "SSL_CERT_FILE",
    "VIRTUAL_ENV",
    "PYTHONPATH",
)

#: 本机 pytest 默认临时目录有 ACL 坑（收尾 PermissionError）；
#: 没设 BASETEMP 就给个可写的 basetemp。
_DEFAULT_BASETEMP = "C:/Users/admin/AppData/Local/hermes/cache/scratch/info_t"


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in _DROP_ENV:
        env.pop(key, None)
    env.setdefault("PYTEST_ADDOPTS", f"--basetemp={_DEFAULT_BASETEMP}")
    return env


def run() -> bool:
    r = subprocess.run(
        ["uv", "run", "python", "-m", "pytest", *TESTS],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=_child_env(),
        encoding="utf-8",
        errors="replace",
    )
    return r.returncode == 0


MUTATIONS = [
    (
        "M1 菜单不排除 is_show=False 的插件（隐藏插件泄漏进菜单）",
        COLLECT,
        "    for it in items:\n"
        "        if not it.is_show:\n"
        "            continue\n"
        "        groups.setdefault(it.menu_type, []).append(it)",
        "    for it in items:\n"
        "        if False:  # 变异：不筛隐藏插件\n"
        "            continue\n"
        "        groups.setdefault(it.menu_type, []).append(it)",
    ),
    (
        "M2 build_menu_html 不转义插件名（XSS / 版面破坏）",
        RENDER,
        '<span class="pname">{_esc(it.name)}</span>',
        '<span class="pname">{it.name}</span>',
    ),
    (
        "M3 render_html 渲染失败改成抛出（命令会变成「没反应」）",
        RENDER,
        '        logger.warning("功能菜单渲染失败，回退纯文本: %s: %s",'
        " type(e).__name__, e)\n"
        "        return None",
        "        raise",
    ),
    (
        "M4 classify 不排序（菜单顺序随机/按插入顺序）",
        COLLECT,
        "    for v in groups.values():\n"
        "        v.sort(key=lambda x: (x.order, x.name))",
        "    for v in groups.values():\n        pass  # 变异：不排序",
    ),
    (
        "M5 find_plugin 只精确匹配（模糊查询失效）",
        COLLECT,
        "    ql = q.lower()\n"
        "    for it in items:\n"
        "        if it.name.lower() == ql:\n"
        "            return it\n"
        "    for it in items:\n"
        "        if ql in it.name.lower():\n"
        "            return it\n"
        "    return None",
        "    ql = q.lower()\n    return None  # 变异：去掉大小写与子串匹配\n",
    ),
    (
        "M6 宿主侧菜单覆盖失效（第三方插件在菜单里又出空挡）",
        COLLECT,
        "    raw = overrides.get(_module_short(module)) or overrides.get(name)\n"
        "    if not isinstance(raw, dict):\n"
        "        return {}\n"
        "    return {k: v for k, v in raw.items() if k in _OVERRIDABLE}",
        "    return {}  # 变异：覆盖全部失效（第三方插件照样空挡）\n",
    ),
]


def main() -> int:
    print("=== 基线 ===")
    if not run():
        print("  ✗ 基线已红 —— 先修好再来做变异检验")
        return 1
    print("  ✓ 全绿")

    results = []
    for label, path, old, new in MUTATIONS:
        orig = path.read_bytes().decode("utf-8")
        cnt = orig.count(old)
        if cnt != 1:
            print(f"  ⚠ {label}: 锚点命中 {cnt} 次 —— 跳过（锚点要能唯一定位）")
            results.append((label, None))
            continue
        path.write_bytes(orig.replace(old, new).encode("utf-8"))
        try:
            caught = not run()
        finally:
            path.write_bytes(orig.encode("utf-8"))
        results.append((label, caught))
        print(f"  {'[捕获]' if caught else '[漏网]'} {label}")

    caught_n = sum(1 for _, c in results if c is True)
    print(f"\n=== 捕获 {caught_n}/{len(results)} ===")
    for label, c in results:
        mark = "✓" if c else ("✗" if c is False else "⚠")
        print(f"  {mark} {label}")
    return 0 if caught_n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

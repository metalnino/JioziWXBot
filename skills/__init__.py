"""
SiverWXBot Skills 插件系统
========================
自动扫描 skills/ 目录下的模块，收集工具定义和执行函数。

每个 Skill 模块需要导出:
  - TOOL_DEF: dict  — OpenAI function calling 格式的工具定义
  - execute(args: dict) -> str  — 工具执行函数
"""

import os
import json
import importlib
import traceback

# 已注册的 skills: {function_name: {"tool_def": dict, "execute": callable}}
_registry = {}


def _discover_skills():
    """扫描当前目录下所有 .py 模块，自动注册 Skills"""
    skills_dir = os.path.dirname(os.path.abspath(__file__))
    for filename in os.listdir(skills_dir):
        if filename.startswith('_') or not filename.endswith('.py'):
            continue
        module_name = filename[:-3]
        try:
            mod = importlib.import_module(f"skills.{module_name}")
            if hasattr(mod, 'TOOL_DEF') and hasattr(mod, 'execute'):
                func_name = mod.TOOL_DEF['function']['name']
                _registry[func_name] = {
                    "tool_def": mod.TOOL_DEF,
                    "execute": mod.execute,
                }
                print(f"[Skills] 已加载 Skill: {func_name} ({module_name}.py)")
            else:
                print(f"[Skills] 跳过 {module_name}.py (缺少 TOOL_DEF 或 execute)")
        except Exception as e:
            print(f"[Skills] 加载 {module_name}.py 失败: {e}")
            traceback.print_exc()


def get_all_tools():
    """返回所有已注册 Skills 的 OpenAI tools 格式列表"""
    if not _registry:
        _discover_skills()
    return [info["tool_def"] for info in _registry.values()]


def execute_tool(function_name, arguments):
    """
    执行指定的工具函数。

    :param function_name: 工具函数名
    :param arguments: JSON 字符串或 dict 格式的参数
    :return: 执行结果字符串
    """
    if not _registry:
        _discover_skills()

    if function_name not in _registry:
        return f"未知的工具: {function_name}"

    try:
        if isinstance(arguments, str):
            args = json.loads(arguments)
        else:
            args = arguments
        result = _registry[function_name]["execute"](args)
        return str(result)
    except Exception as e:
        return f"工具执行出错: {e}"


def get_skills_count():
    """返回已加载的 Skills 数量"""
    if not _registry:
        _discover_skills()
    return len(_registry)

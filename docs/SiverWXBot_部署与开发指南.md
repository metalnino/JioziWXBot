# SiverWXBot Plus 部署与开发指南

> **版本**: V4.7.13 + Skills 插件系统  
> **最后更新**: 2026-04-16  
> **维护人**: 博同学

---

## 一、项目概述

SiverWXBot Plus 是基于 `wxautox4` 的微信 PC 端自动回复机器人，集成了 AI 大模型（Gemini 2.5 Pro）和自研 Skills 插件系统，用于植百汇公司的智能客服场景。

### 核心架构

```
┌─────────────────────────────────────────────────┐
│              SiverWXBot Plus                     │
│                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │ Web 面板  │   │ wxautox4 │   │  AI API      │ │
│  │ (Flask)   │   │ (UI自动化)│   │ (Gemini)     │ │
│  │ :10001    │   │          │   │              │ │
│  └──────────┘   └──────────┘   └──────┬───────┘ │
│                                       │          │
│                              ┌────────▼────────┐ │
│                              │  Skills 插件系统  │ │
│                              │  (Function Call) │ │
│                              │  weather.py ...  │ │
│                              └─────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 目录结构

```
SiverWXBot_plus/
├── web_server.py          # 入口文件（Flask Web 面板）
├── wxbot_core.py          # 核心逻辑（消息监听、AI调用、消息发送）
├── config/
│   ├── config.json        # 主配置文件
│   ├── prompt/
│   │   └── 植百汇客服.md   # AI 人设 Prompt
│   └── memory/            # 对话记忆存储
├── skills/                # ⭐ Skills 插件目录
│   ├── __init__.py        # Skills 注册器
│   └── weather.py         # 天气查询 Skill
├── requirements.txt
└── docs/
    └── SiverWXBot_部署与开发指南.md  # 本文档
```

---

## 二、环境要求

| 项目 | 要求 |
|------|------|
| **操作系统** | Windows 10/11（需要桌面环境，不能纯 Server Core） |
| **Python** | 3.10.x（推荐 pyenv 管理） |
| **微信 PC** | 4.1.7 ~ 4.1.8.107（⚠️ 版本过高或过低都不行） |
| **wxautox4** | >= 40.1.12（`pip install wxautox4 --upgrade`） |
| **网络** | 需能访问 `newapi.aisonnet.org`（AI API）和 `wttr.in`（天气 API） |

### ⚠️ 关键注意事项

1. **微信窗口必须保持可见**  
   wxautox4 依赖 UI 自动化操作微信窗口。如果微信缩到托盘或被遮挡，会导致 `Find Control Timeout` 错误无法发送消息。

2. **不能通过远程桌面断开后运行**  
   断开远程桌面后桌面会话可能失效，UI 自动化将无法工作。建议用 VNC 或保持物理显示器连接。

3. **wxautox4 版本必须匹配**  
   旧版本（如 40.1.9）不兼容微信 4.1.8，会导致"发送按钮找不到"。务必用最新版。

---

## 三、首次部署

### 3.1 安装依赖

```bash
# 使用 pyenv 切换到 Python 3.10
pyenv local 3.10.11

# 安装依赖
pip install -r requirements.txt

# 确保 wxautox4 是最新版
pip install wxautox4 --upgrade
```

### 3.2 配置文件

编辑 `config/config.json`，关键配置项：

```json
{
    "api_url": "https://newapi.aisonnet.org/v1",
    "api_key": "sk-xxxxx",
    "model": "gemini-2.5-pro",
    "sdk_type": "OpenAI",          // ⚠️ 必须是 OpenAI，不是 DusAPI
    
    "AllListen_switch": false,      // false = 白名单模式
    "listen_list": ["博同学🏔"],    // 私聊白名单
    
    "group_switch": true,           // 开启群聊
    "group": ["减肥晚饭小队"],       // 群聊白名单（必须填群名）
    "group_reply_at": true,         // 仅被@时回复
    "group_reply_at_msg": true,     // 回复时@发言人
    
    "reply_delay_switch": true,     // 模拟人工延迟
    "reply_delay_min": 3,
    "reply_delay_max": 8,
    
    "memory_switch": true,          // 对话记忆
    "memory_context_count": 20      // 记忆上下文条数
}
```

### 3.3 启动服务

```bash
cd D:\博\python\SiverWXBot_plus
python web_server.py
```

然后浏览器打开 `http://localhost:10001`，账号 `admin` / 密码 `123456`，点击「启动机器人」。

---

## 四、Skills 插件系统开发指南

### 4.1 什么是 Skills

Skills 是基于 **Gemini Function Calling** 的插件系统。当用户发送消息时：

1. AI 模型收到消息 + 所有可用工具的定义
2. 如果 AI 判断需要调用工具，返回 `tool_calls`
3. 代码层执行对应的 Skill 函数，拿到真实数据
4. 将工具结果回传给 AI，AI 用自然语言总结后回复用户

```
用户: "南京今天天气怎么样"
  ↓
Gemini: tool_calls → get_weather({"city": "南京"})
  ↓
weather.py: 调用 wttr.in API → 返回 "局部多云 20°C..."
  ↓
Gemini: "南京今天局部多云，气温20度，记得带伞哦~"
  ↓
微信: 发送回复给用户
```

### 4.2 创建新 Skill

在 `skills/` 目录下创建新的 `.py` 文件，只需要导出两个东西：

#### 模板

```python
"""
我的新 Skill
============
简要说明这个 Skill 做什么。
"""

import requests  # 或其他依赖

# ========================================
# 1. 工具定义（OpenAI Function Calling 格式）
# ========================================
TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "my_skill_name",           # 工具函数名（英文，下划线分隔）
        "description": "这个工具做什么的中文描述", # AI 根据这个判断何时调用
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "参数1的说明"
                },
                "param2": {
                    "type": "integer",
                    "description": "参数2的说明（可选）"
                }
            },
            "required": ["param1"]          # 必填参数列表
        }
    }
}


# ========================================
# 2. 执行函数
# ========================================
def execute(args: dict) -> str:
    """
    接收 AI 传来的参数，执行实际操作，返回文本结果。
    
    :param args: 字典格式的参数，与 TOOL_DEF.parameters 对应
    :return: 字符串格式的执行结果
    """
    param1 = args.get("param1", "默认值")
    
    try:
        # 在这里做你的逻辑：调 API、查数据库、算数据...
        result = f"查询结果: {param1} 的信息是 XXX"
        return result
    except Exception as e:
        return f"查询失败: {str(e)}"
```

#### 命名规范

- 文件名：`snake_case.py`（如 `weather.py`, `order_query.py`）
- 函数名：`snake_case`（如 `get_weather`, `query_order`）
- 不要以 `_` 开头（会被跳过）

#### 加载机制

- Skills 在 Bot 首次收到消息时**自动扫描加载**，无需手动注册
- 添加新 Skill 后需要**重启 Bot**（停止 → 启动）才能生效
- 加载成功会在日志中看到：`[Skills] 已加载 Skill: xxx (xxx.py)`

### 4.3 现有 Skills 清单

| Skill 文件 | 函数名 | 功能 | API |
|-----------|--------|------|-----|
| `weather.py` | `get_weather` | 查询实时天气预报 | wttr.in（免费） |

### 4.4 Skill 开发最佳实践

1. **description 写清楚**  
   AI 根据 `description` 判断是否调用工具。写得越准确，触发越精准。
   ```
   ❌ "获取信息"
   ✅ "获取指定城市的实时天气预报信息，包括温度、天气状况、湿度、风速等"
   ```

2. **返回结构化文本**  
   返回格式化的文本便于 AI 理解和总结：
   ```
   ❌ "20,多云,78"
   ✅ "温度: 20°C\n天气: 多云\n湿度: 78%"
   ```

3. **做好异常处理**  
   网络请求、API 调用都可能失败，必须 try-except：
   ```python
   try:
       resp = requests.get(url, timeout=10)
       resp.raise_for_status()
   except requests.exceptions.Timeout:
       return "查询超时，请稍后再试"
   except Exception as e:
       return f"查询失败: {str(e)}"
   ```

4. **设置合理的超时**  
   工具执行会阻塞回复流程，建议 API 超时不超过 10 秒。

5. **不要在 Skill 中做复杂计算**  
   Skill 只负责获取数据，让 AI 来做自然语言总结和判断。

### 4.5 Skill 开发示例：工单查询

以下是一个查询植百汇工单的 Skill 示例（假设有后端 API）：

```python
"""
工单查询 Skill
"""
import requests

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "query_order",
        "description": "查询植百汇绿植租赁的工单/订单状态，包括下单时间、配送状态、养护记录等",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "工单编号"
                },
                "customer_name": {
                    "type": "string",
                    "description": "客户名称（模糊搜索）"
                }
            },
            "required": []
        }
    }
}

def execute(args: dict) -> str:
    order_id = args.get("order_id")
    customer = args.get("customer_name")
    
    try:
        params = {}
        if order_id:
            params["id"] = order_id
        if customer:
            params["customer"] = customer
            
        resp = requests.get(
            "https://your-api.example.com/orders",
            params=params,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("orders"):
            return "未找到匹配的工单"
        
        lines = []
        for order in data["orders"][:3]:
            lines.append(
                f"工单号: {order['id']}\n"
                f"客户: {order['customer']}\n"
                f"状态: {order['status']}\n"
                f"下单时间: {order['created_at']}"
            )
        return "\n---\n".join(lines)
        
    except Exception as e:
        return f"工单查询失败: {str(e)}"
```

---

## 五、已做的定制修改

以下是对 SiverWXBot 原版代码的所有改动，**升级 SiverWXBot 版本时需要重新应用**。

### 5.1 wxbot_core.py

#### 改动 1：Skills 工具调用支持

**位置**: `OpenAI_API.chat()` 方法（约第 784 行）

**改动说明**: 在 API 调用时注入 Skills 工具定义，处理 `tool_calls` 响应循环。

```python
# 原始代码
response = self.client.chat.completions.create(
    model=model, messages=messages, stream=stream,
)

# 改动后：加入 Skills 支持
from skills import get_all_tools, execute_tool
_skills_tools = get_all_tools()
_use_stream = stream if not _skills_tools else False  # 有 tools 时强制非流式

_create_kwargs = {"model": model, "messages": messages, "stream": _use_stream}
if _skills_tools:
    _create_kwargs["tools"] = _skills_tools
response = self.client.chat.completions.create(**_create_kwargs)
```

**非流式响应处理** 中增加了 tool_calls 处理：
- 检测 `message_obj.tool_calls`
- 逐个执行工具，收集结果
- 第二次调用 AI 生成最终回复

#### 改动 2：去掉 assistant 历史消息的时间戳前缀

**位置**: 所有 `chat()` 方法中构建历史消息的地方（约第 780, 1055, 1064, 1335, 1427 行）

**原因**: 原代码把时间戳 `[2026/04/16 13:44:10]` 加在 assistant 回复前面，导致 AI 模仿输出时间戳格式。

```python
# 原始
content = f"[{t}] {raw}" if t else raw

# 改动后（仅 assistant 角色）
content = raw
```

### 5.2 config/prompt/植百汇客服.md

增加了工具能力说明：

```markdown
# 工具能力
- 你可以调用工具来查询实时天气等信息
- 当工具返回了数据，必须基于工具返回的真实数据来回复用户，不要说"无法获取"
- 用自然语言总结工具数据，保持亲切的语气
```

### 5.3 定时天气播报（占位符系统）

**位置**: `wxbot_core.py` 的 `_replace_placeholders()` 方法 + `send_scheduled_msg()` 方法

**改动说明**: 在定时消息发送前，自动替换消息中的动态占位符。

#### 可用占位符

| 占位符 | 效果示例 |
|--------|---------|
| `{date}` | `2026年4月16日 星期四` |
| `{date_tomorrow}` | `2026年4月17日 星期五` |
| `{weather_brief:南京}` | `局部多云 15~17°C 当前20°C 湿度78%` |
| `{weather_tomorrow:南京}` | `4/17 零星小雨 15~23°C` |
| `{weather:南京}` | 完整多行天气（含未来预报） |

#### 定时消息模板示例

**早安播报（今天天气）** — 每天 07:30 发送：
```
☀️ {date} 天气播报
南京：{weather_brief:南京}
苏州：{weather_brief:苏州}
上海：{weather_brief:上海}
武汉：{weather_brief:武汉}
深圳：{weather_brief:深圳}
```

**晚间预报（明天天气）** — 每天 21:00 发送：
```
🌙 明日天气预报 {date_tomorrow}
南京：{weather_tomorrow:南京}
苏州：{weather_tomorrow:苏州}
上海：{weather_tomorrow:上海}
武汉：{weather_tomorrow:武汉}
深圳：{weather_tomorrow:深圳}
```

#### 配置步骤

1. 面板左侧 → 「定时消息」
2. 勾选「启用定时消息」
3. 点击「添加定时任务」
4. 填入**时间**、**目标**（群名或用户名）、**消息内容**（用上面的模板）
5. 点击「保存配置」→ 重启 Bot

---

## 六、常见问题排查

### Q1: 发送消息报 `Find Control Timeout: 发送(S)`

**原因**: wxautox4 找不到微信的发送按钮。

**排查步骤**:
1. 确认微信窗口在前台可见（不是缩到托盘）
2. 升级 wxautox4：`pip install wxautox4 --upgrade`
3. 确认微信版本在 4.1.7 ~ 4.1.8.107 之间
4. 重启微信和 Bot

### Q2: Skills 没有触发

**排查步骤**:
1. 日志中是否有 `[Skills] 已加载 Skill: xxx`
2. 确认 Skill 文件在 `skills/` 目录下，且不以 `_` 开头
3. 确认 `TOOL_DEF` 和 `execute` 都正确导出
4. 重启 Bot

### Q3: 群聊收到消息但不回复

**原因**: 群名没有加到 `config.json` 的 `group` 列表中。

```json
"group": ["群名1", "群名2"],
"group_switch": true
```

### Q4: AI 回复带时间戳前缀

**原因**: `wxbot_core.py` 中 assistant 历史消息带了时间戳。确认第五章的改动 2 已应用。

### Q5: 天气查询返回"无法获取"

**原因**: AI prompt 没有告知使用工具数据。确认 `config/prompt/植百汇客服.md` 中有"工具能力"章节。

---

## 七、运维操作

### 启动/停止

```bash
# 启动面板
cd D:\博\python\SiverWXBot_plus
python web_server.py

# 访问 http://localhost:10001
# 账号: admin / 密码: 123456
# 点击「启动机器人」/「停止机器人」
```

### 清空对话记忆

```bash
# PowerShell
Remove-Item -Recurse -Force "D:\博\python\SiverWXBot_plus\config\memory\*"
```

或在面板左侧「记忆管理」中操作。

### 升级 wxautox4

```bash
pip install wxautox4 --upgrade
# 升级后需要重启整个面板进程
```

### 添加监听用户/群

在面板中操作，或直接编辑 `config/config.json`：
- 私聊：加到 `listen_list`
- 群聊：加到 `group`

---

## 八、API 密钥信息

| 服务 | 地址 | 密钥位置 |
|------|------|---------|
| 紫喵AI（Gemini） | `newapi.aisonnet.org/v1` | `config/config.json` → `api_key` |
| 天气 API | `wttr.in`（免费） | 无需密钥 |

> ⚠️ **安全提醒**: `config/config.json` 包含 API 密钥，请勿上传到公开仓库。

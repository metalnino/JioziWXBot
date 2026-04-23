"""
天气查询 Skill
=============
使用 wttr.in 免费 API 获取实时天气信息，无需 API Key。
"""

import requests
import json

# OpenAI Function Calling 格式的工具定义
TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的实时天气预报信息，包括温度、天气状况、湿度、风速等",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如：南京、北京、上海、杭州"
                }
            },
            "required": ["city"]
        }
    }
}


def execute(args: dict) -> str:
    """
    调用 wttr.in API 获取天气数据。

    :param args: {"city": "南京"}
    :return: 格式化的天气信息字符串
    """
    city = args.get("city", "南京")

    try:
        # wttr.in JSON API
        url = f"https://wttr.in/{city}?format=j1&lang=zh"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "SiverWXBot-Skills/1.0"
        })
        resp.raise_for_status()
        data = resp.json()

        # 解析当前天气
        current = data.get("current_condition", [{}])[0]
        temp_c = current.get("temp_C", "N/A")
        feels_like = current.get("FeelsLikeC", "N/A")
        humidity = current.get("humidity", "N/A")
        wind_speed = current.get("windspeedKmph", "N/A")
        wind_dir = current.get("winddir16Point", "")
        # 中文天气描述
        desc_list = current.get("lang_zh", [])
        if desc_list:
            weather_desc = desc_list[0].get("value", "")
        else:
            weather_desc = current.get("weatherDesc", [{}])[0].get("value", "未知")
        uv_index = current.get("uvIndex", "N/A")
        visibility = current.get("visibility", "N/A")

        # 解析今天的预报（最高/最低温度）
        forecast_today = data.get("weather", [{}])[0]
        max_temp = forecast_today.get("maxtempC", "N/A")
        min_temp = forecast_today.get("mintempC", "N/A")

        # 未来几天预报
        forecast_lines = []
        for day in data.get("weather", [])[1:3]:  # 取明后天
            date = day.get("date", "")
            day_max = day.get("maxtempC", "")
            day_min = day.get("mintempC", "")
            # 取白天时段的天气描述
            hourly = day.get("hourly", [])
            if len(hourly) > 4:
                day_desc_list = hourly[4].get("lang_zh", [])
                if day_desc_list:
                    day_desc = day_desc_list[0].get("value", "")
                else:
                    day_desc = hourly[4].get("weatherDesc", [{}])[0].get("value", "")
            else:
                day_desc = ""
            forecast_lines.append(f"  {date}: {day_desc} {day_min}~{day_max}°C")

        # 组装结果
        result = (
            f"📍 {city} 实时天气\n"
            f"天气: {weather_desc}\n"
            f"温度: {temp_c}°C (体感 {feels_like}°C)\n"
            f"今日温度范围: {min_temp}~{max_temp}°C\n"
            f"湿度: {humidity}%\n"
            f"风速: {wind_speed}km/h {wind_dir}\n"
            f"紫外线指数: {uv_index}\n"
            f"能见度: {visibility}km\n"
        )

        if forecast_lines:
            result += "\n📅 未来预报:\n" + "\n".join(forecast_lines)

        return result

    except requests.exceptions.Timeout:
        return f"天气查询超时，请稍后再试"
    except requests.exceptions.RequestException as e:
        return f"天气查询失败: {str(e)}"
    except Exception as e:
        return f"天气数据解析错误: {str(e)}"


def get_brief(city: str) -> str:
    """
    获取精简版天气摘要（一行），适合定时播报。
    格式: 多云 18~25°C 湿度65%

    :param city: 城市名称
    :return: 一行天气摘要
    """
    try:
        url = f"https://wttr.in/{city}?format=j1&lang=zh"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "SiverWXBot-Skills/1.0"
        })
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current_condition", [{}])[0]
        temp_c = current.get("temp_C", "?")
        humidity = current.get("humidity", "?")

        desc_list = current.get("lang_zh", [])
        weather_desc = desc_list[0].get("value", "") if desc_list else "未知"

        forecast_today = data.get("weather", [{}])[0]
        max_temp = forecast_today.get("maxtempC", "?")
        min_temp = forecast_today.get("mintempC", "?")

        return f"{weather_desc} {min_temp}~{max_temp}°C 当前{temp_c}°C 湿度{humidity}%"

    except Exception:
        return "天气获取失败"


def get_tomorrow(city: str) -> str:
    """
    获取明天的天气预报（一行），适合头天晚上播报。
    格式: 4/17 多云 15~23°C

    :param city: 城市名称
    :return: 一行明日天气
    """
    try:
        url = f"https://wttr.in/{city}?format=j1&lang=zh"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "SiverWXBot-Skills/1.0"
        })
        resp.raise_for_status()
        data = resp.json()

        weather_list = data.get("weather", [])
        if len(weather_list) < 2:
            return "明日预报暂无"

        tomorrow = weather_list[1]
        date = tomorrow.get("date", "")  # 2026-04-17
        max_temp = tomorrow.get("maxtempC", "?")
        min_temp = tomorrow.get("mintempC", "?")

        # 取白天时段天气描述
        hourly = tomorrow.get("hourly", [])
        if len(hourly) > 4:
            desc_list = hourly[4].get("lang_zh", [])
            desc = desc_list[0].get("value", "") if desc_list else "未知"
        else:
            desc = "未知"

        # 格式化日期 2026-04-17 → 4/17
        parts = date.split("-")
        short_date = f"{int(parts[1])}/{int(parts[2])}" if len(parts) == 3 else date

        return f"{short_date} {desc} {min_temp}~{max_temp}°C"

    except Exception:
        return "明日天气获取失败"

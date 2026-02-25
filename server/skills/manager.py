"""
Skill Manager - 技能管理器

处理各种技能的调用，如天气查询、网页总结等
"""

import re
import asyncio
import aiohttp
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SkillManager:
    """技能管理器"""

    # 技能触发模式
    WEATHER_PATTERNS = [
        r"天气怎么样",
        r"今天天气",
        r"明天天气",
        r"天气(.*)",
        r"(.*)天气",
    ]

    SUMMARIZE_PATTERNS = [
        r"总结(.*)",
        r" summariz(?:e|ing)(.*)",
        r"这个网页(.*)",
    ]

    def __init__(self):
        self.enabled = True

    async def handle_skill(self, text: str) -> Optional[str]:
        """
        处理技能调用

        Args:
            text: 用户输入文本

        Returns:
            技能响应文本，如果不匹配任何技能返回 None
        """
        # 检查天气技能
        weather_result = await self._handle_weather(text)
        if weather_result:
            return weather_result

        # 检查总结技能
        summarize_result = await self._handle_summarize(text)
        if summarize_result:
            return summarize_result

        return None

    async def _handle_weather(self, text: str) -> Optional[str]:
        """处理天气查询"""
        # 检查是否匹配天气模式
        is_weather_query = any(
            re.search(pattern, text) for pattern in self.WEATHER_PATTERNS
        )

        if not is_weather_query:
            return None

        # 提取城市名
        city = self._extract_city(text)

        if not city:
            # 尝试直接问用户要查询的城市
            return "请告诉我你想查询哪个城市的天气？"

        try:
            return await self._get_weather(city)
        except Exception as e:
            logger.error(f"Weather skill error: {e}")
            return f"抱歉，获取天气信息失败了。"

    def _extract_city(self, text: str) -> Optional[str]:
        """从文本中提取城市名"""
        # 常见城市列表
        common_cities = [
            "北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "重庆",
            "武汉", "西安", "苏州", "天津", "长沙", "郑州", "济南", "青岛",
            "大连", "沈阳", "哈尔滨", "长春", "福州", "厦门", "南昌", "合肥",
            "昆明", "兰州", "石家庄", "太原", "呼和浩特", "南宁", "贵阳",
            "海口", "拉萨", "乌鲁木齐", "银川", "西宁", "香港", "澳门", "台北",
        ]

        # 直接匹配城市名
        for city in common_cities:
            if city in text:
                return city

        # 尝试提取"天气"前面的词
        match = re.search(r"(.{2,4})天气", text)
        if match:
            return match.group(1)

        return None

    async def _get_weather(self, city: str) -> str:
        """获取天气信息"""
        # 使用 wttr.in API
        url = f"https://wttr.in/{city}?format=%l:+%c+%t+湿度%h+风速%w"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    result = await resp.text()
                    # 格式化结果
                    result = result.strip()
                    # 转换温度格式
                    result = result.replace("+", "")
                    return result
                else:
                    return f"抱歉，未能找到{city}的天气信息。"

    async def _handle_summarize(self, text: str) -> Optional[str]:
        """处理网页总结"""
        # 检查是否匹配总结模式
        is_summarize_query = any(
            re.search(pattern, text, re.IGNORECASE) for pattern in self.SUMMARIZE_PATTERNS
        )

        if not is_summarize_query:
            return None

        # 提取 URL
        url = self._extract_url(text)

        if not url:
            return "请告诉我你想要总结的网页链接？"

        try:
            return await self._summarize_url(url)
        except Exception as e:
            logger.error(f"Summarize skill error: {e}")
            return f"抱歉，总结网页失败了。"

    def _extract_url(self, text: str) -> Optional[str]:
        """从文本中提取 URL"""
        url_pattern = r"https?://[^\s]+"
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        return None

    async def _summarize_url(self, url: str) -> str:
        """总结网页内容"""
        # 使用麋鹿(阅读助手) API 或其他免费方案
        # 这里使用 jina.ai 的 Reader API
        try:
            # 先获取网页内容
            async with aiohttp.ClientSession() as session:
                # 使用 jina.ai Reader API
                reader_url = f"https://r.jina.ai/{url}"
                async with session.get(reader_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        content = await resp.text()

                        # 如果内容太长，截取前面部分
                        max_length = 2000
                        if len(content) > max_length:
                            content = content[:max_length] + "..."

                        return f"网页内容摘要：\n{content}"
                    else:
                        return f"抱歉，无法获取该网页内容。"
        except Exception as e:
            logger.error(f"Summarize error: {e}")
            return f"抱歉，总结失败：{str(e)}"


# 全局技能管理器实例
_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """获取技能管理器实例"""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager

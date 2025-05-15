import requests
import re
import json
import os
import tomllib
import traceback
import subprocess
import base64
import shutil
import random
from pathlib import Path
from urllib.parse import urlparse
import time
import aiohttp
from datetime import datetime
from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase

# Base URLs for API services
BASE_URL_VVHAN = "https://api.vvhan.com/api/"
BASE_URL_ALAPI = "https://v3.alapi.cn/api/"

# Zodiac sign mapping
ZODIAC_MAPPING = {
    "白羊座": "aries",
    "金牛座": "taurus",
    "双子座": "gemini",
    "巨蟹座": "cancer",
    "狮子座": "leo",
    "处女座": "virgo",
    "天秤座": "libra",
    "天蝎座": "scorpio",
    "射手座": "sagittarius",
    "摩羯座": "capricorn",
    "水瓶座": "aquarius",
    "双鱼座": "pisces"
}

# Hitokoto type dictionary
hitokoto_type_dict = {
    'a': '动画',
    'b': '漫画',
    'c': '游戏',
    'd': '文学',
    'e': '原创',
    'f': '来自网络',
    'g': '其他',
    'h': '影视',
    'i': '诗词',
    'j': '网易云',
    'k': '哲学',
    'l': '抖机灵'
}


class Apilot(PluginBase):
    description = "从DOW迁移到XXX平台的插件"
    author = "sofs2005"
    version = "2.0.0"

    def __init__(self):
        super().__init__()
        try:
            # Load configuration from TOML file
            config_path = os.path.join(os.path.dirname(__file__), "config.toml")
            try:
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)

                # Read basic configuration
                basic_config = config.get("basic", {})
                self.enable = basic_config.get("enable", True)  # Default to True
                self.alapi_token = basic_config.get("alapi_token", None)
                self.morning_news_text_enabled = basic_config.get("morning_news_text_enabled", False)

                # Read trigger patterns
                triggers_config = config.get("triggers", {})
                self.weather_pattern = triggers_config.get("weather_pattern", '^(?:(.{2,7}?)(?:市|县|区|镇)?|(\d{7,9}))(:?今天|明天|后天|7天|七天)?(?:的)?天气$')
                self.horoscope_pattern = triggers_config.get("horoscope_pattern", '^([\u4e00-\u9fa5]{2}座)$')
                self.news_pattern = triggers_config.get("news_pattern", '^(.*?)新闻$')
                self.history_pattern = triggers_config.get("history_pattern", '^历史上的今天(\d+)月(\d+)日')
                self.hot_trend_pattern = triggers_config.get("hot_trend_pattern", '(.{1,6})热榜$')
                self.hitokoto_trigger = triggers_config.get("hitokoto_trigger", '一言')
                self.dujitang_trigger = triggers_config.get("dujitang_trigger", '毒鸡汤')
                self.dog_diary_trigger = triggers_config.get("dog_diary_trigger", '舔狗')
                self.morning_news_trigger = triggers_config.get("morning_news_trigger", '早报')
                self.moyu_trigger = triggers_config.get("moyu_trigger", '摸鱼')
                self.moyu_video_trigger = triggers_config.get("moyu_video_trigger", '摸鱼视频')
                self.bagua_trigger = triggers_config.get("bagua_trigger", '八卦')
                self.bstp_trigger = triggers_config.get("bstp_trigger", '白丝图片')
                self.hstp_trigger = triggers_config.get("hstp_trigger", '黑丝图片')
                self.xjjsp_trigger = triggers_config.get("xjjsp_trigger", '小姐姐视频')
                self.yzsp_trigger = triggers_config.get("yzsp_trigger", '玉足视频')
                self.hssp_trigger = triggers_config.get("hssp_trigger", '黑丝视频')
                self.cos_trigger = triggers_config.get("cos_trigger", 'cos视频')
                self.ddsp_trigger = triggers_config.get("ddsp_trigger", '吊带视频')
                self.jksp_trigger = triggers_config.get("jksp_trigger", 'JK视频')
                self.llsp_trigger = triggers_config.get("llsp_trigger", '萝莉视频')

                # Read API URLs
                apis_config = config.get("apis", {})
                self.bagua_api_url = apis_config.get("bagua_api_url", "https://dayu.qqsuu.cn/mingxingbagua/apis.php")
                self.moyu_video_api_url = apis_config.get("moyu_video_api_url", "https://api.vvhan.com/api/360wallpaper")
                self.bstp_api_url = apis_config.get("bstp_api_url", "https://api.xlb.one/api/baisi")
                self.hstp_api_url = apis_config.get("hstp_api_url", "https://api.xlb.one/api/heisi")
                self.xjjsp_api_url = apis_config.get("xjjsp_api_url", "https://api.yujn.cn/api/zzxjj.php")
                self.yzsp_api_url = apis_config.get("yzsp_api_url", "https://api.yujn.cn/api/yuzu.php")
                self.hssp_api_url = apis_config.get("hssp_api_url", "https://api.yujn.cn/api/heisi.php")
                self.cos_api_url = apis_config.get("cos_api_url", "https://api.yujn.cn/api/cos.php")
                self.ddsp_api_url = apis_config.get("ddsp_api_url", "https://api.yujn.cn/api/diaodai.php")
                self.jksp_api_url = apis_config.get("jksp_api_url", "https://api.yujn.cn/api/jk.php")
                self.llsp_api_url = apis_config.get("llsp_api_url", "https://api.yujn.cn/api/luoli.php")

                # Important: Set self.enabled to True for the plugin system
                self.enabled = True

                if not self.alapi_token:
                    logger.warning("[Apilot] initialized but alapi_token not found in config")
                else:
                    logger.info("[Apilot] initialized and alapi_token loaded successfully")

                # Initialize condition_2_and_3_cities for weather queries
                self.condition_2_and_3_cities = None

                logger.info("[Apilot] Plugin initialized successfully")

            except Exception as e:
                logger.error(f"[Apilot] Failed to load config: {str(e)}")
                self.enable = False
                self.enabled = False  # Also set system property
                self.alapi_token = None
                self.morning_news_text_enabled = False

        except Exception as e:
            logger.error(f"[Apilot] Initialization failed: {str(e)}")
            self.enable = False
            self.enabled = False  # Also set system property

    @on_text_message(priority=99)  # Increase priority to highest
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        """Handle text messages"""
        # Log that the handler was called
        logger.info(f"[Apilot] handle_text called with message: {message.get('Content', '')[:20]}...")
        logger.info(f"[Apilot] Plugin state: enabled={self.enabled}, enable={self.enable}")

        # Check both system enabled state and config enabled state
        if not hasattr(self, 'enabled') or not self.enabled or not self.enable:
            logger.warning("[Apilot] Plugin is disabled, skipping message processing")
            return True  # Allow other plugins to process

        content = message["Content"].strip()
        from_wxid = message["FromWxid"]
        logger.info(f"[Apilot] Processing text message: {content}")

        # Handle news query
        news_match = re.match(self.news_pattern, content)
        if news_match or content == "新闻":
            logger.info(f"[Apilot] Matched news query: {content}")
            news_type = news_match.group(1) if news_match and news_match.group(1) else "综合"
            news_content = self.get_netease_news(self.alapi_token, news_type)
            await bot.send_text_message(from_wxid, news_content)
            return False  # Block other plugins from processing

        # Handle hitokoto (一言)
        if content == self.hitokoto_trigger:
            logger.info(f"[Apilot] Matched hitokoto query: {content}")
            hitokoto = self.get_hitokoto(self.alapi_token)
            await bot.send_text_message(from_wxid, hitokoto)
            return False  # Block other plugins from processing

        # Handle horoscope query
        horoscope_match = re.match(self.horoscope_pattern, content)
        if horoscope_match:
            logger.info(f"[Apilot] Matched horoscope query: {content}")
            if content in ZODIAC_MAPPING:
                zodiac_english = ZODIAC_MAPPING[content]
                horoscope_content = self.get_horoscope(self.alapi_token, zodiac_english)
                await bot.send_text_message(from_wxid, horoscope_content)
            else:
                await bot.send_text_message(from_wxid, "请重新输入星座名称")
            return False  # Block other plugins from processing

        # Handle weather query
        weather_match = re.match(self.weather_pattern, content)
        if weather_match:
            logger.info(f"[Apilot] Matched weather query: {content}")
            city_or_id = weather_match.group(1) or weather_match.group(2)
            date = weather_match.group(3)
            if not self.alapi_token:
                await bot.send_text_message(from_wxid, "请先配置alapi的token")
            else:
                weather_content = self.get_weather(self.alapi_token, city_or_id, date, content)
                await bot.send_text_message(from_wxid, weather_content)
            return False  # Block other plugins from processing

        # Handle 毒鸡汤
        if content == self.dujitang_trigger:
            logger.info(f"[Apilot] Matched dujitang query: {content}")
            dujitang_content = self.get_soul_dujitang(self.alapi_token)
            await bot.send_text_message(from_wxid, dujitang_content)
            return False  # Block other plugins from processing

        # Handle 舔狗日记
        if content == self.dog_diary_trigger:
            logger.info(f"[Apilot] Matched dog diary query: {content}")
            dog_diary_content = self.get_dog_diary(self.alapi_token)
            await bot.send_text_message(from_wxid, dog_diary_content)
            return False  # Block other plugins from processing

        # Handle 历史上的今天
        history_match = re.match(self.history_pattern, content)
        if content == "历史上的今天" or history_match:
            logger.info(f"[Apilot] Matched history query: {content}")
            month, day = '', ''
            if history_match:
                month, day = history_match.group(1), history_match.group(2)
            history_content = self.get_today_on_history(self.alapi_token, month, day)
            await bot.send_text_message(from_wxid, history_content)
            return False  # Block other plugins from processing

        # Handle 早报
        if content == self.morning_news_trigger:
            logger.info(f"[Apilot] Matched morning news query: {content}")
            morning_news = await self.get_morning_news(self.alapi_token, self.morning_news_text_enabled)
            # 检查返回的是图片字节还是URL或文本
            if isinstance(morning_news, bytes):
                logger.info(f"[Apilot] Sending morning news as image bytes, size: {len(morning_news)} bytes")
                await bot.send_image_message(from_wxid, morning_news)
            elif self.is_valid_url(morning_news):
                # 如果是URL，发送图片
                logger.info(f"[Apilot] Sending morning news as image URL: {morning_news}")
                await bot.send_image_message(from_wxid, morning_news)
            else:
                # 否则发送文本
                logger.info(f"[Apilot] Sending morning news as text")
                await bot.send_text_message(from_wxid, morning_news)
            return False  # Block other plugins from processing

        # Handle 摸鱼
        if content == self.moyu_trigger:
            logger.info(f"[Apilot] Matched moyu query: {content}")
            moyu_calendar = await self.get_moyu_calendar()
            # 检查返回的是图片字节还是URL或错误消息
            if isinstance(moyu_calendar, bytes):
                logger.info(f"[Apilot] Sending moyu calendar as image bytes, size: {len(moyu_calendar)} bytes")
                await bot.send_image_message(from_wxid, moyu_calendar)
            elif self.is_valid_url(moyu_calendar):
                logger.info(f"[Apilot] Sending moyu calendar as image URL: {moyu_calendar}")
                await bot.send_image_message(from_wxid, moyu_calendar)
            else:
                logger.info(f"[Apilot] Sending moyu calendar as text: {moyu_calendar}")
                await bot.send_text_message(from_wxid, moyu_calendar)
            return False  # Block other plugins from processing

        # Handle 摸鱼视频
        if content == self.moyu_video_trigger:
            logger.info(f"[Apilot] Matched moyu video query: {content}")
            moyu_video = await self.get_moyu_calendar_video()
            # 检查返回的是视频字节还是URL或错误消息
            if isinstance(moyu_video, bytes):
                logger.info(f"[Apilot] Sending moyu video as video bytes, size: {len(moyu_video)} bytes")
                await bot.send_video_message(from_wxid, moyu_video)
            elif self.is_valid_url(moyu_video):
                logger.info(f"[Apilot] Sending moyu video as video card: {moyu_video}")
                # 发送视频卡片
                title = "摸鱼视频"
                description = "今日摸鱼视频，快来摸鱼吧"
                success = await self.send_video_card(bot, from_wxid, moyu_video, title, description)
                if not success:
                    # 如果发送卡片失败，回退到直接发送视频
                    logger.info(f"[Apilot] Falling back to direct video URL: {moyu_video}")
                    await bot.send_video_message(from_wxid, moyu_video)
            else:
                logger.info(f"[Apilot] Sending moyu video as text: {moyu_video}")
                await bot.send_text_message(from_wxid, moyu_video)
            return False  # Block other plugins from processing

        # Handle 八卦
        if content == self.bagua_trigger:
            logger.info(f"[Apilot] Matched bagua query: {content}")
            bagua = await self.get_mx_bagua()
            # 检查返回的是图片字节还是URL或错误消息
            if isinstance(bagua, bytes):
                logger.info(f"[Apilot] Sending bagua as image bytes, size: {len(bagua)} bytes")
                await bot.send_image_message(from_wxid, bagua)
            elif self.is_valid_url(bagua):
                logger.info(f"[Apilot] Sending bagua as image URL: {bagua}")
                await bot.send_image_message(from_wxid, bagua)
            else:
                logger.info(f"[Apilot] Sending bagua as text: {bagua}")
                await bot.send_text_message(from_wxid, bagua)
            return False  # Block other plugins from processing

        # Handle 白丝图片
        if content == self.bstp_trigger:
            logger.info(f"[Apilot] Matched bstp query: {content}")
            bstp = await self.get_mx_bstp()
            # 检查返回的是图片字节还是URL或错误消息
            if isinstance(bstp, bytes):
                logger.info(f"[Apilot] Sending bstp as image bytes, size: {len(bstp)} bytes")
                await bot.send_image_message(from_wxid, bstp)
            elif self.is_valid_url(bstp):
                logger.info(f"[Apilot] Sending bstp as image URL: {bstp}")
                await bot.send_image_message(from_wxid, bstp)
            else:
                logger.info(f"[Apilot] Sending bstp as text: {bstp}")
                await bot.send_text_message(from_wxid, bstp)
            return False  # Block other plugins from processing

        # Handle 黑丝图片
        if content == self.hstp_trigger:
            logger.info(f"[Apilot] Matched hstp query: {content}")
            hstp = await self.get_mx_hstp()
            # 检查返回的是图片字节还是URL或错误消息
            if isinstance(hstp, bytes):
                logger.info(f"[Apilot] Sending hstp as image bytes, size: {len(hstp)} bytes")
                await bot.send_image_message(from_wxid, hstp)
            elif self.is_valid_url(hstp):
                logger.info(f"[Apilot] Sending hstp as image URL: {hstp}")
                await bot.send_image_message(from_wxid, hstp)
            else:
                logger.info(f"[Apilot] Sending hstp as text: {hstp}")
                await bot.send_text_message(from_wxid, hstp)
            return False  # Block other plugins from processing

        # Handle 小姐姐视频
        if content == self.xjjsp_trigger:
            logger.info(f"[Apilot] Matched xjjsp query: {content}")
            xjjsp = await self.get_xjjsp()
            # 检查返回的是视频字典、URL还是错误消息
            if isinstance(xjjsp, dict) and "video" in xjjsp:
                video_data = xjjsp["video"]
                cover_data = xjjsp.get("cover")

                # 使用与VideoDemand插件相同的参数格式
                logger.info(f"[Apilot] Sending xjjsp as video base64, video size: {len(video_data)} characters, cover size: {len(cover_data) if cover_data else 0} characters")
                # 发送视频消息 - 使用与VideoSender相同的参数格式
                client_msg_id, new_msg_id = await bot.send_video_message(
                    from_wxid,
                    video=video_data,
                    image=cover_data or "None"  # 使用字符串"None"与VideoSender保持一致
                )
                logger.info(f"[Apilot] Video sent successfully: client_msg_id={client_msg_id}, new_msg_id={new_msg_id}")
            elif self.is_valid_url(xjjsp):
                logger.info(f"[Apilot] Sending xjjsp as video card: {xjjsp}")
                # 发送视频卡片
                title = "小姐姐视频"
                description = "随机小姐姐视频，请欣赏"
                success = await self.send_video_card(bot, from_wxid, xjjsp, title, description)
                if not success:
                    # 如果发送卡片失败，回退到直接发送视频
                    logger.info(f"[Apilot] Falling back to direct video URL: {xjjsp}")
                    await bot.send_video_message(from_wxid, xjjsp)
            else:
                logger.info(f"[Apilot] Sending xjjsp as text: {xjjsp}")
                await bot.send_text_message(from_wxid, xjjsp)
            return False  # Block other plugins from processing

        # Handle 玉足视频
        if content == self.yzsp_trigger:
            logger.info(f"[Apilot] Matched yzsp query: {content}")
            yzsp = await self.get_yzsp()
            # 检查返回的是视频字典、URL还是错误消息
            if isinstance(yzsp, dict) and "video" in yzsp:
                video_data = yzsp["video"]
                cover_data = yzsp.get("cover")

                # 使用与VideoDemand插件相同的参数格式
                logger.info(f"[Apilot] Sending yzsp as video base64, video size: {len(video_data)} characters, cover size: {len(cover_data) if cover_data else 0} characters")
                # 发送视频消息 - 使用与VideoSender相同的参数格式
                client_msg_id, new_msg_id = await bot.send_video_message(
                    from_wxid,
                    video=video_data,
                    image=cover_data or "None"  # 使用字符串"None"与VideoSender保持一致
                )
                logger.info(f"[Apilot] Video sent successfully: client_msg_id={client_msg_id}, new_msg_id={new_msg_id}")
            elif self.is_valid_url(yzsp):
                logger.info(f"[Apilot] Sending yzsp as video card: {yzsp}")
                # 发送视频卡片
                title = "玉足视频"
                description = "随机玉足视频，请欣赏"
                success = await self.send_video_card(bot, from_wxid, yzsp, title, description)
                if not success:
                    # 如果发送卡片失败，回退到直接发送视频
                    logger.info(f"[Apilot] Falling back to direct video URL: {yzsp}")
                    await bot.send_video_message(from_wxid, yzsp)
            else:
                logger.info(f"[Apilot] Sending yzsp as text: {yzsp}")
                await bot.send_text_message(from_wxid, yzsp)
            return False  # Block other plugins from processing

        # Handle 黑丝视频
        if content == self.hssp_trigger:
            logger.info(f"[Apilot] Matched hssp query: {content}")
            hssp = await self.get_hssp()
            # 检查返回的是视频字典、URL还是错误消息
            if isinstance(hssp, dict) and "video" in hssp:
                video_data = hssp["video"]
                cover_data = hssp.get("cover")

                # 使用与VideoDemand插件相同的参数格式
                logger.info(f"[Apilot] Sending hssp as video base64, video size: {len(video_data)} characters, cover size: {len(cover_data) if cover_data else 0} characters")
                # 发送视频消息 - 使用与VideoSender相同的参数格式
                client_msg_id, new_msg_id = await bot.send_video_message(
                    from_wxid,
                    video=video_data,
                    image=cover_data or "None"  # 使用字符串"None"与VideoSender保持一致
                )
                logger.info(f"[Apilot] Video sent successfully: client_msg_id={client_msg_id}, new_msg_id={new_msg_id}")
            elif self.is_valid_url(hssp):
                logger.info(f"[Apilot] Sending hssp as video card: {hssp}")
                # 发送视频卡片
                title = "黑丝视频"
                description = "随机黑丝视频，请欣赏"
                success = await self.send_video_card(bot, from_wxid, hssp, title, description)
                if not success:
                    # 如果发送卡片失败，回退到直接发送视频
                    logger.info(f"[Apilot] Falling back to direct video URL: {hssp}")
                    await bot.send_video_message(from_wxid, hssp)
            else:
                logger.info(f"[Apilot] Sending hssp as text: {hssp}")
                await bot.send_text_message(from_wxid, hssp)
            return False  # Block other plugins from processing

        # Handle cos视频
        if content == self.cos_trigger:
            logger.info(f"[Apilot] Matched cos query: {content}")
            cos = await self.get_cos()
            # 检查返回的是视频字典、URL还是错误消息
            if isinstance(cos, dict) and "video" in cos:
                video_data = cos["video"]
                cover_data = cos.get("cover")

                # 使用与VideoDemand插件相同的参数格式
                logger.info(f"[Apilot] Sending cos as video base64, video size: {len(video_data)} characters, cover size: {len(cover_data) if cover_data else 0} characters")
                # 发送视频消息 - 使用与VideoSender相同的参数格式
                client_msg_id, new_msg_id = await bot.send_video_message(
                    from_wxid,
                    video=video_data,
                    image=cover_data or "None"  # 使用字符串"None"与VideoSender保持一致
                )
                logger.info(f"[Apilot] Video sent successfully: client_msg_id={client_msg_id}, new_msg_id={new_msg_id}")
            elif self.is_valid_url(cos):
                logger.info(f"[Apilot] Sending cos as video card: {cos}")
                # 发送视频卡片
                title = "COS视频"
                description = "随机COS视频，请欣赏"
                success = await self.send_video_card(bot, from_wxid, cos, title, description)
                if not success:
                    # 如果发送卡片失败，回退到直接发送视频
                    logger.info(f"[Apilot] Falling back to direct video URL: {cos}")
                    await bot.send_video_message(from_wxid, cos)
            else:
                logger.info(f"[Apilot] Sending cos as text: {cos}")
                await bot.send_text_message(from_wxid, cos)
            return False  # Block other plugins from processing

        # Handle 吊带视频
        if content == self.ddsp_trigger:
            logger.info(f"[Apilot] Matched ddsp query: {content}")
            ddsp = await self.get_ddsp()
            # 检查返回的是视频字典、URL还是错误消息
            if isinstance(ddsp, dict) and "video" in ddsp:
                video_data = ddsp["video"]
                cover_data = ddsp.get("cover")

                # 使用与VideoDemand插件相同的参数格式
                logger.info(f"[Apilot] Sending ddsp as video base64, video size: {len(video_data)} characters, cover size: {len(cover_data) if cover_data else 0} characters")
                # 发送视频消息 - 使用与VideoSender相同的参数格式
                client_msg_id, new_msg_id = await bot.send_video_message(
                    from_wxid,
                    video=video_data,
                    image=cover_data or "None"  # 使用字符串"None"与VideoSender保持一致
                )
                logger.info(f"[Apilot] Video sent successfully: client_msg_id={client_msg_id}, new_msg_id={new_msg_id}")
            elif self.is_valid_url(ddsp):
                logger.info(f"[Apilot] Sending ddsp as video card: {ddsp}")
                # 发送视频卡片
                title = "吊带视频"
                description = "随机吊带视频，请欣赏"
                success = await self.send_video_card(bot, from_wxid, ddsp, title, description)
                if not success:
                    # 如果发送卡片失败，回退到直接发送视频
                    logger.info(f"[Apilot] Falling back to direct video URL: {ddsp}")
                    await bot.send_video_message(from_wxid, ddsp)
            else:
                logger.info(f"[Apilot] Sending ddsp as text: {ddsp}")
                await bot.send_text_message(from_wxid, ddsp)
            return False  # Block other plugins from processing

        # Handle JK视频
        if content == self.jksp_trigger:
            logger.info(f"[Apilot] Matched jksp query: {content}")
            jksp = await self.get_jksp()
            # 检查返回的是视频字典、URL还是错误消息
            if isinstance(jksp, dict) and "video" in jksp:
                video_data = jksp["video"]
                cover_data = jksp.get("cover")

                # 使用与VideoDemand插件相同的参数格式
                logger.info(f"[Apilot] Sending jksp as video base64, video size: {len(video_data)} characters, cover size: {len(cover_data) if cover_data else 0} characters")
                # 发送视频消息 - 使用与VideoSender相同的参数格式
                client_msg_id, new_msg_id = await bot.send_video_message(
                    from_wxid,
                    video=video_data,
                    image=cover_data or "None"  # 使用字符串"None"与VideoSender保持一致
                )
                logger.info(f"[Apilot] Video sent successfully: client_msg_id={client_msg_id}, new_msg_id={new_msg_id}")
            elif self.is_valid_url(jksp):
                logger.info(f"[Apilot] Sending jksp as video card: {jksp}")
                # 发送视频卡片
                title = "JK视频"
                description = "随机JK视频，请欣赏"
                success = await self.send_video_card(bot, from_wxid, jksp, title, description)
                if not success:
                    # 如果发送卡片失败，回退到直接发送视频
                    logger.info(f"[Apilot] Falling back to direct video URL: {jksp}")
                    await bot.send_video_message(from_wxid, jksp)
            else:
                logger.info(f"[Apilot] Sending jksp as text: {jksp}")
                await bot.send_text_message(from_wxid, jksp)
            return False  # Block other plugins from processing

        # Handle 萝莉视频
        if content == self.llsp_trigger:
            logger.info(f"[Apilot] Matched llsp query: {content}")
            llsp = await self.get_llsp()
            # 检查返回的是视频字典、URL还是错误消息
            if isinstance(llsp, dict) and "video" in llsp:
                video_data = llsp["video"]
                cover_data = llsp.get("cover")

                # 使用与VideoDemand插件相同的参数格式
                logger.info(f"[Apilot] Sending llsp as video base64, video size: {len(video_data)} characters, cover size: {len(cover_data) if cover_data else 0} characters")
                # 发送视频消息 - 使用与VideoSender相同的参数格式
                client_msg_id, new_msg_id = await bot.send_video_message(
                    from_wxid,
                    video=video_data,
                    image=cover_data or "None"  # 使用字符串"None"与VideoSender保持一致
                )
                logger.info(f"[Apilot] Video sent successfully: client_msg_id={client_msg_id}, new_msg_id={new_msg_id}")
            elif self.is_valid_url(llsp):
                logger.info(f"[Apilot] Sending llsp as video card: {llsp}")
                # 发送视频卡片
                title = "萝莉视频"
                description = "随机萝莉视频，请欣赏"
                success = await self.send_video_card(bot, from_wxid, llsp, title, description)
                if not success:
                    # 如果发送卡片失败，回退到直接发送视频
                    logger.info(f"[Apilot] Falling back to direct video URL: {llsp}")
                    await bot.send_video_message(from_wxid, llsp)
            else:
                logger.info(f"[Apilot] Sending llsp as text: {llsp}")
                await bot.send_text_message(from_wxid, llsp)
            return False  # Block other plugins from processing

        # Handle 热榜
        hot_trend_match = re.match(self.hot_trend_pattern, content)
        if hot_trend_match:
            logger.info(f"[Apilot] Matched hot trend query: {content}")
            hot_trends_type = hot_trend_match.group(1).strip()  # 提取匹配的组并去掉可能的空格
            hot_trends_content = self.get_hot_trends(hot_trends_type)
            await bot.send_text_message(from_wxid, hot_trends_content)
            return False  # Block other plugins from processing

        # Allow other plugins to process if no match
        logger.info("[Apilot] No match found for message, allowing other plugins to process")
        return True

    def get_help_text(self, verbose=False):
        """Return help text for the plugin"""
        short_help_text = " 发送特定指令以获取早报、热榜、查询天气、星座运势等！"

        if not verbose:
            return short_help_text

        help_text = "📚 发送关键词获取特定信息！\n"

        # 娱乐和信息类
        help_text += "\n🎉 娱乐与资讯：\n"
        help_text += '  🌅 早报: 发送"早报"获取早报。\n'
        help_text += '  🐟 摸鱼: 发送"摸鱼"获取摸鱼人日历。\n'
        help_text += '  🔥 热榜: 发送"xx热榜"查看支持的热榜。\n'
        help_text += '  🔥 八卦: 发送"八卦"获取明星八卦。\n'
        help_text += '  📰 新闻: 发送"新闻"或"xx新闻"获取网易头条。\n'
        help_text += '  ☠️ 心灵毒鸡汤: 发送"毒鸡汤"获取心灵毒鸡汤。\n'
        help_text += '  ☃️ 历史上的今天: 发送"历史上的今天"or"历史上的今天x月x日"获取历史事件\n'
        help_text += '  🐕‍🦺 舔狗日记: 发送"舔狗"获取舔狗日记\n'
        help_text += '  🎞️ Hitokoto一言: 发送"一言"获取Hitokoto一言\n'
        help_text += '  📸 图片: 发送"白丝图片"、"黑丝图片"等获取相关图片\n'
        help_text += '  🎬 视频: 发送"小姐姐视频"、"玉足视频"、"黑丝视频"、"cos视频"、"吊带视频"、"JK视频"、"萝莉视频"等获取相关视频\n'

        # 查询类
        help_text += "\n🔍 查询工具：\n"
        help_text += '  🌦️ 天气: 发送"城市+天气"查天气，如"北京天气"。\n'
        help_text += '  🌌 星座: 发送星座名称查看今日运势，如"白羊座"。\n'

        return help_text

    def get_hitokoto(self, alapi_token):
        """Get a random Hitokoto quote"""
        logger.info("[Apilot] Getting hitokoto")
        url = BASE_URL_ALAPI + "hitokoto"
        hitokoto_type = 'abcdefghijkl'
        random_type = random.randint(0, len(hitokoto_type) - 1)
        payload = {
            "token": alapi_token,
            "type": hitokoto_type[random_type]
        }
        headers = {"Content-Type": "application/json"}
        try:
            logger.info(f"[Apilot] Making hitokoto request to {url}")
            hitokoto_data = self.make_request(url, method="POST", headers=headers, json_data=payload)
            logger.info(f"[Apilot] Hitokoto API response: {hitokoto_data}")

            if isinstance(hitokoto_data, dict) and hitokoto_data.get("code") == 200:
                data = hitokoto_data.get("data", {})
                if not isinstance(data, dict):
                    logger.error(f"[Apilot] Hitokoto data is not a dictionary: {data}")
                    return "一言获取失败，请稍后再试"

                format_data = (
                    f"【Hitokoto一言】\n"
                    f"🎆{data.get('hitokoto', '未知')}\n"
                    f"🎐type: {hitokoto_type_dict.get(hitokoto_type[random_type], '未知')}\n"
                    f"🥷author: {data.get('from', '未知')}"
                )
                return format_data
            else:
                error_msg = "一言获取失败，请稍后再试"
                if isinstance(hitokoto_data, dict) and "error" in hitokoto_data:
                    error_msg += f"（{hitokoto_data['error']}）"
                logger.error(f"[Apilot] Hitokoto API error: {hitokoto_data}")
                return error_msg
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_hitokoto: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取一言时出错: {str(e)}"

    def get_horoscope(self, alapi_token, zodiac_english):
        """Get horoscope information for a zodiac sign"""
        logger.info(f"[Apilot] Getting horoscope for zodiac: {zodiac_english}")
        url = BASE_URL_ALAPI + "star"
        payload = {
            "token": alapi_token,
            "star": zodiac_english
        }
        headers = {"Content-Type": "application/json"}
        try:
            logger.info(f"[Apilot] Making horoscope request to {url}")
            horoscope_data = self.make_request(url, method="POST", headers=headers, json_data=payload)
            logger.info(f"[Apilot] Horoscope API response: {horoscope_data}")

            if isinstance(horoscope_data, dict) and horoscope_data.get("code") == 200:
                data = horoscope_data.get("data", {})
                logger.info(f"[Apilot] Horoscope data: {data}")

                if not isinstance(data, dict):
                    logger.error(f"[Apilot] Horoscope data is not a dictionary: {data}")
                    return "星座信息格式错误，请稍后再试"

                result = (
                    f"📅 日期：{data.get('date', '未知')}\n\n"
                    f"💡【每日建议】\n宜：{data.get('yi', '未知')}\n忌：{data.get('ji', '未知')}\n\n"
                    f"📊【运势指数】\n"
                    f"总运势：{data.get('all', '未知')}\n"
                    f"爱情：{data.get('love', '未知')}\n"
                    f"工作：{data.get('work', '未知')}\n"
                    f"财运：{data.get('money', '未知')}\n"
                    f"健康：{data.get('health', '未知')}\n\n"
                    f"🔔【提醒】：{data.get('notice', '无提醒')}\n\n"
                    f"🍀【幸运提示】\n数字：{data.get('lucky_number', '未知')}\n"
                    f"颜色：{data.get('lucky_color', '未知')}\n"
                    f"星座：{data.get('lucky_star', '未知')}\n\n"
                    f"✍【简评】\n总运：{data.get('all_text', '未知')}\n"
                    f"爱情：{data.get('love_text', '未知')}\n"
                    f"工作：{data.get('work_text', '未知')}\n"
                    f"财运：{data.get('money_text', '未知')}\n"
                    f"健康：{data.get('health_text', '未知')}\n"
                )
                return result
            else:
                error_msg = "星座信息获取失败，请检查token是否有误或稍后再试"
                if isinstance(horoscope_data, dict) and "error" in horoscope_data:
                    error_msg += f"（{horoscope_data['error']}）"
                logger.error(f"[Apilot] Horoscope API error: {horoscope_data}")
                return error_msg
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_horoscope: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取星座信息时出错: {str(e)}"

    def get_weather(self, alapi_token, city_or_id, date, content):
        """Get weather information for a city"""
        logger.info(f"[Apilot] Getting weather for city_or_id={city_or_id}, date={date}")

        url = BASE_URL_ALAPI + 'tianqi'
        isFuture = date in ['明天', '后天', '七天', '7天']
        if isFuture:
            url = BASE_URL_ALAPI + 'tianqi/seven'
            logger.info(f"[Apilot] Using future weather API: {url}")

        # Determine whether to use city_id or city name
        if city_or_id and city_or_id.isnumeric():  # Check if it's a numeric city_id
            params = {
                'city_id': city_or_id,
                'token': f'{alapi_token}'
            }
            logger.info(f"[Apilot] Using city_id: {city_or_id}")
        else:
            city_info = self.check_multiple_city_ids(city_or_id)
            if city_info:
                data = city_info['data']
                formatted_city_info = "\n".join(
                    [f"{idx + 1}) {entry['province']}--{entry['leader']}, ID: {entry['city_id']}"
                     for idx, entry in enumerate(data)]
                )
                logger.info(f"[Apilot] Multiple cities found for {city_or_id}")
                return f'查询 <{city_or_id}> 具有多条数据：\n{formatted_city_info}\n请使用id查询，发送"id天气"'

            params = {
                'city': city_or_id,
                'token': f'{alapi_token}'
            }
            logger.info(f"[Apilot] Using city name: {city_or_id}")

        try:
            logger.info(f"[Apilot] Making weather request to {url} with params: {params}")
            weather_data = self.make_request(url, params=params)
            logger.info(f"[Apilot] Weather API response: {weather_data}")

            if isinstance(weather_data, dict) and weather_data.get("code") == 200:
                data = weather_data.get("data", {})
                logger.info(f"[Apilot] Weather data: {data}")

                if isFuture:
                    # 未来天气API返回的是一个列表
                    if isinstance(data, list) and len(data) > 0:
                        # 获取城市名称（从第一个元素）
                        city_name = data[0].get('city', '未知城市')

                        # 找到明天的天气数据
                        if date == '明天' and len(data) > 1:
                            tomorrow_data = data[1]  # 第二个元素是明天的数据
                            result = (
                                f"📍 {city_name} 明天天气预报\n\n"
                                f"📅 日期：{tomorrow_data.get('date', '未知')}\n"
                                f"⛅ 天气：白天 {tomorrow_data.get('wea_day', '未知')}，夜间 {tomorrow_data.get('wea_night', '未知')}\n"
                                f"🌡️ 温度：{tomorrow_data.get('temp_day', '未知')}℃ / {tomorrow_data.get('temp_night', '未知')}℃\n"
                                f"🌬️ 风向：白天 {tomorrow_data.get('wind_day', '未知')} {tomorrow_data.get('wind_day_level', '未知')}，夜间 {tomorrow_data.get('wind_night', '未知')} {tomorrow_data.get('wind_night_level', '未知')}\n"
                                f"💧 湿度：{tomorrow_data.get('humidity', '未知')}\n"
                                f"👁️ 能见度：{tomorrow_data.get('visibility', '未知')}\n"
                                f"🌅 日出：{tomorrow_data.get('sunrise', '未知')}，日落：{tomorrow_data.get('sunset', '未知')}\n"
                            )

                            # 添加生活指数
                            index_data = tomorrow_data.get('index', [])
                            if index_data:
                                result += "\n📝 生活指数：\n"
                                for index in index_data:
                                    if isinstance(index, dict):
                                        name = index.get('name', '未知')
                                        level = index.get('level', '未知')

                                        # 设置表情符号
                                        emoji = "🚗" if "洗车" in name else "🏃" if "运动" in name else "🤧" if "感冒" in name or "过敏" in name else "☂️" if "紫外线" in name else "🌫️" if "空气" in name else "📌"

                                        # 设置状态颜色
                                        status_emoji = ""
                                        if "适宜" in level or "最弱" in level or "优" in level:
                                            status_emoji = "🟢"  # 绿色
                                        elif "较适宜" in level or "弱" in level or "良" in level:
                                            status_emoji = "🔵"  # 蓝色
                                        elif "较不宜" in level or "中等" in level:
                                            status_emoji = "🟠"  # 橙色
                                        elif "不宜" in level or "较强" in level or "较差" in level:
                                            status_emoji = "🔴"  # 红色
                                        elif "少发" in level or "不易发" in level:
                                            status_emoji = "🟢"  # 绿色
                                        elif "较易发" in level:
                                            status_emoji = "🔴"  # 红色
                                        elif "易发" in level:
                                            status_emoji = "🔴"  # 红色
                                        elif "极易发" in level:
                                            status_emoji = "🔴"  # 红色

                                        result += f"{emoji} {name} {status_emoji} {level}\n"

                            return result

                        # 处理后天或七天天气
                        elif date in ['后天', '七天', '7天']:
                            # 确定要显示的天数和标题
                            if date == '后天' and len(data) > 2:
                                # 只显示后天的天气
                                day_data = data[2]  # 第三个元素是后天的数据
                                result = (
                                    f"📍 {city_name} 后天天气预报\n\n"
                                    f"📅 日期：{day_data.get('date', '未知')}\n"
                                    f"⛅ 天气：白天 {day_data.get('wea_day', '未知')}，夜间 {day_data.get('wea_night', '未知')}\n"
                                    f"🌡️ 温度：{day_data.get('temp_day', '未知')}℃ / {day_data.get('temp_night', '未知')}℃\n"
                                    f"🌬️ 风向：白天 {day_data.get('wind_day', '未知')} {day_data.get('wind_day_level', '未知')}，夜间 {day_data.get('wind_night', '未知')} {day_data.get('wind_night_level', '未知')}\n"
                                    f"💧 湿度：{day_data.get('humidity', '未知')}\n"
                                    f"👁️ 能见度：{day_data.get('visibility', '未知')}\n"
                                    f"🌅 日出：{day_data.get('sunrise', '未知')}，日落：{day_data.get('sunset', '未知')}\n"
                                )

                                # 添加生活指数
                                index_data = day_data.get('index', [])
                                if index_data:
                                    result += "\n📝 生活指数：\n"
                                    for index in index_data:
                                        if isinstance(index, dict):
                                            name = index.get('name', '未知')
                                            level = index.get('level', '未知')

                                            # 设置表情符号
                                            emoji = "🚗" if "洗车" in name else "🏃" if "运动" in name else "🤧" if "感冒" in name or "过敏" in name else "☂️" if "紫外线" in name else "🌫️" if "空气" in name else "📌"

                                            # 设置状态颜色
                                            status_emoji = ""
                                            if "适宜" in level or "最弱" in level or "优" in level:
                                                status_emoji = "🟢"  # 绿色
                                            elif "较适宜" in level or "弱" in level or "良" in level:
                                                status_emoji = "🔵"  # 蓝色
                                            elif "较不宜" in level or "中等" in level:
                                                status_emoji = "🟠"  # 橙色
                                            elif "不宜" in level or "较强" in level or "较差" in level:
                                                status_emoji = "🔴"  # 红色
                                            elif "少发" in level or "不易发" in level:
                                                status_emoji = "🟢"  # 绿色
                                            elif "较易发" in level:
                                                status_emoji = "🔴"  # 红色
                                            elif "易发" in level:
                                                status_emoji = "🔴"  # 红色
                                            elif "极易发" in level:
                                                status_emoji = "🔴"  # 红色

                                            result += f"{emoji} {name} {status_emoji} {level}\n"

                                return result
                            else:
                                # 创建七天天气预报
                                result = f"📍 {city_name} 未来天气预报\n\n"

                                # 确定要显示的天数
                                days_to_show = 7 if date in ['七天', '7天'] else 3
                                days_to_show = min(days_to_show, len(data))

                                # 从第二天开始显示（索引1是明天）
                                start_idx = 1
                                if date == '后天':
                                    start_idx = 2  # 从后天开始显示

                                for i in range(start_idx, days_to_show):
                                    day_data = data[i]
                                    result += (
                                        f"📅 {day_data.get('date', '未知')}\n"
                                        f"⛅ 天气：白天 {day_data.get('wea_day', '未知')}，夜间 {day_data.get('wea_night', '未知')}\n"
                                        f"🌡️ 温度：{day_data.get('temp_day', '未知')}℃ / {day_data.get('temp_night', '未知')}℃\n"
                                        f"🌬️ 风向：{day_data.get('wind_day', '未知')} {day_data.get('wind_day_level', '未知')}\n"
                                        f"💧 空气质量：{day_data.get('air_level', '未知')}\n\n"
                                    )

                            return result
                    else:
                        logger.error(f"[Apilot] Future weather data format error: {data}")
                        return "未来天气信息格式错误，请稍后再试"
                elif not isinstance(data, dict):
                    logger.error(f"[Apilot] Weather data is not a dictionary: {data}")
                    return "天气信息格式错误，请稍后再试"
                else:
                    # Format current day weather data
                    # Use .get() method to safely access dictionary keys
                    aqi_data = data.get('aqi', {})
                    index_data = data.get('index', [])

                    if not isinstance(aqi_data, dict):
                        aqi_data = {}

                    # Extract index information
                    index_info = {}
                    if isinstance(index_data, list):
                        for item in index_data:
                            if isinstance(item, dict):
                                item_type = item.get('type', '')
                                if 'xiche' in item_type:
                                    index_info['wash_car'] = item.get('content', '无建议')
                                elif 'yundong' in item_type:
                                    index_info['sports'] = item.get('content', '无建议')
                                elif 'ziwanxian' in item_type:
                                    index_info['uv'] = item.get('content', '无建议')

                    # 获取城市和日期信息，并处理None值
                    city = data.get('city', '未知城市')
                    if city is None or city == "None":
                        city = '未知城市'

                    province = data.get('province', '')
                    if province is None or province == "None":
                        province = ''

                    date = data.get('date', '未知日期')
                    if date is None or date == "None":
                        date = '未知日期'

                    # 处理天气信息，确保None值被替换为默认值
                    weather = data.get('weather', '未知')
                    if weather is None or weather == "None":
                        weather = '未知'

                    weather_code = data.get('weather_code', '')
                    if weather_code is None or weather_code == "None":
                        weather_code = ''

                    temp = data.get('temp', '未知')
                    if temp is None or temp == "None":
                        temp = '未知'

                    min_temp = data.get('min_temp', '未知')
                    if min_temp is None or min_temp == "None":
                        min_temp = '未知'

                    sunrise = data.get('sunrise', '未知')
                    if sunrise is None or sunrise == "None":
                        sunrise = '未知'

                    sunset = data.get('sunset', '未知')
                    if sunset is None or sunset == "None":
                        sunset = '未知'

                    # 构建基本天气信息
                    result = f"🏙️ 城市: {city}"
                    if province and province != city:
                        result += f" ({province})"
                    result += "\n\n"

                    result += f"🕒 日期: {date}\n"
                    result += f"☁️ 天气: {weather}"
                    if weather_code:
                        result += f" | {weather_code}"
                    result += "\n"

                    result += f"🌡️ 温度: {temp}℃"
                    if min_temp != '未知':
                        result += f" | {min_temp}℃"
                    result += "\n"

                    result += f"🌅 日出/日落: {sunrise} / {sunset}\n"

                    # 添加天气指标部分
                    result += "\n⚠️ 天气指标:\n"

                    # 处理指数信息
                    if isinstance(index_data, list):
                        for item in index_data:
                            if isinstance(item, dict):
                                # 获取指数名称并处理None值
                                name = item.get('name', '')
                                if name is None or name == "None":
                                    name = '未知指数'

                                # 获取指数级别并处理None值
                                level = item.get('level', '')
                                if level is None or level == "None":
                                    level = '未知'

                                # 获取指数代码并处理None值
                                code = item.get('code', '')
                                if code is None or code == "None":
                                    code = ''

                                # 只有当名称和级别都有值时才添加到结果中
                                if name and name != '未知指数':
                                    # 获取指标类型
                                    indicator_type = ""
                                    if "过敏" in name:
                                        indicator_type = "guoming"
                                        emoji = "😷"  # 过敏指数
                                    elif "洗车" in name:
                                        indicator_type = "xiche"
                                        emoji = "🚗"  # 洗车指数
                                    elif "感冒" in name:
                                        indicator_type = "ganmao"
                                        emoji = "🤧"  # 感冒指数
                                    elif "运动" in name:
                                        indicator_type = "yundong"
                                        emoji = "🏃"  # 运动指数
                                    elif "空气" in name or "污染" in name or "扩散" in name:
                                        indicator_type = "air"
                                        emoji = "🌫️"  # 空气污染指数
                                    elif "紫外线" in name:
                                        indicator_type = "ziwanxian"
                                        emoji = "☀️"  # 紫外线指数
                                    elif "钓鱼" in name:
                                        indicator_type = "diaoyu"
                                        emoji = "🎣"  # 钓鱼指数
                                    elif "穿衣" in name:
                                        indicator_type = "chuanyi"
                                        emoji = "👕"  # 穿衣指数
                                    elif "旅游" in name:
                                        indicator_type = "lvyou"
                                        emoji = "🏖️"  # 旅游指数
                                    elif "带伞" in name:
                                        indicator_type = "daisan"
                                        emoji = "☂️"  # 带伞指数
                                    else:
                                        emoji = "📌"  # 默认emoji

                                    # 设置状态颜色 - 根据不同指标类型使用不同的颜色逻辑
                                    status_emoji = "⚪"  # 默认白色

                                    # 根据指标类型选择特定的判断逻辑
                                    if indicator_type == "ziwanxian":  # 紫外线指数
                                        if any(keyword in level for keyword in ["弱", "最弱"]):
                                            status_emoji = "🟢"  # 绿色表示弱
                                        elif "中等" in level:
                                            status_emoji = "🟡"  # 黄色表示中等
                                        elif "强" in level and "很强" not in level and "极强" not in level:
                                            status_emoji = "🟠"  # 橙色表示强
                                        elif "很强" in level:
                                            status_emoji = "🔴"  # 红色表示很强
                                        elif "极强" in level:
                                            status_emoji = "🟣"  # 紫色表示极强
                                    elif indicator_type == "ganmao":  # 感冒指数
                                        if "不易发" in level:
                                            status_emoji = "🟢"  # 绿色表示不易发
                                        elif "少发" in level:
                                            status_emoji = "🔵"  # 蓝色表示少发
                                        elif "较易发" in level:
                                            status_emoji = "🟡"  # 黄色表示较易发
                                        elif "易发" in level:
                                            status_emoji = "🔴"  # 红色表示易发
                                        elif "极易发" in level:
                                            status_emoji = "🔴"  # 红色表示极易发
                                    elif indicator_type == "xiche":  # 洗车指数
                                        if "适宜" in level and "不" not in level and "较" not in level:
                                            status_emoji = "🟢"  # 绿色表示适宜
                                        elif "较适宜" in level:
                                            status_emoji = "🔵"  # 蓝色表示较适宜
                                        elif "不适宜" in level:
                                            status_emoji = "🔴"  # 红色表示不适宜
                                    elif indicator_type == "yundong":  # 运动指数
                                        if "适宜" in level and "不" not in level and "较" not in level:
                                            status_emoji = "🟢"  # 绿色表示适宜
                                        elif "较适宜" in level:
                                            status_emoji = "🔵"  # 蓝色表示较适宜
                                        elif "不建议" in level:
                                            status_emoji = "🟡"  # 黄色表示不建议
                                        elif "不适宜" in level:
                                            status_emoji = "🔴"  # 红色表示不适宜
                                    elif indicator_type == "chuanyi":  # 穿衣指数
                                        if any(keyword in level for keyword in ["炎热", "短袖"]):
                                            status_emoji = "🔴"  # 红色表示炎热
                                        elif any(keyword in level for keyword in ["舒适", "薄外套"]):
                                            status_emoji = "🟢"  # 绿色表示舒适
                                        elif any(keyword in level for keyword in ["较冷", "毛衣", "夹克"]):
                                            status_emoji = "🟡"  # 黄色表示较冷
                                        elif any(keyword in level for keyword in ["寒冷", "棉衣", "羽绒服"]):
                                            status_emoji = "🔵"  # 蓝色表示寒冷
                                    elif indicator_type == "lvyou":  # 旅游指数
                                        if "非常适宜" in level:
                                            status_emoji = "🟢"  # 绿色表示非常适宜
                                        elif "适宜" in level and "不" not in level:
                                            status_emoji = "🔵"  # 蓝色表示适宜
                                        elif "一般" in level:
                                            status_emoji = "🟡"  # 黄色表示一般
                                        elif "不适宜" in level:
                                            status_emoji = "🔴"  # 红色表示不适宜
                                    elif indicator_type == "diaoyu":  # 钓鱼指数
                                        if "适宜" in level and "不" not in level and "较" not in level:
                                            status_emoji = "🟢"  # 绿色表示适宜
                                        elif "较适宜" in level:
                                            status_emoji = "🔵"  # 蓝色表示较适宜
                                        elif "不适宜" in level:
                                            status_emoji = "🔴"  # 红色表示不适宜
                                    elif indicator_type == "guoming":  # 过敏指数
                                        if any(keyword in level for keyword in ["不易过敏", "1级"]):
                                            status_emoji = "🟢"  # 绿色表示1级不易过敏
                                        elif any(keyword in level for keyword in ["过敏少发", "2级"]):
                                            status_emoji = "🔵"  # 蓝色表示2级过敏少发
                                        elif any(keyword in level for keyword in ["较易过敏", "3级"]):
                                            status_emoji = "🟡"  # 黄色表示3级较易过敏
                                        elif any(keyword in level for keyword in ["易过敏", "4级"]):
                                            status_emoji = "🟠"  # 橙色表示4级易过敏
                                        elif any(keyword in level for keyword in ["极易过敏", "5级"]):
                                            status_emoji = "🔴"  # 红色表示5级极易过敏
                                        # 兼容旧版本格式
                                        elif "低" in level:
                                            status_emoji = "🟢"  # 绿色表示低
                                        elif "中" in level:
                                            status_emoji = "🟡"  # 黄色表示中
                                        elif "高" in level:
                                            status_emoji = "🔴"  # 红色表示高
                                    elif indicator_type == "air":  # 空气污染扩散条件指数
                                        if any(keyword in level for keyword in ["优", "良好", "有利"]):
                                            status_emoji = "🟢"  # 绿色表示优/良好
                                        elif any(keyword in level for keyword in ["良", "一般", "中等"]):
                                            status_emoji = "🔵"  # 蓝色表示良/一般
                                        elif any(keyword in level for keyword in ["轻度", "较差"]):
                                            status_emoji = "🟡"  # 黄色表示轻度污染
                                        elif any(keyword in level for keyword in ["中度", "差"]):
                                            status_emoji = "🟠"  # 橙色表示中度污染
                                        elif any(keyword in level for keyword in ["重度", "很差"]):
                                            status_emoji = "🔴"  # 红色表示重度污染
                                        elif any(keyword in level for keyword in ["严重", "极差"]):
                                            status_emoji = "🟣"  # 紫色表示严重污染
                                    else:  # 通用判断逻辑
                                        if any(keyword in level for keyword in ["适宜", "良好", "最弱", "不需要", "不易", "舒适"]):
                                            status_emoji = "🟢"  # 绿色表示良好
                                        elif any(keyword in level for keyword in ["较适宜", "中等", "弱", "偏高", "一般"]):
                                            status_emoji = "🟡"  # 黄色表示中等
                                        elif any(keyword in level for keyword in ["较不宜", "较强", "少量"]):
                                            status_emoji = "🟠"  # 橙色表示较差
                                        elif any(keyword in level for keyword in ["不宜", "很强", "不建议", "高发", "易发", "极强", "不适宜"]):
                                            status_emoji = "🔴"  # 红色表示不佳

                                    result += f"{emoji} {name} {status_emoji} {level}\n"

                    # 添加空气质量信息
                    if aqi_data:
                        result += "\n🌫️ 空气质量:\n"

                        # 处理空气质量指数
                        air = aqi_data.get('air', '未知')
                        if air is None or air == "None":
                            air = '未知'

                        air_level = aqi_data.get('air_level', '未知')
                        if air_level is None or air_level == "None":
                            air_level = '未知'

                        result += f"🔵 质量指数: {air} ({air_level})\n"

                        # 处理PM2.5和PM10
                        pm25 = aqi_data.get('pm25', '未知')
                        if pm25 is None or pm25 == "None":
                            pm25 = '未知'

                        pm10 = aqi_data.get('pm10', '未知')
                        if pm10 is None or pm10 == "None":
                            pm10 = '未知'

                        result += f"😷 PM2.5: {pm25} | PM10: {pm10}\n"

                        # 处理其他空气质量指标
                        co = aqi_data.get('co', '未知')
                        if co is None or co == "None":
                            co = '未知'

                        no2 = aqi_data.get('no2', '未知')
                        if no2 is None or no2 == "None":
                            no2 = '未知'

                        so2 = aqi_data.get('so2', '未知')
                        if so2 is None or so2 == "None":
                            so2 = '未知'

                        o3 = aqi_data.get('o3', '未知')
                        if o3 is None or o3 == "None":
                            o3 = '未知'

                        result += f"🧪 CO: {co} | NO₂: {no2} | SO₂: {so2} | O₃: {o3}\n"

                        # 处理空气提示
                        air_tips = aqi_data.get('air_tips', '无提示')
                        if air_tips is None or air_tips == "None":
                            air_tips = '无提示'

                        result += f"💡 提示: {air_tips}\n"

                    # 添加预警信息
                    alarm_data = data.get('alarm', [])
                    if isinstance(alarm_data, list) and alarm_data:
                        # 添加空行分隔
                        result += "\n⚠️ 预警信息:\n"
                        for alarm in alarm_data:
                            if isinstance(alarm, dict):
                                # 根据预警等级选择合适的emoji
                                level_emoji = "⚠️"
                                level = alarm.get('level', '')
                                if level is None or level == "None":
                                    level = ''

                                if "红色" in level:
                                    level_emoji = "🔴"
                                elif "橙色" in level:
                                    level_emoji = "🟠"
                                elif "黄色" in level:
                                    level_emoji = "🟡"
                                elif "蓝色" in level:
                                    level_emoji = "🔵"

                                # 获取其他预警信息
                                title = alarm.get('title', '')
                                if title is None or title == "None":
                                    title = ''

                                alarm_type = alarm.get('type', '')
                                if alarm_type is None or alarm_type == "None":
                                    alarm_type = ''

                                publish_time = alarm.get('publish_time', '')
                                if publish_time is None or publish_time == "None":
                                    publish_time = ''

                                tips = alarm.get('tips', '')
                                if tips is None or tips == "None":
                                    tips = ''
                                # 处理内容中可能存在的HTML标签
                                tips = tips.replace('<br>', '\n        ').replace('<br/>', '\n        ')

                                content = alarm.get('content', '')
                                if content is None or content == "None":
                                    content = ''

                                # 构建更清晰的预警信息格式
                                if title and level:
                                    result += (
                                        f"{level_emoji} {alarm_type}{level}预警: {title}\n"
                                        f"⏰ 发布时间: {publish_time}\n"
                                    )

                                    if tips:
                                        result += (
                                            f"📋 预警提示:\n"
                                            f"        {tips}\n"
                                        )

                                    if content:
                                        result += (
                                            f"📢 详细内容:\n"
                                            f"        {content}\n\n"
                                        )

                    # 添加小时预报
                    hour_data = data.get('hour', [])
                    if isinstance(hour_data, list) and hour_data:
                        result += "\n⏳ 未来10小时的天气预报:\n"
                        count = 0
                        for hour in hour_data:
                            if count >= 10:  # 只显示10小时
                                break
                            if isinstance(hour, dict):
                                # 获取时间
                                time_str = hour.get('time', '')
                                if time_str is None or time_str == "None":
                                    time_str = ''

                                # 获取天气
                                wea = hour.get('wea', '未知')
                                if wea is None or wea == "None":
                                    wea = '未知'

                                # 获取温度
                                temp = hour.get('temp', '未知')
                                if temp is None or temp == "None":
                                    temp = '未知'

                                # 只有当所有必要数据都存在时才添加到结果中
                                if time_str:
                                    time_parts = time_str.split(' ')
                                    time = time_parts[1] if len(time_parts) > 1 else time_str
                                    result += f"{time} - {wea} - {temp}℃\n"
                                    count += 1

                    return result
            else:
                error_msg = "天气信息获取失败，请检查城市名称或稍后再试"
                if isinstance(weather_data, dict) and "error" in weather_data:
                    error_msg += f"（{weather_data['error']}）"
                logger.error(f"[Apilot] Weather API error: {weather_data}")
                return error_msg
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_weather: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取天气信息时出错: {str(e)}"

    def get_netease_news(self, alapi_token, news_type="综合"):
        """Get news from NetEase"""
        logger.info(f"[Apilot] Getting news for type: {news_type}")
        url = BASE_URL_ALAPI + "new/toutiao"

        # 根据新闻类型获取对应的type值
        # 新闻类型映射表
        NEWS_TYPE_MAPPING = {
            '综合': '1',
            '娱乐': '2',
            '体育': '3',
            '财经': '4',
            '科技': '5',
            '搞笑': '6',
            '游戏': '7',
            '读书': '8',
            '生活': '9',
            '直播': '10',
            '历史': '11',
            '国际': '12',
            '影视': '13',
            '国内足球': '14',
            '国际足球': '15',
            '篮球': '16',
            '跑步': '17',
            '手机': '18',
            '电脑': '19',
            '新能源': '20',
            '设计': '21',
            '地方': '22',
            '健康': '23',
            '酒文化': '24',
            '教育': '25',
            '育儿': '26',
            '女性': '27',
            '情感': '28',
            '官方': '29',
            '奇事': '30'
        }

        # 获取新闻类型对应的值，默认为综合(1)
        type_value = NEWS_TYPE_MAPPING.get(news_type, '1')

        params = {
            "token": alapi_token,
            "type": type_value
        }

        headers = {"Content-Type": "application/json"}
        try:
            logger.info(f"[Apilot] Making GET news request to {url} with params: {params}")
            news_data = self.make_request(url, method="GET", params=params, headers=headers)
            logger.info(f"[Apilot] News API response: {news_data}")

            if isinstance(news_data, dict) and news_data.get("code") == 200:
                data = news_data.get("data", [])
                logger.info(f"[Apilot] News data: {data}")

                # 检查data是否为列表
                if isinstance(data, list):
                    news_list = data

                    # 检查新闻列表是否为空
                    if not news_list:
                        logger.warning("[Apilot] News list is empty")
                        return "暂时没有获取到新闻，请稍后再试。可能是API限制或服务器问题，请稍后再尝试。"

                    result = f"📰 网易{news_type}新闻\n\n"

                    for idx, news in enumerate(news_list, 1):
                        if idx > 10:  # Limit to 10 news items
                            break
                        if isinstance(news, dict):
                            title = news.get('title', '未知标题')
                            source = news.get('source', '')
                            time_str = news.get('time', '')
                            pc_url = news.get('pc_url', '')

                            result += f"{idx}. {title}"
                            if source or time_str:
                                result += f"\n   🔖 来源: {source} {time_str}"
                            if pc_url:
                                result += f"\n   🔗 链接: {pc_url}"
                            result += "\n\n"
                        else:
                            logger.warning(f"[Apilot] News item is not a dictionary: {news}")

                    # 添加提示信息
                    supported_types = "、".join(list(NEWS_TYPE_MAPPING.keys())[:10]) + "等"
                    result += f"\n💡 发送\"XX新闻\"获取特定类型新闻，如：{supported_types}"

                    return result
                else:
                    logger.error(f"[Apilot] News data is not a list: {data}")
                    return "新闻信息格式错误，请稍后再试"
            else:
                error_msg = "新闻获取失败，请稍后再试"
                if isinstance(news_data, dict):
                    if "error" in news_data:
                        error_msg += f"（{news_data['error']}）"
                    elif "message" in news_data:
                        error_msg += f"（{news_data['message']}）"
                logger.error(f"[Apilot] News API error: {news_data}")
                return error_msg
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_netease_news: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取新闻时出错: {str(e)}"

    def check_multiple_city_ids(self, city_name):
        """Check if a city name has multiple IDs"""
        url = BASE_URL_ALAPI + 'tianqi/citylist'
        params = {
            'token': self.alapi_token,
            'city': city_name
        }
        try:
            response = self.make_request(url, params=params)
            if isinstance(response, dict) and response.get("code") == 200:
                data = response.get("data", [])
                if len(data) > 1:
                    return response
            return None
        except Exception as e:
            logger.error(f"[Apilot] Error checking city IDs: {str(e)}")
            return None

    def make_request(self, url, method="GET", params=None, headers=None, json_data=None):
        """Make an HTTP request to an API"""
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                response = requests.post(url, params=params, headers=headers, json=json_data, timeout=10)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[Apilot] Request error: {str(e)}")
            return {"error": str(e)}
        except ValueError as e:
            logger.error(f"[Apilot] JSON parsing error: {str(e)}")
            return {"error": "Invalid JSON response"}
        except Exception as e:
            logger.error(f"[Apilot] Unexpected error: {str(e)}")
            return {"error": str(e)}

    def get_soul_dujitang(self, alapi_token):
        """Get a random soul chicken soup quote"""
        logger.info("[Apilot] Getting soul dujitang")
        url = BASE_URL_ALAPI + "soul"
        payload = {"token": alapi_token}
        headers = {'Content-Type': "application/json"}
        try:
            logger.info(f"[Apilot] Making soul dujitang request to {url}")
            soul_data = self.make_request(url, method="POST", headers=headers, json_data=payload)
            logger.info(f"[Apilot] Soul dujitang API response: {soul_data}")

            if isinstance(soul_data, dict) and soul_data.get('code') == 200:
                data = soul_data.get('data', {})
                if not isinstance(data, dict):
                    logger.error(f"[Apilot] Soul dujitang data is not a dictionary: {data}")
                    return "毒鸡汤获取失败，请稍后再试"

                content = data.get('content', '未知')
                # 格式化并返回 ALAPI 提供的心灵毒鸡汤信息
                result = f"💡【今日心灵毒鸡汤】\n{content}\n"
                return result
            else:
                error_msg = "毒鸡汤获取失败，请稍后再试"
                if isinstance(soul_data, dict) and "error" in soul_data:
                    error_msg += f"（{soul_data['error']}）"
                logger.error(f"[Apilot] Soul dujitang API error: {soul_data}")
                return error_msg
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_soul_dujitang: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取毒鸡汤时出错: {str(e)}"

    def get_dog_diary(self, alapi_token):
        """Get a random dog diary entry"""
        logger.info("[Apilot] Getting dog diary")
        url = BASE_URL_ALAPI + "dog"
        payload = {
            "token": alapi_token,
            "format": 'json'
        }
        headers = {"Content-Type": "application/json"}
        try:
            logger.info(f"[Apilot] Making dog diary request to {url}")
            dog_diary_data = self.make_request(url, method='POST', headers=headers, json_data=payload)
            logger.info(f"[Apilot] Dog diary API response: {dog_diary_data}")

            if isinstance(dog_diary_data, dict) and dog_diary_data.get('code') == 200:
                data = dog_diary_data.get('data', {})
                if not isinstance(data, dict):
                    logger.error(f"[Apilot] Dog diary data is not a dictionary: {data}")
                    return "舔狗日记获取失败，请稍后再试"

                content = data.get('content', '未知')
                format_output = (
                    "【（づ￣3￣）づ╭❤️～舔狗日记】  \n  "
                    f"  🐶{content}"
                )
                return format_output
            else:
                error_msg = "舔狗日记获取失败，请稍后再试"
                if isinstance(dog_diary_data, dict) and "error" in dog_diary_data:
                    error_msg += f"（{dog_diary_data['error']}）"
                logger.error(f"[Apilot] Dog diary API error: {dog_diary_data}")
                return error_msg
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_dog_diary: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取舔狗日记时出错: {str(e)}"

    def is_valid_url(self, url):
        """Check if a string is a valid URL"""
        if not isinstance(url, str):
            return False
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    async def get_morning_news(self, alapi_token, text_enabled=False):
        """Get morning news, either as text or image - using original DOW plugin's approach"""
        logger.info(f"[Apilot] Getting morning news, text_enabled={text_enabled}")

        if text_enabled:
            # 获取文字版早报
            if alapi_token:
                url = BASE_URL_ALAPI + "zaobao/news"
                payload = {"token": alapi_token}
                headers = {"Content-Type": "application/json"}
                try:
                    logger.info(f"[Apilot] Making morning news text request to ALAPI: {url}")
                    news_data = self.make_request(url, method="POST", headers=headers, json_data=payload)
                    logger.info(f"[Apilot] ALAPI morning news text response: {news_data}")

                    if isinstance(news_data, dict) and news_data.get('code') == 200:
                        data = news_data.get('data', {})
                        if not isinstance(data, dict):
                            logger.error(f"[Apilot] Morning news data is not a dictionary: {data}")
                            return "早报获取失败，请稍后再试"

                        date = data.get('date', '未知日期')
                        news_list = data.get('news', [])
                        weiyu = data.get('weiyu', '')

                        if not isinstance(news_list, list):
                            logger.error(f"[Apilot] Morning news list is not a list: {news_list}")
                            return "早报内容格式错误，请稍后再试"

                        result = f"☕ {date} 今日早报\n\n"

                        for idx, news in enumerate(news_list, 1):
                            if isinstance(news, str):
                                result += f"{idx}. {news}\n"

                        if weiyu:
                            result += f"\n【微语】{weiyu}"

                        return result
                    else:
                        error_msg = "ALAPI早报获取失败，尝试其他API源"
                        if isinstance(news_data, dict) and "error" in news_data:
                            error_msg += f"（{news_data['error']}）"
                        logger.error(f"[Apilot] ALAPI morning news text error: {news_data}")
                        # 继续尝试其他API
                except Exception as e:
                    logger.error(f"[Apilot] Exception in get_morning_news (ALAPI text): {str(e)}")
                    logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
                    # 继续尝试其他API

            # 如果ALAPI失败或没有token，尝试其他API
            try:
                url = "https://api.03c3.cn/api/zb"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json"
                }

                logger.info(f"[Apilot] Trying backup API for text news: {url}")

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=15) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                if data.get('code') == 200 and 'data' in data:
                                    news_list = data['data'].get('news', [])
                                    if news_list:
                                        result = f"☕ 今日早报\n\n"
                                        for idx, news in enumerate(news_list, 1):
                                            result += f"{idx}. {news}\n"
                                        return result
                            except Exception as json_error:
                                logger.error(f"[Apilot] Failed to parse backup API response: {json_error}")

                # 如果所有尝试都失败，返回错误消息
                return "早报文本获取失败，请稍后再试"
            except Exception as e:
                logger.error(f"[Apilot] Exception in get_morning_news (backup text): {str(e)}")
                logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
                return f"获取早报时出错: {str(e)}"
        else:
            # 获取图片版早报
            # 首选ALAPI，如果有token的话
            if alapi_token:
                try:
                    logger.info(f"[Apilot] Trying ALAPI for morning news image")
                    url = BASE_URL_ALAPI + "zaobao"
                    params = {"token": alapi_token, "format": "json"}

                    news_data = self.make_request(url, params=params)
                    logger.info(f"[Apilot] ALAPI morning news response: {news_data}")

                    if isinstance(news_data, dict) and news_data.get('code') == 200:
                        data = news_data.get('data', {})
                        if isinstance(data, dict) and 'image' in data:
                            img_url = data['image']
                            logger.info(f"[Apilot] Got image URL from ALAPI: {img_url}")

                            # 下载图片
                            headers = {
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                "Accept": "image/webp, image/apng, image/*",
                                "Referer": "https://api.alapi.cn/"
                            }

                            async with aiohttp.ClientSession() as session:
                                async with session.get(img_url, headers=headers, timeout=15) as response:
                                    if response.status == 200:
                                        img_data = await response.read()
                                        logger.info(f"[Apilot] Successfully downloaded morning news image from ALAPI, size: {len(img_data)} bytes")
                                        return img_data
                except Exception as alapi_error:
                    logger.error(f"[Apilot] Failed to get morning news from ALAPI: {str(alapi_error)}")
                    # 继续尝试备用API

            # 如果ALAPI失败或没有token，尝试备用API
            try:
                # 尝试使用多个API源获取早报图片
                backup_apis = [
                    "https://api.03c3.cn/api/zb",
                    "https://api.vvhan.com/api/60s",
                    "https://api.pearktrue.cn/api/60s/image"
                ]

                logger.info(f"[Apilot] Trying backup APIs for morning news image")

                for api_url in backup_apis:
                    try:
                        logger.info(f"[Apilot] Trying API: {api_url}")
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept": "application/json, image/webp, image/apng, image/*"
                        }

                        async with aiohttp.ClientSession() as session:
                            async with session.get(api_url, headers=headers, timeout=15) as response:
                                if response.status == 200:
                                    # 检查是否返回JSON数据
                                    content_type = response.headers.get('Content-Type', '')
                                    if 'application/json' in content_type:
                                        data = await response.json()
                                        if "api/zb" in api_url and 'data' in data and 'imageurl' in data['data']:
                                            img_url = data['data']['imageurl']
                                            logger.info(f"[Apilot] Got image URL from {api_url}: {img_url}")

                                            # 下载图片
                                            async with session.get(img_url, headers=headers, timeout=15) as img_response:
                                                if img_response.status == 200:
                                                    img_data = await img_response.read()
                                                    logger.info(f"[Apilot] Successfully downloaded morning news image from {img_url}, size: {len(img_data)} bytes")
                                                    return img_data
                                        elif "api/60s" in api_url and 'imgUrl' in data:
                                            img_url = data['imgUrl']
                                            logger.info(f"[Apilot] Got image URL from {api_url}: {img_url}")

                                            # 下载图片
                                            async with session.get(img_url, headers=headers, timeout=15) as img_response:
                                                if img_response.status == 200:
                                                    img_data = await img_response.read()
                                                    logger.info(f"[Apilot] Successfully downloaded morning news image from {img_url}, size: {len(img_data)} bytes")
                                                    return img_data
                                    # 如果是直接返回图片
                                    elif 'image' in content_type:
                                        img_data = await response.read()
                                        logger.info(f"[Apilot] Successfully downloaded morning news image directly from {api_url}, size: {len(img_data)} bytes")
                                        return img_data
                    except Exception as api_error:
                        logger.error(f"[Apilot] Failed to get morning news from {api_url}: {str(api_error)}")
                        continue

                # 如果所有尝试都失败，返回错误消息
                logger.error(f"[Apilot] All attempts to get morning news image failed")
                return "早报图片获取失败，请稍后再试"
            except Exception as e:
                logger.error(f"[Apilot] Exception in get_morning_news (image): {str(e)}")
                logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
                return f"获取早报时出错: {str(e)}"

    async def get_moyu_calendar(self):
        """Get moyu (slacking off) calendar - using same approach as morning news"""
        logger.info("[Apilot] Getting moyu calendar using same approach as morning news")
        try:
            # 使用与早报相同的方式下载图片
            url = "https://api.vvhan.com/api/moyu"
            logger.info(f"[Apilot] Downloading moyu calendar from {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/webp, image/apng, image/*",
                "Referer": "https://api.vvhan.com/"
            }

            # 使用与早报相同的方式下载图片
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        # 检查是否是图片内容
                        content_type = response.headers.get('Content-Type', '')
                        if 'image' in content_type:
                            img_data = await response.read()
                            logger.info(f"[Apilot] Successfully downloaded moyu calendar, size: {len(img_data)} bytes, content-type: {content_type}")
                            return img_data
                        else:
                            logger.error(f"[Apilot] Moyu calendar response is not an image: {content_type}")
                            return f"摸鱼日历返回的不是图片: {content_type}"
                    else:
                        logger.error(f"[Apilot] Failed to download moyu calendar, status code: {response.status}")
                        return "摸鱼日历获取失败，请稍后再试"
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_moyu_calendar: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取摸鱼日历时出错: {str(e)}"

    async def get_moyu_calendar_video(self):
        """Get moyu (slacking off) calendar video"""
        logger.info("[Apilot] Getting moyu calendar video")
        url = self.moyu_video_api_url
        try:
            # 直接返回URL，用于卡片视频
            logger.info(f"[Apilot] Returning moyu calendar video URL: {url}")
            return url
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_moyu_calendar_video: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取摸鱼视频时出错: {str(e)}"

    async def get_mx_bagua(self):
        """Get celebrity gossip"""
        logger.info("[Apilot] Getting celebrity gossip")
        url = self.bagua_api_url
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        try:
            logger.info(f"[Apilot] Making celebrity gossip request to {url}")
            bagua_info = self.make_request(url, method="POST", headers=headers, data=payload)
            logger.info(f"[Apilot] Celebrity gossip API response: {bagua_info}")

            # 验证请求是否成功
            if isinstance(bagua_info, dict) and bagua_info.get('code') == 200:
                bagua_pic_url = bagua_info.get("data", "")
                if self.is_valid_url(bagua_pic_url):
                    # 下载图片内容
                    try:
                        logger.info(f"[Apilot] Downloading celebrity gossip image from {bagua_pic_url}")
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                            'Referer': 'https://dayu.qqsuu.cn/'
                        }

                        # 使用异步HTTP客户端
                        async with aiohttp.ClientSession() as session:
                            async with session.get(bagua_pic_url, headers=headers, timeout=10) as response:
                                if response.status == 200:
                                    # 检查是否是图片内容
                                    content_type = response.headers.get('Content-Type', '')
                                    if 'image' in content_type:
                                        image_data = await response.read()
                                        logger.info(f"[Apilot] Successfully downloaded celebrity gossip image, size: {len(image_data)} bytes")
                                        # 返回图片字节
                                        return image_data
                                    else:
                                        logger.error(f"[Apilot] Celebrity gossip response is not an image: {content_type}")
                                        # 如果不是图片，返回URL
                                        return bagua_pic_url
                                else:
                                    logger.error(f"[Apilot] Failed to download celebrity gossip image, status code: {response.status}")
                                    # 如果下载失败，返回URL
                                    logger.info(f"[Apilot] Falling back to returning URL: {bagua_pic_url}")
                                    return bagua_pic_url
                    except Exception as download_error:
                        logger.error(f"[Apilot] Failed to download celebrity gossip image: {download_error}")
                        # 如果下载失败，返回URL
                        logger.info(f"[Apilot] Falling back to returning URL: {bagua_pic_url}")
                        return bagua_pic_url
                else:
                    return "周末不更新，请微博吃瓜"
            else:
                logger.error(f"[Apilot] Celebrity gossip API error: {bagua_info}")
                return "暂无明星八卦，吃瓜莫急"
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_mx_bagua: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取明星八卦时出错: {str(e)}"

    def get_hot_trends(self, hot_trends_type):
        """Get hot trends"""
        logger.info(f"[Apilot] Getting hot trends for type: {hot_trends_type}")

        # 热榜类型映射
        hot_trend_types = {
            "微博": "wbHot",
            "虎扑": "huPu",
            "知乎": "zhihuHot",
            "知乎日报": "zhihuDay",
            "哔哩哔哩": "bili",
            "36氪": "36Ke",
            "抖音": "douyinHot",
            "IT": "itNews",
            "虎嗅": "huXiu",
            "产品经理": "woShiPm",
            "头条": "toutiao",
            "百度": "baiduRD",
            "豆瓣": "douban",
        }

        # 检查是否支持该类型的热榜
        if hot_trends_type in hot_trend_types:
            url = BASE_URL_ALAPI + "tophub"
            payload = {
                "token": self.alapi_token,
                "type": hot_trend_types[hot_trends_type]
            }
            headers = {"Content-Type": "application/json"}
            try:
                logger.info(f"[Apilot] Making hot trends request to {url}")
                hot_trends_data = self.make_request(url, method="POST", headers=headers, json_data=payload)
                logger.info(f"[Apilot] Hot trends API response: {hot_trends_data}")

                if isinstance(hot_trends_data, dict) and hot_trends_data.get('code') == 200:
                    data = hot_trends_data.get('data', {})
                    if not isinstance(data, dict):
                        logger.error(f"[Apilot] Hot trends data is not a dictionary: {data}")
                        return "热榜获取失败，请稍后再试"

                    if data.get('success') == True:
                        output = []
                        topics = data.get('data', [])
                        update_time = data.get('update_time', '未知')
                        output.append(f'【{hot_trends_type}热榜】更新时间：{update_time}\n')

                        for i, topic in enumerate(topics[:15], 1):
                            if isinstance(topic, dict):
                                title = topic.get('title', '未知标题')
                                hot = topic.get('hot', '无热度参数')
                                url = topic.get('url', '')

                                formatted_str = f"{i}. {title} ({hot} 浏览)"
                                if url:
                                    formatted_str += f"\nURL: {url}"
                                output.append(formatted_str)

                        return "\n".join(output)
                    else:
                        logger.error(f"[Apilot] Hot trends data success is not True: {data}")
                        return "热榜获取失败，请稍后再试"
                else:
                    error_msg = "热榜获取失败，请稍后再试"
                    if isinstance(hot_trends_data, dict) and "error" in hot_trends_data:
                        error_msg += f"（{hot_trends_data['error']}）"
                    logger.error(f"[Apilot] Hot trends API error: {hot_trends_data}")
                    return error_msg
            except Exception as e:
                logger.error(f"[Apilot] Exception in get_hot_trends: {str(e)}")
                logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
                return f"获取热榜时出错: {str(e)}"
        else:
            # 返回支持的热榜类型列表
            supported_types = "/".join(hot_trend_types.keys())
            final_output = (
                f"👉 已支持的类型有：\n\n    {supported_types}\n"
                f"\n📝 请按照以下格式发送：\n    类型+热榜  例如：微博热榜"
            )
            return final_output

    def get_today_on_history(self, alapi_token, month="", day=""):
        """Get historical events that happened on this day"""
        logger.info(f"[Apilot] Getting today on history for month={month}, day={day}")
        url = BASE_URL_ALAPI + "eventHistory"
        payload = {
            "token": alapi_token,
            "month": month,
            "day": day
        }
        headers = {"Content-Type": "application/json"}
        try:
            logger.info(f"[Apilot] Making today on history request to {url}")
            history_event_data = self.make_request(url, method="POST", headers=headers, json_data=payload)
            logger.info(f"[Apilot] Today on history API response: {history_event_data}")

            if isinstance(history_event_data, dict) and history_event_data.get('code') == 200:
                current_date = ""
                if month and day:
                    current_date = f"{month}月{day}日"
                else:
                    today = datetime.now()
                    current_date = today.strftime("%m月%d日")

                format_output = [f"【📆 历史上的今天 {current_date} 📆】\n"]
                data = history_event_data.get('data', [])
                if not isinstance(data, list):
                    logger.error(f"[Apilot] Today on history data is not a list: {data}")
                    return "历史上的今天获取失败，请稍后再试"

                history_count = len(data)

                # 随机选择历史事件
                output_count = min(random.randint(6, 10), history_count)  # 随机选择6-10条事件，但不超过总数
                selected_indices = set()

                # 设置消息长度限制
                total_length = len(format_output[0])
                message_limit = 2000  # 设置消息长度限制（微信单条消息大约2000字左右）

                # 随机选择事件并添加到输出中
                while len(selected_indices) < output_count:
                    idx = random.randint(0, history_count - 1)
                    if idx in selected_indices:
                        continue

                    event = data[idx]
                    if not isinstance(event, dict):
                        continue

                    year = event.get('year', '未知')
                    title = event.get('title', '未知事件')

                    history = f"📍 {year}年：{title}\n"

                    # 检查是否超出消息长度限制
                    if total_length + len(history) > message_limit:
                        break

                    selected_indices.add(idx)
                    format_output.append(history)
                    total_length += len(history)

                # 添加有多少事件未显示的提示
                if history_count > len(selected_indices):
                    remaining = history_count - len(selected_indices)
                    format_output.append(f"\n还有 {remaining} 条历史事件未显示")

                format_output.append("\n💡 发送\"历史上的今天X月X日\"可查询特定日期")
                return "\n".join(format_output)
            else:
                error_msg = "历史上的今天获取失败，请稍后再试"
                if isinstance(history_event_data, dict) and "error" in history_event_data:
                    error_msg += f"（{history_event_data['error']}）"
                logger.error(f"[Apilot] Today on history API error: {history_event_data}")
                return error_msg
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_today_on_history: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取历史上的今天时出错: {str(e)}"

    def handle_error(self, error, default_message="出错啦，稍后再试"):
        """Handle errors and return a user-friendly message"""
        if isinstance(error, dict) and "error" in error:
            logger.error(f"[Apilot] API error: {error['error']}")
            return f"错误: {error['error']}"
        elif isinstance(error, Exception):
            logger.error(f"[Apilot] Exception: {str(error)}")
            return default_message
        else:
            logger.error(f"[Apilot] Unknown error: {error}")
            return default_message

    async def on_enable(self, bot=None):
        """Called when the plugin is enabled"""
        await super().on_enable(bot)
        self.enabled = True  # Ensure the system property is set
        logger.info("[Apilot] Plugin enabled - system state: enabled={}, config state: enable={}".format(
            self.enabled, self.enable))

    async def on_disable(self):
        """Called when the plugin is disabled"""
        await super().on_disable()
        self.enabled = False  # Update the system property
        logger.info("[Apilot] Plugin disabled")

    async def get_mx_bstp(self):
        """Get white stockings images"""
        logger.info("[Apilot] Getting white stockings images")
        url = self.bstp_api_url
        try:
            logger.info(f"[Apilot] Making white stockings request to {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp, image/apng, image/*',
                'Referer': 'https://api.xlb.one/'
            }

            # 使用异步HTTP客户端
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        # 检查是否是图片内容
                        content_type = response.headers.get('Content-Type', '')
                        if 'image' in content_type:
                            img_data = await response.read()
                            logger.info(f"[Apilot] Successfully downloaded white stockings image, size: {len(img_data)} bytes")
                            # 返回图片字节
                            return img_data
                        else:
                            logger.error(f"[Apilot] White stockings response is not an image: {content_type}")
                            # 如果不是图片，返回URL
                            return url
                    else:
                        logger.error(f"[Apilot] Failed to download white stockings image, status code: {response.status}")
                        # 如果下载失败，返回URL
                        logger.info(f"[Apilot] Falling back to returning URL: {url}")
                        return url
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_mx_bstp: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取白丝图片时出错: {str(e)}"

    async def get_mx_hstp(self):
        """Get black stockings images"""
        logger.info("[Apilot] Getting black stockings images")
        url = self.hstp_api_url
        try:
            logger.info(f"[Apilot] Making black stockings request to {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp, image/apng, image/*',
                'Referer': 'https://api.xlb.one/'
            }

            # 使用异步HTTP客户端
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        # 检查是否是图片内容
                        content_type = response.headers.get('Content-Type', '')
                        if 'image' in content_type:
                            img_data = await response.read()
                            logger.info(f"[Apilot] Successfully downloaded black stockings image, size: {len(img_data)} bytes")
                            # 返回图片字节
                            return img_data
                        else:
                            logger.error(f"[Apilot] Black stockings response is not an image: {content_type}")
                            # 如果不是图片，返回URL
                            return url
                    else:
                        logger.error(f"[Apilot] Failed to download black stockings image, status code: {response.status}")
                        # 如果下载失败，返回URL
                        logger.info(f"[Apilot] Falling back to returning URL: {url}")
                        return url
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_mx_hstp: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取黑丝图片时出错: {str(e)}"

    async def send_video_card(self, bot, wxid, video_url, title, description="", thumb_url=None):
        """Send a video card message"""
        logger.info(f"[Apilot] Sending video card: {video_url}")

        # 如果没有提供缩略图URL，使用默认图片
        if not thumb_url:
            thumb_url = "https://api.yujn.cn/static/images/logo.png"

        try:
            # 构造视频卡片XML
            xml = f"""<appmsg appid="wx79f2c4418704b4f8" sdkver="0">
<title>{title}</title>
<des>{description}</des>
<action>view</action>
<type>5</type>
<showtype>0</showtype>
<content/>
<url>{video_url}</url>
<dataurl>{video_url}</dataurl>
<lowurl>{video_url}</lowurl>
<lowdataurl>{video_url}</lowdataurl>
<recorditem/>
<thumburl>{thumb_url}</thumburl>
<messageaction/>
<laninfo/>
<extinfo/>
<sourceusername/>
<sourcedisplayname/>
<commenturl/>
<appattach>
<totallen>0</totallen>
<attachid/>
<emoticonmd5/>
<fileext/>
<aeskey/>
</appattach>
<webviewshared>
<publisherId/>
<publisherReqId>0</publisherReqId>
</webviewshared>
<weappinfo>
<pagepath/>
<username/>
<appid/>
<appservicetype>0</appservicetype>
</weappinfo>
<websearch/>
</appmsg>
<fromusername>{bot.wxid}</fromusername>
<scene>0</scene>
<appinfo>
<version>1</version>
<appname/>
</appinfo>
<commenturl/>"""

            # 发送视频卡片
            await bot.send_app_message(wxid, xml, 5)
            logger.info(f"[Apilot] Video card sent successfully")
            return True
        except Exception as e:
            logger.error(f"[Apilot] Failed to send video card: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return False

    async def _get_video_with_cover(self, url, video_type, referer="https://api.yujn.cn/"):
        """Generic method to get videos with cover image"""
        logger.info(f"[Apilot] Getting {video_type} video")
        try:
            logger.info(f"[Apilot] Making {video_type} video request to {url}")

            # 首先尝试获取JSON数据，与原版保持一致
            payload = "format=json"
            headers = {'Content-Type': "application/x-www-form-urlencoded"}

            # 使用requests库发送POST请求获取JSON数据
            response = requests.post(url, headers=headers, data=payload)

            if response.status_code == 200:
                try:
                    # 尝试解析JSON响应
                    video_info = response.json()

                    if isinstance(video_info, dict) and video_info.get('code') == 200:
                        # 从JSON响应中提取视频URL
                        video_url = video_info.get('data')

                        if video_url and self.is_valid_url(video_url):
                            logger.info(f"[Apilot] Successfully got {video_type} video URL: {video_url}")

                            # 下载视频内容
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                'Accept': 'video/mp4, video/*',
                                'Referer': referer
                            }

                            # 使用aiohttp下载视频
                            async with aiohttp.ClientSession() as session:
                                async with session.get(video_url, headers=headers, timeout=30) as video_response:
                                    if video_response.status == 200:
                                        # 检查是否是视频内容
                                        content_type = video_response.headers.get('Content-Type', '')
                                        if 'video' in content_type or 'mp4' in content_type:
                                            video_data = await video_response.read()
                                            logger.info(f"[Apilot] Successfully downloaded {video_type} video, size: {len(video_data)} bytes")

                                            # 创建临时文件保存视频
                                            temp_dir = Path("temp")
                                            temp_dir.mkdir(exist_ok=True)
                                            timestamp = int(time.time())
                                            video_path = temp_dir / f"{video_type}_{timestamp}.mp4"

                                            with open(video_path, 'wb') as f:
                                                f.write(video_data)

                                            # 提取视频首帧作为封面
                                            cover_data = None
                                            try:
                                                # 使用ffmpeg提取第一帧，与VideoSender保持一致
                                                temp_dir = "temp_thumbnails"  # 创建临时文件夹
                                                os.makedirs(temp_dir, exist_ok=True)
                                                thumbnail_path = os.path.join(temp_dir, f"temp_thumbnail_{int(time.time())}.jpg")

                                                # 执行ffmpeg命令提取第一帧
                                                process = subprocess.run([
                                                    "ffmpeg",
                                                    "-i", str(video_path),
                                                    "-ss", "00:00:01",  # 从视频的第 1 秒开始提取，与VideoDemand保持一致
                                                    "-vframes", "1",
                                                    thumbnail_path,
                                                    "-y"  # 如果文件存在，覆盖
                                                ], check=False, capture_output=True)

                                                if process.returncode != 0:
                                                    logger.error(f"[Apilot] ffmpeg 执行失败: {process.stderr.decode()}")
                                                    cover_data = None
                                                else:
                                                    # 读取生成的缩略图
                                                    if os.path.exists(thumbnail_path):
                                                        with open(thumbnail_path, "rb") as image_file:
                                                            image_data = image_file.read()
                                                            image_base64 = base64.b64encode(image_data).decode("utf-8")
                                                            cover_data = image_base64
                                                            logger.info(f"[Apilot] Successfully extracted video cover, base64 size: {len(cover_data)} characters")
                                                    else:
                                                        logger.error(f"[Apilot] 缩略图文件不存在: {thumbnail_path}")
                                                        cover_data = None
                                            except Exception as cover_error:
                                                logger.error(f"[Apilot] Exception in extracting video cover: {str(cover_error)}")
                                                cover_data = None
                                            finally:
                                                # 清理临时文件
                                                if 'temp_dir' in locals() and os.path.exists(temp_dir):
                                                    try:
                                                        shutil.rmtree(temp_dir, ignore_errors=True)  # 递归删除临时文件夹
                                                    except Exception as cleanup_error:
                                                        logger.error(f"[Apilot] 清理缩略图临时文件失败: {cleanup_error}")

                                            # 清理视频临时文件
                                            try:
                                                if os.path.exists(str(video_path)):
                                                    os.remove(str(video_path))
                                            except Exception as cleanup_error:
                                                logger.error(f"[Apilot] Failed to clean up video file: {str(cleanup_error)}")

                                            # 将视频数据也转换为base64编码的字符串
                                            video_base64 = base64.b64encode(video_data).decode("utf-8")
                                            logger.info(f"[Apilot] Video converted to base64, size: {len(video_base64)} characters")

                                            # 返回视频和封面的base64字符串
                                            return {"video": video_base64, "cover": cover_data}
                                        else:
                                            logger.error(f"[Apilot] {video_type} video response is not a video: {content_type}")
                                            # 如果不是视频，返回URL
                                            return video_url
                                    else:
                                        logger.error(f"[Apilot] Failed to download {video_type} video, status code: {video_response.status}")
                                        # 如果下载失败，返回URL
                                        logger.info(f"[Apilot] Falling back to returning URL: {video_url}")
                                        return video_url
                        else:
                            logger.error(f"[Apilot] Invalid video URL: {video_url}")
                            return f"获取{video_type}视频失败，请稍后再试"
                    else:
                        logger.error(f"[Apilot] Invalid JSON response: {video_info}")
                        return f"获取{video_type}视频失败，请稍后再试"
                except ValueError:
                    # 如果响应不是JSON，尝试直接下载视频
                    logger.error(f"[Apilot] Response is not JSON, trying to download video directly")
                    return await self._download_video_directly(url, video_type, referer)
            else:
                logger.error(f"[Apilot] Failed to get {video_type} video info, status code: {response.status_code}")
                return f"获取{video_type}视频失败，请稍后再试"
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_{video_type}: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取{video_type}视频时出错: {str(e)}"

    async def _download_video_directly(self, url, video_type, referer="https://api.yujn.cn/"):
        """Directly download video without JSON parsing"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'video/mp4, video/*',
                'Referer': referer
            }

            # 使用aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:  # 视频可能较大，增加超时时间
                    if response.status == 200:
                        # 检查是否是视频内容
                        content_type = response.headers.get('Content-Type', '')
                        if 'video' in content_type or 'mp4' in content_type:
                            video_data = await response.read()
                            logger.info(f"[Apilot] Successfully downloaded {video_type} video directly, size: {len(video_data)} bytes")

                            # 创建临时文件保存视频
                            temp_dir = Path("temp")
                            temp_dir.mkdir(exist_ok=True)
                            timestamp = int(time.time())
                            video_path = temp_dir / f"{video_type}_{timestamp}.mp4"

                            with open(video_path, 'wb') as f:
                                f.write(video_data)

                            # 提取视频首帧作为封面
                            cover_data = None
                            try:
                                # 使用ffmpeg提取第一帧，与VideoSender保持一致
                                temp_dir = "temp_thumbnails"  # 创建临时文件夹
                                os.makedirs(temp_dir, exist_ok=True)
                                thumbnail_path = os.path.join(temp_dir, f"temp_thumbnail_{int(time.time())}.jpg")

                                # 执行ffmpeg命令提取第一帧
                                process = subprocess.run([
                                    "ffmpeg",
                                    "-i", str(video_path),
                                    "-ss", "00:00:01",  # 从视频的第 1 秒开始提取，与VideoDemand保持一致
                                    "-vframes", "1",
                                    thumbnail_path,
                                    "-y"  # 如果文件存在，覆盖
                                ], check=False, capture_output=True)

                                if process.returncode != 0:
                                    logger.error(f"[Apilot] ffmpeg 执行失败: {process.stderr.decode()}")
                                    cover_data = None
                                else:
                                    # 读取生成的缩略图
                                    if os.path.exists(thumbnail_path):
                                        with open(thumbnail_path, "rb") as image_file:
                                            image_data = image_file.read()
                                            image_base64 = base64.b64encode(image_data).decode("utf-8")
                                            cover_data = image_base64
                                            logger.info(f"[Apilot] Successfully extracted video cover, base64 size: {len(cover_data)} characters")
                                    else:
                                        logger.error(f"[Apilot] 缩略图文件不存在: {thumbnail_path}")
                                        cover_data = None
                            except Exception as cover_error:
                                logger.error(f"[Apilot] Exception in extracting video cover: {str(cover_error)}")
                                cover_data = None
                            finally:
                                # 清理临时文件
                                if 'temp_dir' in locals() and os.path.exists(temp_dir):
                                    try:
                                        shutil.rmtree(temp_dir, ignore_errors=True)  # 递归删除临时文件夹
                                    except Exception as cleanup_error:
                                        logger.error(f"[Apilot] 清理缩略图临时文件失败: {cleanup_error}")

                            # 清理视频临时文件
                            try:
                                if os.path.exists(str(video_path)):
                                    os.remove(str(video_path))
                            except Exception as cleanup_error:
                                logger.error(f"[Apilot] Failed to clean up video file: {str(cleanup_error)}")

                            # 将视频数据也转换为base64编码的字符串
                            video_base64 = base64.b64encode(video_data).decode("utf-8")
                            logger.info(f"[Apilot] Video converted to base64, size: {len(video_base64)} characters")

                            # 返回视频和封面的base64字符串
                            return {"video": video_base64, "cover": cover_data}
                        else:
                            logger.error(f"[Apilot] {video_type} video response is not a video: {content_type}")
                            # 如果不是视频，返回URL
                            return url
                    else:
                        logger.error(f"[Apilot] Failed to download {video_type} video, status code: {response.status}")
                        # 如果下载失败，返回URL
                        logger.info(f"[Apilot] Falling back to returning URL: {url}")
                        return url
        except Exception as e:
            logger.error(f"[Apilot] Exception in _download_video_directly for {video_type}: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取{video_type}视频时出错: {str(e)}"

    async def _get_video_url_only(self, url, video_type):
        """Get only the video URL without downloading"""
        logger.info(f"[Apilot] Getting {video_type} video URL only")
        try:
            # 首先尝试获取JSON数据
            payload = "format=json"
            headers = {'Content-Type': "application/x-www-form-urlencoded"}

            # 使用requests库发送POST请求获取JSON数据
            response = requests.post(url, headers=headers, data=payload)

            if response.status_code == 200:
                try:
                    # 尝试解析JSON响应
                    video_info = response.json()

                    if isinstance(video_info, dict) and video_info.get('code') == 200:
                        # 从JSON响应中提取视频URL
                        video_url = video_info.get('data')

                        if video_url and self.is_valid_url(video_url):
                            logger.info(f"[Apilot] Successfully got {video_type} video URL: {video_url}")
                            return video_url
                        else:
                            logger.error(f"[Apilot] Invalid video URL: {video_url}")
                            return f"获取{video_type}视频失败，请稍后再试"
                    else:
                        logger.error(f"[Apilot] Invalid JSON response: {video_info}")
                        return f"获取{video_type}视频失败，请稍后再试"
                except ValueError:
                    # 如果响应不是JSON，返回错误信息
                    logger.error(f"[Apilot] Response is not JSON")
                    return f"获取{video_type}视频失败，请稍后再试"
            else:
                logger.error(f"[Apilot] Failed to get {video_type} video info, status code: {response.status_code}")
                return f"获取{video_type}视频失败，请稍后再试"
        except Exception as e:
            logger.error(f"[Apilot] Exception in get_{video_type}: {str(e)}")
            logger.error(f"[Apilot] Exception traceback: {traceback.format_exc()}")
            return f"获取{video_type}视频时出错: {str(e)}"

    async def get_xjjsp(self):
        """Get beautiful girl videos with cover image"""
        return await self._get_video_url_only(self.xjjsp_api_url, "xjjsp")

    async def get_yzsp(self):
        """Get foot videos with cover image"""
        return await self._get_video_url_only(self.yzsp_api_url, "yzsp")

    async def get_hssp(self):
        """Get black stockings videos with cover image"""
        return await self._get_video_url_only(self.hssp_api_url, "hssp")

    async def get_cos(self):
        """Get cosplay videos with cover image"""
        return await self._get_video_url_only(self.cos_api_url, "cos")

    async def get_ddsp(self):
        """Get suspender videos with cover image"""
        return await self._get_video_url_only(self.ddsp_api_url, "ddsp")

    async def get_jksp(self):
        """Get JK videos with cover image"""
        return await self._get_video_url_only(self.jksp_api_url, "jksp")

    async def get_llsp(self):
        """Get loli videos with cover image"""
        return await self._get_video_url_only(self.llsp_api_url, "llsp")

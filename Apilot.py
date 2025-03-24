import random
import plugins
import requests
import re
import json
import io
from urllib.parse import urlparse
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel import channel
from common.log import logger
from plugins import *
from datetime import datetime, timedelta
import time
import os
from requests_html import HTMLSession

BASE_URL_VVHAN = "https://api.vvhan.com/api/"
BASE_URL_ALAPI = "https://v3.alapi.cn/api/"


@plugins.register(
    name="Apilot",
    desire_priority=88,
    hidden=False,
    desc="A plugin to handle specific keywords",
    version="1.0",
    author="sofs2005",
)
class Apilot(Plugin):
    def __init__(self):
        super().__init__()
        try:
            self.conf = super().load_config()
            self.condition_2_and_3_cities = None  # 天气查询，存储重复城市信息，Initially set to None
            if not self.conf:
                logger.warn("[Apilot] inited but alapi_token not found in config")
                self.alapi_token = None # Setting a default value for alapi_token
                self.morning_news_text_enabled = False
            else:
                logger.info("[Apilot] inited and alapi_token loaded successfully")
                self.alapi_token = self.conf["alapi_token"]
                try:
                    self.morning_news_text_enabled = self.conf["morning_news_text_enabled"]
                except:
                    self.morning_news_text_enabled = False
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        except Exception as e:
            raise self.handle_error(e, "[Apiot] init failed, ignore ")

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT
        ]:
            return
        content = e_context["context"].content.strip()
        logger.debug("[Apilot] on_handle_context. content: %s" % content)

        if content == "早报":
            news = self.get_morning_news(self.alapi_token, self.morning_news_text_enabled)
            reply_type = ReplyType.IMAGE if isinstance(news, io.BytesIO) else ReplyType.TEXT
            reply = self.create_reply(reply_type, news)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return
        if content == "摸鱼":
            moyu = self.get_moyu_calendar()
            reply_type = ReplyType.IMAGE_URL if self.is_valid_url(moyu) else ReplyType.TEXT
            reply = self.create_reply(reply_type, moyu)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return

        if content == "摸鱼视频":
            moyu = self.get_moyu_calendar_video()
            reply_type = ReplyType.VIDEO_URL if self.is_valid_url(moyu) else ReplyType.TEXT
            reply = self.create_reply(reply_type, moyu)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return

        if content == "八卦":
            bagua = self.get_mx_bagua()
            reply_type = ReplyType.IMAGE_URL if self.is_valid_url(bagua) else ReplyType.TEXT
            reply = self.create_reply(reply_type, bagua)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return
            
        if content == "白丝图片":
            bstp = self.get_mx_bstp()
            reply_type = ReplyType.IMAGE_URL if self.is_valid_url(bstp) else ReplyType.TEXT
            reply = self.create_reply(reply_type, bstp)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return

        if content == "黑丝图片":
            hstp = self.get_mx_hstp()
            reply_type = ReplyType.IMAGE_URL if self.is_valid_url(hstp) else ReplyType.TEXT
            reply = self.create_reply(reply_type, hstp)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return

        if content == "玉足视频":
            yzsp = self.get_yzsp()
            reply_type = ReplyType.VIDEO_URL if self.is_valid_url(yzsp) else ReplyType.TEXT
            reply = self.create_reply(reply_type, yzsp)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return
        
        if content == "黑丝视频":
            hssp = self.get_hssp()
            reply_type = ReplyType.VIDEO_URL if self.is_valid_url(hssp) else ReplyType.TEXT
            reply = self.create_reply(reply_type, hssp)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return
        
        if content == "cos视频":
            cos = self.get_cos()
            reply_type = ReplyType.VIDEO_URL if self.is_valid_url(cos) else ReplyType.TEXT
            reply = self.create_reply(reply_type, cos)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return        
        
        if content == "吊带视频":
            ddsp = self.get_ddsp()
            reply_type = ReplyType.VIDEO_URL if self.is_valid_url(ddsp) else ReplyType.TEXT
            reply = self.create_reply(reply_type, ddsp)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return 
                  
        if content == "JK视频":
            jksp = self.get_jksp()
            reply_type = ReplyType.VIDEO_URL if self.is_valid_url(jksp) else ReplyType.TEXT
            reply = self.create_reply(reply_type, jksp)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return    
                
        if content == "萝莉视频":
            llsp = self.get_llsp()
            reply_type = ReplyType.VIDEO_URL if self.is_valid_url(llsp) else ReplyType.TEXT
            reply = self.create_reply(reply_type, llsp)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return                 
        
        if content == "小姐姐视频":
            xjjsp = self.get_xjjsp()
            reply_type = ReplyType.VIDEO_URL if self.is_valid_url(xjjsp) else ReplyType.TEXT
            reply = self.create_reply(reply_type, xjjsp)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return  

        if content == "毒鸡汤":
            dujitang = self.get_soul_dujijtang(self.alapi_token)
            reply = self.create_reply( ReplyType.TEXT, dujitang)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS #事件结束，并跳过处理context的默认逻辑

        history_match = re.match(r"^历史上的今天(\d+)月(\d+)日", content)
        if content == "历史上的今天" or history_match:
            month, day = '', ''
            if history_match:
                month, day = history_match.group(1), history_match.group(2)
            history_event = self.get_today_on_history(self.alapi_token, month, day)
            reply = self.create_reply(ReplyType.TEXT, history_event)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS # 事件结束，并跳过处理context的默认逻辑

        if content == '舔狗':
            dog_diary = self.get_dog_diary(self.alapi_token)
            reply = self.create_reply(ReplyType.TEXT, dog_diary)
            e_context['reply'] = reply
            e_context.action = EventAction.BREAK_PASS # 事件结束， 并跳过处理context的默认逻辑

        if content == '一言':
            hitokoto = self.get_hitokoto(self.alapi_token)
            reply = self.create_reply(ReplyType.TEXT, hitokoto)
            e_context['reply'] = reply
            e_context.action = EventAction.BREAK_PASS #事件结束，并跳过处理context默认逻辑

        horoscope_match = re.match(r'^([\u4e00-\u9fa5]{2}座)$', content)
        if horoscope_match:
            if content in ZODIAC_MAPPING:
                zodiac_english = ZODIAC_MAPPING[content]
                content = self.get_horoscope(self.alapi_token, zodiac_english)
                reply = self.create_reply(ReplyType.TEXT, content)
            else:
                reply = self.create_reply(ReplyType.TEXT, "请重新输入星座名称")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return

        hot_trend_match = re.search(r'(.{1,6})热榜$', content)
        if hot_trend_match:
            hot_trends_type = hot_trend_match.group(1).strip()  # 提取匹配的组并去掉可能的空格
            content = self.get_hot_trends(hot_trends_type)
            reply = self.create_reply(ReplyType.TEXT, content)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return


        # 天气查询
        weather_match = re.match(r'^(?:(.{2,7}?)(?:市|县|区|镇)?|(\d{7,9}))(:?今天|明天|后天|7天|七天)?(?:的)?天气$', content)
        if weather_match:
            # 如果匹配成功，提取第一个捕获组
            city_or_id = weather_match.group(1) or weather_match.group(2)
            date = weather_match.group(3)
            if not self.alapi_token:
                self.handle_error("alapi_token not configured", "天气请求失败")
                reply = self.create_reply(ReplyType.TEXT, "请先配置alapi的token")
            else:
                content = self.get_weather(self.alapi_token, city_or_id, date, content)
                reply = self.create_reply(ReplyType.TEXT, content)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            return

    def get_help_text(self, verbose=False, **kwargs):
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
        help_text += '  ☠️ 心灵毒鸡汤: 发送"毒鸡汤"获取心灵毒鸡汤。\n'
        help_text += '  ☃️ 历史上的今天: 发送"历史上的今天"or"历史上的今天x月x日"获取历史事件\n'
        help_text += '  🐕‍🦺 舔狗日记: 发送"舔狗"获取舔狗日记\n'
        help_text += '  🎞️ Hitokoto一言: 发送"一言"获取Hitokoto一言\n'
        help_text += '  📸 图片视频: 发送"白丝图片"、"黑丝图片"、"玉足视频"等获取相关内容\n'

        # 查询类
        help_text += "\n🔍 查询工具：\n"
        help_text += '  🌦️ 天气: 发送"城市+天气"查天气，如"北京天气"。\n'
        help_text += '  🌌 星座: 发送星座名称查看今日运势，如"白羊座"。\n'

        return help_text

    def get_hitokoto(self, alapi_token):
        url = BASE_URL_ALAPI + "hitokoto"
        hitokoto_type = 'abcdefghijkl'
        random_type = random.randint(0, len(hitokoto_type) - 1)
        payload = {
            "token": alapi_token,
            "type": hitokoto_type[random_type]
        }
        headers = {"Content-Type": "application/json"}
        try:
            hitokoto_data = self.make_request(url, method="POST", headers=headers, json_data=payload)
            if isinstance(hitokoto_data, dict) and hitokoto_data.get("code") == 200:
                data = hitokoto_data["data"]
                format_data = (
                    f"【Hitokoto一言】\n"
                    f"🎆{data['hitokoto']}\n"
                    f"🎐type: {hitokoto_type_dict[hitokoto_type[random_type]]}\n"
                    f"🥷author: {data['from']}"
                )
                return format_data
            else:
                return self.handle_error(hitokoto_data, "出错啦，稍后再试")
        except Exception as e:
            return self.handle_error(e, "出错啦，稍后再试~")

    def get_dog_diary(self, alapi_token):
        url = BASE_URL_ALAPI + "dog"
        payload = {
            "token": alapi_token,
            "format": 'json'
        }
        headers = {"Content-Type": "application/json"}
        try:
            dog_diary_data = self.make_request(url, method='POST', headers=headers, json_data=payload)
            if isinstance(dog_diary_data, dict) and dog_diary_data.get('code') == 200:
                data = dog_diary_data['data']['content']
                format_output = (
                    "【（づ￣3￣）づ╭❤️～舔狗日记】  \n  "
                    f"  🐶{data}"
                )
                return format_output
            else:
                return self.handle_error(dog_diary_data, "出错啦，稍后再试~")

        except Exception as e:
            return self.handle_error(e, "出错啦，稍后再试~")

    def get_today_on_history(self, alapi_token, month = "", day = ""):
        url = BASE_URL_ALAPI + "eventHistory"
        payload = {
            "token": alapi_token,
            "month": month,
            "day": day
        }
        headers = {"Content-Type": "application/json"}
        try:
            history_event_data = self.make_request(url, method="POST", headers=headers, json_data=payload)
            if isinstance(history_event_data, dict) and history_event_data.get('code') == 200:
                current_date = ""
                if month and day:
                    current_date = f"{month}月{day}日"
                else:
                    today = datetime.now()
                    current_date = today.strftime("%m月%d日")
                
                format_output = [f"【📆 历史上的今天 {current_date} 📆】\n"]
                data = history_event_data['data']
                history_count = len(data)
                
                # 随机选择历史事件
                output_count = random.randint(6, 10)  # 随机选择6-10条事件
                selected_indices = set()
                
                # 设置消息长度限制
                total_length = len(format_output[0])
                message_limit = 2000  # 设置消息长度限制（微信单条消息大约2000字左右）
                
                # 随机选择并添加事件，直到达到数量或长度限制
                attempt_count = 0
                while len(selected_indices) < min(output_count, history_count) and attempt_count < 50:
                    attempt_count += 1
                    idx = random.randint(0, history_count - 1)
                    if idx in selected_indices:
                        continue
                    
                    event = data[idx]
                    # 提取年份显示为单独的标签
                    year = event['date'].split('年')[0] if '年' in event['date'] else ""
                    year_display = f"📅 {year}" if year else ""
                    
                    # 截断过长的描述
                    desc = event['desc']
                    if len(desc) > 60:  # 缩短描述长度
                        desc = desc[:57] + "..."
                    
                    # 使用更美观的emoji和格式
                    history = (
                        f"🔹 事件 {len(selected_indices) + 1}: {event['title']}\n"
                        f"   {year_display}  📍 {event['date']}\n"
                        f"   📝 {desc}\n"
                    )
                    
                    # 检查添加当前事件后消息是否会超出长度限制
                    if total_length + len(history) + 50 > message_limit:  # 预留50字符给提示信息
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
                return self.handle_error(history_event_data, "出错啦，稍后再试~")

        except Exception as e:
            return self.handle_error(e, "出错啦，稍后再试~")

    def get_soul_dujijtang(self, alapi_token):
        if alapi_token:
            url = BASE_URL_ALAPI + "soul"
            payload = {"token": alapi_token}
            headers = {'Content-Type': "application/json"}
            try:
                soul_data = self.make_request(url, method="POST", headers=headers, json_data=payload)
                if isinstance(soul_data, dict) and soul_data.get('code') == 200:
                    data = soul_data['data']['content']
                    # 格式化并返回 ALAPI 提供的心灵毒鸡汤信息
                    result = (
                        f"💡【今日心灵毒鸡汤】\n{data}\n"
                    )
                    return result
                else:
                    return self.handle_error(soul_data, "心灵毒鸡汤获取信息获取失败，请检查 token 是否有误")

            except Exception as e:
                return self.handle_error(e, "出错啦，稍后再试")

        else:
            return self.handle_error('',"alapi_token缺失")


    def get_morning_news(self, alapi_token, morning_news_text_enabled):
        if not alapi_token:
            url = "https://api.03c3.cn/api/zb"  # 修改为更稳定的API
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
            try:
                morning_news_info = self.make_request(url, method="GET", headers=headers)
                if isinstance(morning_news_info, dict) and morning_news_info.get('code') == 200:
                    if morning_news_text_enabled:
                        # 提取并格式化新闻
                        news_list = morning_news_info.get('data', {}).get('news', [])
                        if news_list:
                            formatted_news = f"☕ 今日早报\n\n"
                            for idx, news in enumerate(news_list, 1):
                                formatted_news += f"{idx}. {news}\n"
                            return f"{formatted_news}\n图片链接：{morning_news_info.get('data', {}).get('imageurl', '')}"
                    else:
                        # 下载图片而不是返回URL
                        image_url = morning_news_info.get('data', {}).get('imageurl')
                        if image_url:
                            return self.download_image(image_url)
                return self.handle_error(morning_news_info, '早报信息获取失败，可配置"alapi token"切换至 Alapi 服务，或者稍后再试')
            except Exception as e:
                return self.handle_error(e, "出错啦，稍后再试")
        else:
            url = BASE_URL_ALAPI + "zaobao"
            data = {
                "token": alapi_token,
                "format": "json"
            }
            headers = {'Content-Type': "application/x-www-form-urlencoded"}
            try:
                morning_news_info = self.make_request(url, method="POST", headers=headers, data=data)
                if isinstance(morning_news_info, dict) and morning_news_info.get('code') == 200:
                    img_url = morning_news_info['data']['image']
                    if morning_news_text_enabled:
                        news_list = morning_news_info['data']['news']
                        weiyu = morning_news_info['data']['weiyu']

                        # 整理新闻为有序列表
                        formatted_news = f"☕ {morning_news_info['data']['date']}  今日早报\n"
                        formatted_news = formatted_news + "\n".join(news_list)
                        # 组合新闻和微语
                        return f"{formatted_news}\n\n{weiyu}\n\n 图片url：{img_url}"
                    else:
                        # 下载图片而不是返回URL
                        return self.download_image(img_url)
                else:
                    return self.handle_error(morning_news_info, "早报获取失败，请检查 token 是否有误")
            except Exception as e:
                return self.handle_error(e, "早报获取失败")

    def download_image(self, image_url):
        """使用requests-html模拟浏览器下载图片"""
        try:
            # 首先需要安装requests-html库
            # pip install requests-html
            from requests_html import HTMLSession
            import random
            import time
            from urllib.parse import urlparse
            
            # 创建会话
            session = HTMLSession()
            
            # 多种User-Agent随机选择
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
            ]
            
            # 解析URL获取域名
            parsed_url = urlparse(image_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # 先访问首页获取cookies
            logger.info(f"[早报] 先访问主域名: {base_url}")
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            session.get(base_url, headers=headers)
            
            # 随机延迟模拟人类行为
            time.sleep(random.uniform(1, 2))
            
            # 访问图片URL
            logger.info(f"[早报] 下载图片: {image_url}")
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": base_url,
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "same-origin",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache"
            }
            
            response = session.get(image_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                img_io = io.BytesIO(response.content)
                img_io.seek(0)
                logger.info(f"[早报] 图片下载成功: {len(response.content)/1024:.2f} KB")
                return img_io
            else:
                logger.error(f"[早报] 请求失败，状态码: {response.status_code}")
                return self._try_backup_apis(image_url)
            
        except Exception as e:
            logger.error(f"[早报] 模拟浏览器下载失败: {e}")
            return self._try_backup_apis(image_url)

    def _try_backup_apis(self, original_url=None):
        """尝试从备用API获取早报图片"""
        try:
            logger.info("尝试使用备用API获取早报图片")
            
            # 备用API列表
            backup_apis = [
                "https://api.03c3.cn/api/zb",
                "https://api.vvhan.com/api/60s",
                "https://api.pearktrue.cn/api/60s/image"
            ]
            
            for api_url in backup_apis:
                try:
                    logger.info(f"尝试从备用API获取: {api_url}")
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
                    }
                    
                    # 判断API是否返回JSON数据
                    if "api/zb" in api_url or "api/60s" in api_url:
                        response = requests.get(api_url, headers=headers, timeout=10)
                        response.raise_for_status()
                        
                        # 检查是否返回JSON数据
                        if response.headers.get('Content-Type', '').startswith('application/json'):
                            data = response.json()
                            if "api/zb" in api_url and 'data' in data and 'imageurl' in data['data']:
                                img_url = data['data']['imageurl']
                                img_response = requests.get(img_url, headers=headers, timeout=10)
                                img_response.raise_for_status()
                                img_io = io.BytesIO(img_response.content)
                                img_io.seek(0)
                                logger.info(f"成功从备用API {api_url} 获取早报图片")
                                return img_io
                            elif "api/60s" in api_url and 'imgUrl' in data:
                                img_url = data['imgUrl']
                                img_response = requests.get(img_url, headers=headers, timeout=10)
                                img_response.raise_for_status()
                                img_io = io.BytesIO(img_response.content)
                                img_io.seek(0)
                                logger.info(f"成功从备用API {api_url} 获取早报图片")
                                return img_io
                        # 如果是直接返回图片
                        else:
                            img_io = io.BytesIO(response.content)
                            img_io.seek(0)
                            logger.info(f"成功从备用API {api_url} 获取早报图片")
                            return img_io
                    # 直接返回图片的API
                    else:
                        response = requests.get(api_url, headers=headers, timeout=10)
                        response.raise_for_status()
                        img_io = io.BytesIO(response.content)
                        img_io.seek(0)
                        logger.info(f"成功从备用API {api_url} 获取早报图片")
                        return img_io
                        
                except Exception as e:
                    logger.warning(f"从备用API {api_url} 获取早报图片失败: {e}")
                    continue
            
            # 如果所有备用API都失败
            logger.error("所有备用API均获取失败")
            return self.handle_error("所有图片来源均获取失败", "下载图片失败，请稍后再试")
        except Exception as e:
            logger.error(f"尝试备用API失败: {e}")
            return self.handle_error("尝试备用API失败", "下载图片失败，请稍后再试")

    def get_moyu_calendar(self):
        url = BASE_URL_VVHAN + "moyu?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        moyu_calendar_info = self.make_request(url, method="POST", headers=headers, data=payload)
        # 验证请求是否成功
        if isinstance(moyu_calendar_info, dict) and moyu_calendar_info['success']:
            return moyu_calendar_info['url']
        else:
            url = "https://dayu.qqsuu.cn/moyuribao/apis.php?type=json"
            payload = "format=json"
            headers = {'Content-Type': "application/x-www-form-urlencoded"}
            moyu_calendar_info = self.make_request(url, method="POST", headers=headers, data=payload)
            if isinstance(moyu_calendar_info, dict) and moyu_calendar_info['code'] == 200:
                moyu_pic_url = moyu_calendar_info['data']
                if self.is_valid_image_url(moyu_pic_url):
                    return moyu_pic_url
                else:
                    return "周末无需摸鱼，愉快玩耍吧"
            else:
                return '暂无可用"摸鱼"服务，认真上班'

    def get_moyu_calendar_video(self):
        url = "https://dayu.qqsuu.cn/moyuribaoshipin/apis.php?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        moyu_calendar_info = self.make_request(url, method="POST", headers=headers, data=payload)
        logger.debug(f"[Apilot] moyu calendar video response: {moyu_calendar_info}")
        # 验证请求是否成功
        if isinstance(moyu_calendar_info, dict) and moyu_calendar_info['code'] == 200:
            moyu_video_url = moyu_calendar_info['data']
            if self.is_valid_image_url(moyu_video_url):
                return moyu_video_url

        # 未成功请求到视频时，返回提示信息
        return "视频版没了，看看文字版吧"

    def get_horoscope(self, alapi_token, astro_sign: str, time_period: str = "today"):
        if not alapi_token:
            url = BASE_URL_VVHAN + "horoscope"
            params = {
                'type': astro_sign,
                'time': time_period
            }
            try:
                horoscope_data = self.make_request(url, "GET", params=params)
                if isinstance(horoscope_data, dict) and horoscope_data['success']:
                    data = horoscope_data['data']

                    result = (
                        f"{data['title']} ({data['time']}):\n\n"
                        f"💡【每日建议】\n宜：{data['todo']['yi']}\n忌：{data['todo']['ji']}\n\n"
                        f"📊【运势指数】\n"
                        f"总运势：{data['index']['all']}\n"
                        f"爱情：{data['index']['love']}\n"
                        f"工作：{data['index']['work']}\n"
                        f"财运：{data['index']['money']}\n"
                        f"健康：{data['index']['health']}\n\n"
                        f"🍀【幸运提示】\n数字：{data['luckynumber']}\n"
                        f"颜色：{data['luckycolor']}\n"
                        f"星座：{data['luckyconstellation']}\n\n"
                        f"✍【简评】\n{data['shortcomment']}\n\n"
                        f"📜【详细运势】\n"
                        f"总运：{data['fortunetext']['all']}\n"
                        f"爱情：{data['fortunetext']['love']}\n"
                        f"工作：{data['fortunetext']['work']}\n"
                        f"财运：{data['fortunetext']['money']}\n"
                        f"健康：{data['fortunetext']['health']}\n"
                    )

                    return result

                else:
                    return self.handle_error(horoscope_data, '星座信息获取失败，可配置"alapi token"切换至 Alapi 服务，或者稍后再试')

            except Exception as e:
                return self.handle_error(e, "出错啦，稍后再试")
        else:
            # 使用 ALAPI 的 URL 和提供的 token
            url = BASE_URL_ALAPI + "star"
            payload = f"token={alapi_token}&star={astro_sign}"
            headers = {'Content-Type': "application/x-www-form-urlencoded"}
            try:
                horoscope_data = self.make_request(url, method="POST", headers=headers, data=payload)
                if isinstance(horoscope_data, dict) and horoscope_data.get('code') == 200:
                    data = horoscope_data['data']['day']

                    # 格式化并返回 ALAPI 提供的星座信息
                    result = (
                        f"📅 日期：{data['date']}\n\n"
                        f"💡【每日建议】\n宜：{data['yi']}\n忌：{data['ji']}\n\n"
                        f"📊【运势指数】\n"
                        f"总运势：{data['all']}\n"
                        f"爱情：{data['love']}\n"
                        f"工作：{data['work']}\n"
                        f"财运：{data['money']}\n"
                        f"健康：{data['health']}\n\n"
                        f"🔔【提醒】：{data['notice']}\n\n"
                        f"🍀【幸运提示】\n数字：{data['lucky_number']}\n"
                        f"颜色：{data['lucky_color']}\n"
                        f"星座：{data['lucky_star']}\n\n"
                        f"✍【简评】\n总运：{data['all_text']}\n"
                        f"爱情：{data['love_text']}\n"
                        f"工作：{data['work_text']}\n"
                        f"财运：{data['money_text']}\n"
                        f"健康：{data['health_text']}\n"
                    )
                    return result
                else:
                    return self.handle_error(horoscope_data, "星座获取信息获取失败，请检查 token 是否有误")
            except Exception as e:
                return self.handle_error(e, "出错啦，稍后再试")

    def get_hot_trends(self, hot_trends_type):
        # 查找映射字典以获取API参数
        hot_trends_type_en = hot_trend_types.get(hot_trends_type, None)
        if hot_trends_type_en is not None:
            url = BASE_URL_VVHAN + "hotlist/" + hot_trends_type_en
            try:
                data = self.make_request(url, "GET", {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                })
                if isinstance(data, dict) and data['success'] == True:
                    output = []
                    topics = data['data']
                    output.append(f'更新时间：{data["update_time"]}\n')
                    for i, topic in enumerate(topics[:15], 1):
                        hot = topic.get('hot', '无热度参数, 0')
                        formatted_str = f"{i}. {topic['title']} ({hot} 浏览)\nURL: {topic['url']}\n"
                        output.append(formatted_str)
                    return "\n".join(output)
                else:
                    return self.handle_error(data, "热榜获取失败，请稍后再试")
            except Exception as e:
                return self.handle_error(e, "出错啦，稍后再试")
        else:
            supported_types = "/".join(hot_trend_types.keys())
            final_output = (
                f"👉 已支持的类型有：\n\n    {supported_types}\n"
                f"\n📝 请按照以下格式发送：\n    类型+热榜  例如：微博热榜"
            )
            return final_output

    def get_weather(self, alapi_token, city_or_id: str, date: str, content):
        url = BASE_URL_ALAPI + 'tianqi'
        isFuture = date in ['明天', '后天', '七天', '7天']
        if isFuture:
            url = BASE_URL_ALAPI + 'tianqi/seven'
        # 判断使用id还是city请求api
        if city_or_id.isnumeric():  # 判断是否为纯数字，也即是否为 city_id
            params = {
                'city_id': city_or_id,
                'token': f'{alapi_token}'
            }
        else:
            city_info = self.check_multiple_city_ids(city_or_id)
            if city_info:
                data = city_info['data']
                formatted_city_info = "\n".join(
                    [f"{idx + 1}) {entry['province']}--{entry['leader']}, ID: {entry['city_id']}"
                     for idx, entry in enumerate(data)]
                )
                return f'查询 <{city_or_id}> 具有多条数据：\n{formatted_city_info}\n请使用id查询，发送"id天气"'

            params = {
                'city': city_or_id,
                'token': f'{alapi_token}'
            }
        try:
            weather_data = self.make_request(url, "GET", params=params)
            if isinstance(weather_data, dict) and weather_data.get('code') == 200:
                data = weather_data['data']
                if isFuture:
                    formatted_output = []
                    for num, d in enumerate(data):
                        if num == 0:
                            formatted_output.append(f"🏙️ 城市: {d['city']} ({d['province']})\n")
                        if date == '明天' and num != 1:
                            continue
                        if date == '后天' and num != 2:
                            continue
                        basic_info = [
                            f"🕒 日期: {d['date']}",
                            f"🌞 天气: 🌞{d['wea_day']}| 🌛{d['wea_night']}",
                            f"🌡️ 温度: 🌞{d['temp_day']}℃| 🌛{d['temp_night']}℃",
                            f"🌅 日出/日落: {d['sunrise']} / {d['sunset']}",
                        ]
                        for i in d['index']:
                            basic_info.append(f"{i['name']}: {i['level']}")
                        formatted_output.append("\n".join(basic_info) + '\n')
                    return "\n".join(formatted_output)
                update_time = data['update_time']
                dt_object = datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S")
                formatted_update_time = dt_object.strftime("%m-%d %H:%M")
                # Basic Info
                if not city_or_id.isnumeric() and data['city'] not in content:  # 如果返回城市信息不是所查询的城市，重新输入
                    return "输入不规范，请输<国内城市+(今天|明天|后天|七天|7天)+天气>，比如 '广州天气'"
                formatted_output = []
                # 重新组织和分类天气信息
                # 1. 基本位置和时间信息
                location_info = (
                    f"🏙️ 城市: {data['city']} ({data['province']})\n"
                    f"🕒 更新: {formatted_update_time}\n"
                )
                
                # 2. 天气状况信息
                weather_info = (
                    f"🌦️ 天气: {data['weather']}\n"
                    f"🌡️ 温度: ↓{data['min_temp']}℃| 现{data['temp']}℃| ↑{data['max_temp']}℃\n"
                )
                
                # 3. 风力信息
                wind_info = (
                    f"🌬️ 风向: {data['wind']} | 风速: {data.get('wind_speed', 'N/A')} | 风力: {data.get('wind_power', 'N/A')}\n"
                )
                
                # 4. 环境指标分开显示
                humidity_info = f"💦 湿度: {data['humidity']}"
                visibility_info = f"👁️ 能见度: {data.get('visibility', 'N/A')}" 
                pressure_info = f"🔄 气压: {data.get('pressure', 'N/A')}"
                
                environment_info = f"{humidity_info} | {visibility_info} | {pressure_info}\n"
                
                # 5. 太阳信息
                sun_info = f"🌅 日出/日落: {data['sunrise']} / {data['sunset']}\n"
                
                # 组合所有信息
                formatted_output.append(location_info + weather_info + wind_info + environment_info + sun_info)

                # 空气质量信息
                if data.get('aqi'):
                    aqi_data = data['aqi']
                    air_level = aqi_data.get('air_level', '')
                    level_emoji = '🟢'  # 默认良好
                    if '轻度' in air_level:
                        level_emoji = '🟡'
                    elif '中度' in air_level:
                        level_emoji = '🟠'
                    elif '重度' in air_level:
                        level_emoji = '🔴'
                    elif '严重' in air_level:
                        level_emoji = '🟣'
                    
                    aqi_info = "💨 空气质量： \n"
                    aqi_info += (
                        f"{level_emoji} 质量指数: {aqi_data.get('air', 'N/A')} ({aqi_data.get('air_level', 'N/A')})\n"
                        f"😷 PM2.5: {aqi_data.get('pm25', 'N/A')} | PM10: {aqi_data.get('pm10', 'N/A')}\n"
                        f"⚗️ CO: {aqi_data.get('co', 'N/A')} | NO₂: {aqi_data.get('no2', 'N/A')} | SO₂: {aqi_data.get('so2', 'N/A')} | O₃: {aqi_data.get('o3', 'N/A')}\n"
                        f"💡 提示: {aqi_data.get('air_tips', 'N/A')}\n"
                    )
                    formatted_output.append(aqi_info)

                # 天气指标 Weather indicators
                weather_indicators = data.get('index')
                if weather_indicators:
                    indicators_info = '⚠️ 天气指标： \n'
                    for weather_indicator in weather_indicators:
                        # 根据指标类型选择合适的emoji
                        indicator_type = weather_indicator['type']
                        indicator_emoji = "🔍"  # 默认emoji
                        
                        if "diaoyu" in indicator_type:
                            indicator_emoji = "🎣"  # 钓鱼指数
                        elif "ganmao" in indicator_type:
                            indicator_emoji = "🤧"  # 感冒指数
                        elif "guoming" in indicator_type or "allergy" in indicator_type:
                            indicator_emoji = "😷"  # 过敏指数
                        elif "xiche" in indicator_type:
                            indicator_emoji = "🚗"  # 洗车指数
                        elif "yundong" in indicator_type:
                            indicator_emoji = "🏃"  # 运动指数
                        elif "ziwanxian" in indicator_type or "uv" in indicator_type:
                            indicator_emoji = "☀️"  # 紫外线指数
                        elif "chuanyi" in indicator_type:
                            indicator_emoji = "👕"  # 穿衣指数
                        elif "lvyou" in indicator_type:
                            indicator_emoji = "🏖️"  # 旅游指数
                        elif "daisan" in indicator_type:
                            indicator_emoji = "☂️"  # 带伞指数
                        
                        # 根据指标等级选择颜色emoji
                        level = weather_indicator['level']
                        level_emoji = "⚪"  # 默认白色
                        
                        if any(keyword in level for keyword in ["适宜", "良好", "最弱", "不需要", "不易"]):
                            level_emoji = "🟢"  # 绿色表示良好
                        elif any(keyword in level for keyword in ["较适宜", "中等", "弱", "偏高"]):
                            level_emoji = "🟡"  # 黄色表示中等
                        elif any(keyword in level for keyword in ["较不宜", "较强", "偏高", "少量"]):
                            level_emoji = "🟠"  # 橙色表示较差
                        elif any(keyword in level for keyword in ["不宜", "很强", "不建议", "高发", "易发", "极强"]):
                            level_emoji = "🔴"  # 红色表示不佳
                        
                        # 合并到一行显示
                        indicators_info += f"{indicator_emoji} {weather_indicator['name']} {level_emoji} {level}：{weather_indicator['content'][:60]}{'...' if len(weather_indicator['content']) > 60 else ''}\n\n"
                    
                    formatted_output.append(indicators_info)


                # Next 7 hours weather
                ten_hours_later = dt_object + timedelta(hours=10)

                future_weather = []
                for hour_data in data['hour']:
                    forecast_time_str = hour_data['time']
                    forecast_time = datetime.strptime(forecast_time_str, "%Y-%m-%d %H:%M:%S")

                    if dt_object < forecast_time <= ten_hours_later:
                        future_weather.append(f"     {forecast_time.hour:02d}:00 - {hour_data['wea']} - {hour_data['temp']}°C")

                future_weather_info = "⏳ 未来10小时的天气预报:\n" + "\n".join(future_weather)
                formatted_output.append(future_weather_info)

                # Alarm Info
                if data.get('alarm'):
                    alarm_info = "⚠️ 预警信息:\n"
                    for alarm in data['alarm']:
                        alarm_info += (
                            f"🔴 标题: {alarm['title']}\n"
                            f"🟠 等级: {alarm['level']}\n"
                            f"🟡 类型: {alarm['type']}\n"
                            f"🟢 提示: {alarm['tips']}\n"
                            f"🔵 内容: {alarm['content']}\n\n"
                        )
                    formatted_output.append(alarm_info)

                return "\n".join(formatted_output)
            else:
                return self.handle_error(weather_data, "获取失败，请查看服务器log")

        except Exception as e:
            return self.handle_error(e, "获取天气信息失败")

    def get_mx_bagua(self):
        url = "https://dayu.qqsuu.cn/mingxingbagua/apis.php?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        bagua_info = self.make_request(url, method="POST", headers=headers, data=payload)
        # 验证请求是否成功
        if isinstance(bagua_info, dict) and bagua_info['code'] == 200:
            bagua_pic_url = bagua_info["data"]
            if self.is_valid_image_url(bagua_pic_url):
                return bagua_pic_url
            else:
                return "周末不更新，请微博吃瓜"
        else:
            logger.error(f"错误信息：{bagua_info}")
            return "暂无明星八卦，吃瓜莫急"

    def make_request(self, url, method="GET", headers=None, params=None, data=None, json_data=None):
        try:
            if method.upper() == "GET":
                response = requests.request(method, url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.request(method, url, headers=headers, data=data, json=json_data)
            else:
                return {"success": False, "message": "Unsupported HTTP method"}

            return response.json()
        except Exception as e:
            return e


    def create_reply(self, reply_type, content):
        reply = Reply()
        reply.type = reply_type
        reply.content = content
        return reply

    def handle_error(self, error, message):
        logger.error(f"{message}，错误信息：{error}")
        return message

    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def is_valid_image_url(self, url):
        try:
            response = requests.head(url)  # Using HEAD request to check the URL header
            # If the response status code is 200, the URL exists and is reachable.
            return response.status_code == 200
        except requests.RequestException as e:
            # If there's an exception such as a timeout, connection error, etc., the URL is not valid.
            return False

    def load_city_conditions(self):
        if self.condition_2_and_3_cities is None:
            try:
                json_file_path = os.path.join(os.path.dirname(__file__), 'duplicate-citys.json')
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    self.condition_2_and_3_cities = json.load(f)
            except Exception as e:
                return self.handle_error(e, "加载condition_2_and_3_cities.json失败")


    def check_multiple_city_ids(self, city):
        self.load_city_conditions()
        city_info = self.condition_2_and_3_cities.get(city, None)
        if city_info:
            return city_info
        return None
    
    def get_yzsp(self):
        url = "https://api.xlb.one/api/jpmt?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        yzsp_info = self.make_request(url, method="POST", headers=headers, data=payload)
        if isinstance(yzsp_info, dict) and yzsp_info['code'] == 200:
            yzsp_url = yzsp_info['data']
            if self.is_valid_image_url(yzsp_url):
                return yzsp_url
        return "获取视频失败，请稍后再试"
            
    def get_hssp(self):
        url = "https://api.yujn.cn/api/heisis.php?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        hssp_info = self.make_request(url, method="POST", headers=headers, data=payload)
        if isinstance(hssp_info, dict) and hssp_info['code'] == 200:
            hssp_url = hssp_info['data']
            if self.is_valid_image_url(hssp_url):
                return hssp_url
        return "获取视频失败，请稍后再试"
            
    def get_cos(self):
        url = "https://api.xlb.one/api/COS?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        cos_info = self.make_request(url, method="POST", headers=headers, data=payload)
        if isinstance(cos_info, dict) and cos_info['code'] == 200:
            cos_url = cos_info['data']
            if self.is_valid_image_url(cos_url):
                return cos_url
        return "获取视频失败，请稍后再试"

    def get_ddsp(self):
        url = "https://api.xlb.one/api/diaodai?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        ddsp_info = self.make_request(url, method="POST", headers=headers, data=payload)
        if isinstance(ddsp_info, dict) and ddsp_info['code'] == 200:
            ddsp_url = ddsp_info['data']
            if self.is_valid_image_url(ddsp_url):
                return ddsp_url
        return "获取视频失败，请稍后再试"

    def get_jksp(self):
        url = "https://api.xlb.one/api/jksp?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        jksp_info = self.make_request(url, method="POST", headers=headers, data=payload)
        if isinstance(jksp_info, dict) and jksp_info['code'] == 200:
            jksp_url = jksp_info['data']
            if self.is_valid_image_url(jksp_url):
                return jksp_url
        return "获取视频失败，请稍后再试"

    def get_llsp(self):
        url = "https://api.xlb.one/api/luoli?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        llsp_info = self.make_request(url, method="POST", headers=headers, data=payload)
        if isinstance(llsp_info, dict) and llsp_info['code'] == 200:
            llsp_url = llsp_info['data']
            if self.is_valid_image_url(llsp_url):
                return llsp_url
        return "获取视频失败，请稍后再试"

    def get_xjjsp(self):
        url = "https://api.yujn.cn/api/zzxjj.php?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        xjjsp_info = self.make_request(url, method="POST", headers=headers, data=payload)
        if isinstance(xjjsp_info, dict) and xjjsp_info['code'] == 200:
            xjjsp_url = xjjsp_info['data']
            if self.is_valid_image_url(xjjsp_url):
                return xjjsp_url
        return "获取视频失败，请稍后再试"
        
    def get_mx_bstp(self):
        url = "https://api.xlb.one/api/baisi?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        bstp_info = self.make_request(url, method="POST", headers=headers, data=payload)
        # 验证请求是否成功
        if isinstance(bstp_info, dict) and bstp_info['code'] == 200:
            bstp_pic_url = bstp_info['image']
            if self.is_valid_image_url(bstp_pic_url):
                return bstp_pic_url
        logger.error(f"白丝图片获取失败，错误信息：{bstp_info}")
        return "获取图片失败，请稍后再试"
        
    def get_mx_hstp(self):
        url = "https://api.xlb.one/api/heisi?type=json"
        payload = "format=json"
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        hstp_info = self.make_request(url, method="POST", headers=headers, data=payload)
        # 验证请求是否成功
        if isinstance(hstp_info, dict) and hstp_info['code'] == 200:
            hstp_pic_url = hstp_info['image']
            if self.is_valid_image_url(hstp_pic_url):
                return hstp_pic_url
        logger.error(f"黑丝图片获取失败，错误信息：{hstp_info}")
        return "获取图片失败，请稍后再试"



ZODIAC_MAPPING = {
        '白羊座': 'aries',
        '金牛座': 'taurus',
        '双子座': 'gemini',
        '巨蟹座': 'cancer',
        '狮子座': 'leo',
        '处女座': 'virgo',
        '天秤座': 'libra',
        '天蝎座': 'scorpio',
        '射手座': 'sagittarius',
        '摩羯座': 'capricorn',
        '水瓶座': 'aquarius',
        '双鱼座': 'pisces'
    }

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

hitokoto_type_dict = {
    'a':'动画',
    'b':'漫画',
    'c':'游戏',
    'd':'文学',
    'e':'原创',
    'f':'来自网络',
    'g':'其他',
    'h':'影视',
    'i':'诗词',
    'j':'网易云',
    'k':'哲学',
    'l':'抖机灵'
}



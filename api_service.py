import os
import time
import requests
import logging
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('APIService')

class APIService:
    def __init__(self, max_retries=3):
        self.api_urls = [
            "https://api.dwo.cc/api/miss?type=json",
            "https://api.kuleu.com/api/xjj?type=json"
        ]
        self.current_api_index = 0
        self.max_retries = max_retries
        self.fail_count = 0
        self.switch_threshold = 2  # 连续失败2次后切换API
        
        # 从环境变量加载API密钥（如果有）
        self.api_key = os.environ.get('VIDEO_API_KEY', '')
        
        # 添加用户代理和其他必要的请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, */*',
            'Content-Type': 'application/json'
        }
        
        # 如果有API密钥，添加到请求头
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def get_video_link(self):
        """从API获取视频链接
        返回: 视频URL字符串，如果失败则返回None
        """
        retries = 0
        
        while retries < self.max_retries:
            try:
                current_api = self.api_urls[self.current_api_index]
                logger.info(f"尝试从API获取视频: {current_api}")
                
                # 发送GET请求获取视频数据
                response = requests.get(
                    current_api,
                    headers=self.headers,
                    timeout=10
                )
                
                # 检查响应状态码
                if response.status_code == 200:
                    # 尝试解析JSON响应
                    try:
                        data = response.json()
                        print(data)
                        video_url = self._extract_video_url(data)
                        
                        if video_url:
                            # 跟随重定向获取最终视频地址
                            final_url = self.follow_redirects(video_url)
                            
                            # 重置失败计数
                            self.fail_count = 0
                            retries = 0  # 重置重试计数
                            
                            return final_url
                        else:
                            logger.warning("无法从API响应中提取视频URL")
                            self.fail_count += 1
                            retries += 1
                    except json.JSONDecodeError:
                        # JSON解析失败，尝试直接从文本中提取URL
                        text = response.text
                        video_url = self._extract_url_from_text(text)
                        
                        if video_url:
                            # 跟随重定向获取最终视频地址
                            final_url = self.follow_redirects(video_url)
                            
                            # 重置失败计数
                            self.fail_count = 0
                            retries = 0  # 重置重试计数
                            
                            return final_url
                        else:
                            logger.warning("JSON解析失败且无法从文本中提取URL")
                            self.fail_count += 1
                            retries += 1
                else:
                    logger.error(f"API请求失败，状态码: {response.status_code}")
                    self.fail_count += 1
                    retries += 1
                
                # 检查是否需要切换API
                if self.fail_count >= self.switch_threshold:
                    self._switch_api()
                    
                # 指数退避策略
                wait_time = min(2 ** retries, 8)  # 最多等待8秒
                logger.info(f"获取视频链接失败，{wait_time}秒后重试 ({retries}/{self.max_retries})")
                time.sleep(wait_time)
                
            except requests.exceptions.ConnectionError as e:
                logger.error(f"API连接失败: {e}")
                self.fail_count += 1
                retries += 1
                time.sleep(2)
            except requests.exceptions.Timeout as e:
                logger.error(f"API请求超时: {e}")
                self.fail_count += 1
                retries += 1
                time.sleep(3)
            except Exception as e:
                logger.error(f"获取视频链接时发生未知错误: {e}")
                retries += 1
                time.sleep(1)
        
        logger.error("所有API请求尝试均失败，无法获取视频链接")
        return None
    
    def _switch_api(self):
        """切换到下一个可用的API"""
        if len(self.api_urls) > 1:
            self.current_api_index = (self.current_api_index + 1) % len(self.api_urls)
            logger.info(f"切换到备用API: {self.api_urls[self.current_api_index]}")
            self.fail_count = 0
    
    def _extract_video_url(self, data):
        """从解析后的JSON数据中提取视频URL
        根据不同API的响应格式进行适配
        """
        if isinstance(data, list) and len(data) > 0:
            video_data = data[0]
            # 尝试常见的键名
            for key in ["data", "url", "video_url", "link", "src","video"]:
                if key in video_data:
                    video_url = str(video_data[key]).strip()
                    if video_url:
                        return video_url
        elif isinstance(data, dict):
            # 尝试从字典的顶层键中提取
            for key in ["data", "url", "video_url", "link", "src","video"]:
                if key in data:
                    # 如果值是字典，递归查找
                    if isinstance(data[key], dict) or isinstance(data[key], list):
                        nested_url = self._extract_video_url(data[key])
                        if nested_url:
                            return nested_url
                    else:
                        video_url = str(data[key]).strip()
                        if video_url:
                            return video_url
        
        return None
    
    def _extract_url_from_text(self, text):
        """尝试从文本中直接提取URL（当JSON解析失败时使用）"""
        import re
        # 匹配常见的视频URL格式
        url_patterns = [
            r'https?://[^"\'\s]+?\.(mp4|mov|avi|mkv)',  # 常见视频文件扩展名
            r'https?://[^"]+?(?=")',  # 双引号包围的URL
            r'https?://[^\']+?(?=\')',  # 单引号包围的URL
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # 如果是第一个模式，matches是元组，取第一个元素
                if isinstance(matches[0], tuple):
                    return matches[0][0]
                else:
                    return matches[0]
        
        return None
    
    def follow_redirects(self, url):
        """跟随重定向获取最终视频地址
        参数: url - 原始视频链接
        返回: 最终视频链接字符串
        """
        try:
            logger.info(f"跟随重定向: {url}")
            session = requests.Session()
            # 不允许自动重定向，以便记录重定向过程
            response = session.get(url, allow_redirects=False, timeout=10)
            
            # 手动跟随重定向，最多5次
            redirect_count = 0
            max_redirects = 5
            
            while response.status_code in [301, 302, 303, 307, 308] and redirect_count < max_redirects:
                redirect_url = response.headers.get('Location')
                if redirect_url:
                    logger.info(f"重定向到: {redirect_url}")
                    response = session.get(redirect_url, allow_redirects=False, timeout=10)
                    redirect_count += 1
                else:
                    break
            
            # 返回最终URL或原始URL
            final_url = response.url if response.status_code < 400 else url
            logger.info(f"最终视频URL: {final_url}")
            return final_url
            
        except Exception as e:
            logger.error(f"跟随重定向失败: {e}")
            return url

# 测试代码
if __name__ == "__main__":
    print("开始测试API连接...")
    api_service = APIService(max_retries=5)
    
    # 测试API连接
    print(f"当前使用的API URL: {api_service.api_urls[api_service.current_api_index]}")
    
    # 尝试获取视频链接
    video_link = api_service.get_video_link()
    
    if video_link:
        print(f"\n成功获取视频链接: {video_link}")
        
        # 测试链接有效性
        try:
            print("\n测试视频链接有效性...")
            response = requests.head(video_link, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                content_length = response.headers.get('Content-Length', '未知')
                print(f"链接有效! 内容类型: {content_type}, 大小: {content_length}字节")
            else:
                print(f"链接返回状态码: {response.status_code}")
        except Exception as e:
            print(f"测试链接有效性失败: {e}")
    else:
        print("\n未能获取视频链接，请检查API是否可用")
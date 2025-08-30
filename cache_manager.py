import os
import time
import logging
import requests
from collections import deque

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CacheManager')

class CacheManager:
    def __init__(self, cache_dir="cache", max_cache=55, max_uncached=10):
        self.cache_dir = cache_dir
        self.max_cache = max_cache  # 总缓存数上限
        self.max_uncached = max_uncached  # 未播放缓存数上限
        self.video_queue = deque()  # 存储已缓存的视频路径
        self.played_videos = deque()  # 存储已播放的视频路径
        
        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"缓存目录: {self.cache_dir}")
        
        # 加载已有的缓存文件
        self._load_existing_cache()
        logger.info(f"初始缓存数: {self.get_cache_count()}")
        logger.info(f"未播放缓存数: {self.get_uncached_count()}")
    
    def _load_existing_cache(self):
        """加载已有的缓存文件"""
        if os.path.exists(self.cache_dir):
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.mp4')]
            # 按修改时间排序
            cache_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.cache_dir, x)))
            
            # 将文件添加到队列
            for file in cache_files:
                file_path = os.path.join(self.cache_dir, file)
                self.video_queue.append(file_path)
            
            # 如果缓存数量超过上限，清理旧缓存
            self.clean_old_cache()
    
    def cache_video(self, video_url):
        """缓存视频到本地
        参数: video_url - 视频链接
        返回: 本地视频路径，如果失败则返回None
        """
        try:
            # 生成唯一文件名
            filename = f"video_{int(time.time())}.mp4"
            video_path = os.path.join(self.cache_dir, filename)
            
            # 下载视频
            logger.info(f"开始缓存视频: {video_url}")
            
            # 设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # 使用stream模式下载大文件
            with requests.get(video_url, stream=True, timeout=60, headers=headers) as response:
                response.raise_for_status()  # 如果状态码不是200，抛出异常
                
                # 获取文件大小（如果可用）
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(video_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # 过滤掉keep-alive新块
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            # 记录下载进度（每下载10%记录一次）
                            if total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                if progress % 10 < 1:  # 避免频繁记录
                                    logger.debug(f"下载进度: {progress:.1f}% ({downloaded_size}/{total_size} bytes)")
            
            # 检查文件是否成功下载
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                # 添加到缓存队列
                self.video_queue.append(video_path)
                logger.info(f"视频缓存成功: {video_path}, 大小: {os.path.getsize(video_path)} bytes")
                
                # 检查总缓存数，如果超过上限则清理
                self.clean_old_cache()
                
                return video_path
            else:
                logger.error(f"视频缓存失败: 文件不存在或为空")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"缓存视频失败 - 请求异常: {e}")
            if os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.info(f"已删除不完整的缓存文件: {video_path}")
                except Exception as remove_error:
                    logger.error(f"删除不完整缓存文件失败: {remove_error}")
            return None
        except Exception as e:
            logger.error(f"缓存视频失败 - 未知错误: {e}")
            if os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.info(f"已删除不完整的缓存文件: {video_path}")
                except Exception as remove_error:
                    logger.error(f"删除不完整缓存文件失败: {remove_error}")
            return None
    
    def clean_old_cache(self):
        """清理旧缓存"""
        total_cache = len(self.video_queue) + len(self.played_videos)
        
        if total_cache > self.max_cache:
            # 需要清理的数量
            need_to_clean = total_cache - self.max_cache
            logger.info(f"缓存数量超过上限 ({total_cache}/{self.max_cache})，需要清理 {need_to_clean} 个文件")
            
            # 优先清理已播放的视频
            cleaned_count = 0
            while need_to_clean > 0 and self.played_videos:
                old_video = self.played_videos.popleft()
                try:
                    if os.path.exists(old_video):
                        file_size = os.path.getsize(old_video)
                        os.remove(old_video)
                        cleaned_count += 1
                        logger.info(f"清理已播放缓存: {old_video}, 释放空间: {file_size} bytes")
                    need_to_clean -= 1
                except Exception as e:
                    logger.error(f"删除缓存文件失败: {e}")
            
            # 如果还需要清理，清理最早的未播放视频
            while need_to_clean > 0 and self.video_queue:
                old_video = self.video_queue.popleft()
                try:
                    if os.path.exists(old_video):
                        file_size = os.path.getsize(old_video)
                        os.remove(old_video)
                        cleaned_count += 1
                        logger.info(f"清理未播放缓存: {old_video}, 释放空间: {file_size} bytes")
                    need_to_clean -= 1
                except Exception as e:
                    logger.error(f"删除缓存文件失败: {e}")
            
            logger.info(f"共清理 {cleaned_count} 个缓存文件")
        
    def get_cache_size(self):
        """获取缓存目录的总大小（字节）"""
        total_size = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(self.cache_dir):
                for filename in filenames:
                    if filename.endswith('.mp4'):
                        filepath = os.path.join(dirpath, filename)
                        if os.path.exists(filepath):
                            total_size += os.path.getsize(filepath)
            return total_size
        except Exception as e:
            logger.error(f"获取缓存大小失败: {e}")
            return 0
    
    def move_to_played(self, video_path):
        """将视频标记为已播放"""
        if video_path in self.video_queue:
            self.video_queue.remove(video_path)
            self.played_videos.append(video_path)
            logger.debug(f"视频已标记为已播放: {video_path}")
    
    def get_cache_count(self):
        """获取缓存总数"""
        return len(self.video_queue) + len(self.played_videos)
    
    def get_uncached_count(self):
        """获取未播放缓存数"""
        return len(self.video_queue)
    
    def get_next_video(self):
        """获取下一个未播放视频，确保返回有效的视频路径"""
        while self.video_queue:
            video_path = self.video_queue.popleft()  # 移除并返回队列中的第一个元素
            
            # 检查视频文件是否存在且有效
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                self.played_videos.append(video_path)     # 将其标记为已播放
                logger.info(f"获取下一个视频: {video_path}")
                return video_path
            else:
                logger.warning(f"跳过无效视频文件: {video_path}")
                # 如果文件不存在，尝试从文件系统中删除记录
                try:
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        logger.info(f"已删除无效视频文件: {video_path}")
                except Exception as e:
                    logger.error(f"删除无效视频文件失败: {e}")
        logger.warning("没有可用的缓存视频")
        return None
    
    def remove_video(self, video_path):
        """移除指定视频"""
        if video_path in self.video_queue:
            self.video_queue.remove(video_path)
            try:
                if os.path.exists(video_path):
                    file_size = os.path.getsize(video_path)
                    os.remove(video_path)
                    logger.info(f"移除视频: {video_path}, 释放空间: {file_size} bytes")
            except Exception as e:
                logger.error(f"移除视频失败: {e}")
        elif video_path in self.played_videos:
            self.played_videos.remove(video_path)
            try:
                if os.path.exists(video_path):
                    file_size = os.path.getsize(video_path)
                    os.remove(video_path)
                    logger.info(f"移除已播放视频: {video_path}, 释放空间: {file_size} bytes")
            except Exception as e:
                logger.error(f"移除已播放视频失败: {e}")
        else:
            logger.warning(f"视频不在缓存队列中: {video_path}")

# 测试代码
if __name__ == "__main__":
    cache_manager = CacheManager()
    print(f"初始缓存数: {cache_manager.get_cache_count()}")
    print(f"未播放缓存数: {cache_manager.get_uncached_count()}")
    print(f"缓存总大小: {cache_manager.get_cache_size()} bytes")
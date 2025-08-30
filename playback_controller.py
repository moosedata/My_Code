#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""视频播放控制器模块"""

import os
import sys
import platform
import time
import traceback
import logging
from ffpyplayer.player import MediaPlayer
from ffpyplayer.tools import set_loglevel

# 配置日志
def setup_logger():
    """配置日志记录器"""
    logger = logging.getLogger("PlaybackController")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # 添加处理器到记录器
        logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

# 设置ffpyplayer日志级别（可选，设为WARNING以减少输出）
set_loglevel("warning")

class PlaybackController:
    """基于ffpyplayer的视频播放控制器"""
    
    def __init__(self):
        """初始化播放控制器"""
        self.player = None  # ffpyplayer媒体播放器实例
        self.media = None  # 当前加载的媒体文件路径
        self.current_file = None  # 当前播放的文件路径
        self.is_initialized = False  # 播放器初始化状态
        self.is_playing = False  # 当前播放状态
        self.media_ready = False  # 媒体准备状态
        self.last_valid_timestamp = 0  # 上次有效的时间戳
        self.media_length = 0  # 媒体总长度（毫秒）
        
        # 初始化ffpyplayer
        self._initialize_ffpyplayer()
    
    def _initialize_ffpyplayer(self):
        """初始化ffpyplayer播放器
        返回: 是否初始化成功
        """
        try:
            # ffpyplayer不需要像VLC那样复杂的初始化
            self.is_initialized = True
            logger.info("ffpyplayer播放器初始化成功")
            return True
        except Exception as e:
            logger.error(f"ffpyplayer播放器初始化失败: {e}")
            self.is_initialized = False
            return False
    
    def set_ffpyplayer_path(self, path):
        """设置ffpyplayer相关库的路径（ffpyplayer通常不需要此步骤）
        参数: path - ffpyplayer库的路径
        返回: 是否设置成功
        """
        # 注意：ffpyplayer通常通过pip安装，不需要手动设置路径
        # 此方法保留以保持API兼容性
        logger.warning("ffpyplayer不需要手动设置路径")
        return True
    
    def load_media(self, file_path):
        """加载媒体文件
        参数: file_path - 媒体文件路径
        返回: 是否加载成功
        """
        if not self.is_initialized:
            logger.error("播放器未初始化，无法加载媒体")
            return False
        
        if not os.path.exists(file_path):
            logger.error(f"媒体文件不存在: {file_path}")
            return False
        
        try:
            # 停止当前播放
            if self.player:
                self.player.stop()
            
            # 创建新的媒体播放器实例
            self.player = MediaPlayer(file_path)
            self.current_file = file_path
            self.media_ready = True
            
            # 尝试获取媒体长度
            time.sleep(0.5)  # 给播放器一些时间来加载媒体
            self.media_length = int(self.get_length())
            
            logger.info(f"加载媒体成功: {file_path}")
            logger.debug(f"媒体长度: {self.media_length}毫秒")
            return True
        except Exception as e:
            logger.error(f"加载媒体过程中出错: {e}")
            logger.debug(traceback.format_exc())
            self.player = None
            self.current_file = None
            self.media_ready = False
            return False
    
    def play(self):
        """开始播放
        返回: 是否播放成功
        """
        if not self.is_initialized:
            logger.error("播放器未初始化，无法播放")
            return False
        
        if not self.player:
            logger.error("没有加载媒体文件，无法播放")
            return False
        
        try:
            # ffpyplayer的play方法不需要返回值检查
            self.player.play()
            self.is_playing = True
            logger.info(f"开始播放: {self.current_file}")
            return True
        except Exception as e:
            logger.error(f"播放过程中出错: {e}")
            self.is_playing = False
            return False
    
    def pause(self):
        """暂停播放
        返回: 是否暂停成功
        """
        if not self.is_initialized:
            logger.error("播放器未初始化，无法暂停")
            return False
        
        if not self.player:
            logger.error("没有加载媒体文件，无法暂停")
            return False
        
        try:
            # ffpyplayer的pause方法会切换播放状态
            self.player.pause()
            self.is_playing = not self.is_playing
            status = "暂停" if not self.is_playing else "继续播放"
            logger.info(f"{status}: {self.current_file}")
            return True
        except Exception as e:
            logger.error(f"暂停过程中出错: {e}")
            return False
    
    def stop(self):
        """停止播放
        返回: 是否停止成功
        """
        if not self.is_initialized:
            logger.error("播放器未初始化，无法停止")
            return False
        
        if not self.player:
            logger.error("没有加载媒体文件，无法停止")
            return False
        
        try:
            self.player.stop()
            self.is_playing = False
            self.media_ready = False
            logger.info(f"停止播放: {self.current_file}")
            return True
        except Exception as e:
            logger.error(f"停止过程中出错: {e}")
            return False
    
    def is_playing_status(self):
        """获取当前播放状态
        返回: 是否正在播放
        """
        try:
            if self.is_initialized and self.player:
                # ffpyplayer没有直接的is_playing方法，我们维护自己的状态
                return self.is_playing
            return False
        except Exception as e:
            logger.error(f"获取播放状态出错: {e}")
            return False
    
    def set_volume(self, volume):
        """设置音量
        参数: volume - 音量值(0-100)
        返回: 是否设置成功
        """
        if not self.is_initialized:
            logger.error("播放器未初始化，无法设置音量")
            return False
        
        if not self.player:
            logger.error("没有加载媒体文件，无法设置音量")
            return False
        
        # 确保音量在有效范围内
        volume = max(0, min(100, volume))
        
        try:
            # ffpyplayer的音量范围是0.0-1.0
            self.player.set_volume(volume / 100.0)
            logger.info(f"设置音量成功: {volume}%")
            return True
        except Exception as e:
            logger.error(f"设置音量过程中出错: {e}")
            return False
    
    def get_volume(self):
        """获取当前音量
        返回: 音量值(0-100)
        """
        if not self.is_initialized:
            logger.error("播放器未初始化，无法获取音量")
            return 0
        
        if not self.player:
            logger.error("没有加载媒体文件，无法获取音量")
            return 0
        
        try:
            # ffpyplayer返回的音量范围是0.0-1.0
            volume = int(self.player.get_volume() * 100)
            logger.debug(f"当前音量: {volume}%")
            return volume
        except Exception as e:
            logger.error(f"获取音量过程中出错: {e}")
            return 0
    
    def get_current_time(self):
        """获取当前播放时间（毫秒）
        返回: 当前播放时间
        """
        if not self.is_initialized or not self.player:
            return self.last_valid_timestamp
        
        try:
            # 获取当前时间（秒）
            current_time = self.player.get_pts()
            if current_time is None:
                logger.warning("获取到无效的时间戳，使用上次有效时间戳")
                return self.last_valid_timestamp
            
            # 转换为毫秒
            current_time_ms = int(current_time * 1000)
            
            # 验证时间戳有效性
            if current_time_ms < 0:
                logger.warning(f"获取到无效的时间戳: {current_time_ms}，使用上次有效时间戳")
                return self.last_valid_timestamp
            
            # 检查时间戳是否合理（不超过媒体长度）
            media_length = self.get_length()
            if media_length > 0 and current_time_ms > media_length + 1000:  # 允许1秒误差
                logger.warning(f"时间戳超出媒体长度: {current_time_ms}/{media_length}，使用上次有效时间戳")
                return self.last_valid_timestamp
            
            # 更新并返回有效时间戳
            self.last_valid_timestamp = current_time_ms
            return current_time_ms
        except Exception as e:
            logger.error(f"获取当前播放时间出错: {e}")
            logger.debug(traceback.format_exc())
            # 返回上次有效的时间戳
            return self.last_valid_timestamp
    
    def get_length(self):
        """获取媒体总长度（毫秒）
        返回: 媒体总长度
        """
        if not self.is_initialized or not self.player:
            return 0
        
        try:
            # 尝试获取媒体长度
            # 注意：ffpyplayer没有直接获取媒体长度的方法
            # 这里使用我们之前缓存的值
            if self.media_length > 0:
                return self.media_length
            
            # 如果没有缓存，尝试估算
            # 这不是一个准确的方法，但在ffpyplayer中是必要的
            # 先快进到末尾
            self.player.seek(1.0)
            time.sleep(0.5)  # 给播放器一些时间响应
            length = self.player.get_pts()
            if length is not None:
                self.media_length = int(length * 1000)
            
            # 恢复到原来的位置
            if self.last_valid_timestamp > 0:
                self.player.seek(self.last_valid_timestamp / 1000.0)
            else:
                self.player.seek(0.0)
                
            return self.media_length
        except Exception as e:
            logger.error(f"获取媒体长度出错: {e}")
            return 0
    
    def set_position(self, position):
        """设置播放位置（0.0-1.0），增强错误处理和重试机制
        参数: position - 播放位置(0.0-1.0)
        返回: 是否设置成功
        """
        # 检查播放器是否初始化
        if not self.is_initialized:
            logger.error("播放器未初始化，无法设置播放位置")
            return False
        
        # 检查播放器实例是否存在
        if not self.player:
            logger.error("播放器实例不存在，无法设置播放位置")
            return False
        
        # 确保位置在有效范围内
        position = max(0.0, min(1.0, position))
        
        # 设置最大重试次数和递增等待策略
        max_retries = 5
        retry_count = 0
        retry_delays = [0.1, 0.2, 0.3, 0.5, 1.0]  # 递增的等待时间
        
        while retry_count < max_retries:
            try:
                # 检查媒体是否准备好
                if not self.media_ready:
                    logger.warning("媒体尚未准备好，尝试等待")
                    time.sleep(0.2)  # 增加等待时间
                    retry_count += 1
                    continue
                
                # 尝试设置位置
                self.player.seek(position)
                
                # 验证位置是否正确设置
                # 注意：ffpyplayer没有直接获取当前位置比例的方法
                # 我们需要通过获取当前时间和总长度来计算
                time.sleep(0.1)  # 给播放器一些时间响应
                current_time = self.get_current_time()
                media_length = self.get_length()
                
                if media_length > 0:
                    current_position = current_time / media_length
                    if abs(current_position - position) < 0.05:  # 允许5%的误差
                        logger.info(f"设置播放位置成功: {position:.1%}")
                        return True
                    else:
                        logger.warning(f"位置设置不准确: 目标={position:.1%}, 实际={current_position:.1%}")
                else:
                    # 如果无法获取媒体长度，假设设置成功
                    logger.info(f"设置播放位置成功: {position:.1%}")
                    return True
                
                # 重试前的策略
                retry_count += 1
                
                # 在重试之间执行一些恢复操作
                if retry_count % 2 == 0:
                    # 每两次重试后，重置播放器状态
                    logger.info("执行播放器状态重置...")
                    current_playing = self.is_playing
                    self.player.stop()
                    time.sleep(0.2)
                    if current_playing:
                        self.player.play()
                        time.sleep(0.3)
                
                # 等待递增的时间
                time.sleep(retry_delays[min(retry_count-1, len(retry_delays)-1)])
                
            except Exception as e:
                logger.warning(f"设置播放位置过程中出错: {str(e)}，重试中 ({retry_count+1}/{max_retries})")
                logger.debug(traceback.format_exc())
                retry_count += 1
                
                # 在异常情况下尝试更激进的恢复策略
                if retry_count % 2 == 0:
                    logger.info("执行异常恢复策略...")
                    try:
                        current_file = self.current_file
                        current_playing = self.is_playing
                        self.player.stop()
                        time.sleep(0.3)
                        if current_file:
                            self.load_media(current_file)  # 重新加载媒体
                            if current_playing:
                                self.player.play()
                                time.sleep(0.5)
                    except Exception as recovery_error:
                        logger.error(f"恢复策略执行失败: {recovery_error}")
                time.sleep(retry_delays[min(retry_count-1, len(retry_delays)-1)])
        
        # 所有重试都失败
        logger.error(f"设置播放位置失败，已尝试{max_retries}次")
        return False
    
    def __del__(self):
        """析构函数，释放资源"""
        if hasattr(self, 'player') and self.player:
            try:
                self.player.stop()
                del self.player
            except:
                pass

# ffpyplayer不需要查找路径的函数，保留以保持API兼容性
def find_and_set_vlc_path():
    """查找并设置VLC库的路径（ffpyplayer不需要此步骤）
    返回: None，因为ffpyplayer不需要设置路径
    """
    logger.warning("ffpyplayer不需要手动设置路径")
    return None

# 测试代码
if __name__ == "__main__":
    # 创建播放控制器
    controller = PlaybackController()
    
    # 如果初始化成功，可以进行播放测试
    if controller.is_initialized:
        print("ffpyplayer播放器初始化成功")
        print(f"当前音量: {controller.get_volume()}%")
        
        # 如果有命令行参数作为视频文件路径
        if len(sys.argv) > 1:
            video_file = sys.argv[1]
            if controller.load_media(video_file):
                print(f"加载媒体成功: {video_file}")
                controller.set_volume(50)
                controller.play()
                
                # 等待用户输入停止
                input("按Enter键停止播放...")
                controller.stop()
        else:
            print("请提供视频文件路径作为参数")
    else:
        print("ffpyplayer播放器初始化失败")
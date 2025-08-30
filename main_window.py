import os
import sys
import time
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MainWindow')

# 导入重构后的模块
from api_service import APIService
from cache_manager import CacheManager
from playback_controller import PlaybackController

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("抖音风格视频播放器")
        self.geometry("900x700")
        
        # 设置中文字体支持
        self.default_font = tkfont.nametofont("TkDefaultFont")
        self.default_font.configure(family="SimHei", size=10)
        self.text_font = tkfont.nametofont("TkTextFont")
        self.text_font.configure(family="SimHei", size=10)
        
        # 初始化核心组件
        self.api_service = APIService()
        self.cache_manager = CacheManager()
        self.playback_controller = PlaybackController()
        
        # 状态变量
        self.is_loading = False  # 是否正在加载视频
        self.is_caching = False  # 是否正在后台缓存
        self.current_video_path = None  # 当前播放的视频路径
        self.cache_thread = None  # 缓存线程
        self.stop_cache_event = threading.Event()  # 停止缓存事件
        
        # 创建UI
        self._create_ui()
        
        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 检查VLC初始化状态
        if not self.playback_controller.is_initialized:
            self._show_vlc_config_dialog()
        
        # 启动后台缓存线程
        self._start_cache_thread()
    
    def _create_ui(self):
        """创建用户界面"""
        # 主布局
        self.main_frame = ttk.Frame(self, padding=(10, 10, 10, 10))
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 视频播放区域
        self.video_frame = ttk.LabelFrame(self.main_frame, text="视频播放", padding=(5, 5, 5, 5))
        self.video_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 播放画布
        self.canvas = tk.Canvas(self.video_frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 播放控制区域
        self.control_frame = ttk.Frame(self.main_frame, padding=(5, 5, 5, 5))
        self.control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 播放/暂停按钮
        self.play_button = ttk.Button(self.control_frame, text="播放", command=self._toggle_play_pause, width=10)
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        # 停止按钮
        self.stop_button = ttk.Button(self.control_frame, text="停止", command=self._stop_playback, width=10)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 下一个按钮
        self.next_button = ttk.Button(self.control_frame, text="下一个", command=self._play_next_video, width=10)
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        # 音量控制
        self.volume_frame = ttk.Frame(self.control_frame)
        self.volume_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(self.volume_frame, text="音量:").pack(side=tk.LEFT)
        self.volume_scale = ttk.Scale(self.volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=100, command=self._on_volume_change)
        self.volume_scale.set(50)  # 默认音量50%
        self.volume_scale.pack(side=tk.LEFT, padx=5)
        
        self.volume_label = ttk.Label(self.volume_frame, text="50%")
        self.volume_label.pack(side=tk.LEFT)
        
        # 播放进度条
        self.progress_frame = ttk.Frame(self.main_frame, padding=(5, 5, 5, 5))
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_scale = ttk.Scale(self.progress_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self._on_progress_change)
        self.progress_scale.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5)
        
        self.time_label = ttk.Label(self.progress_frame, text="00:00/00:00", width=10)
        self.time_label.pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_frame = ttk.Frame(self.main_frame, padding=(5, 5, 5, 5))
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 缓存状态
        self.cache_status_var = tk.StringVar(value="缓存状态: 未缓存")
        self.cache_status_label = ttk.Label(self.status_frame, textvariable=self.cache_status_var, anchor=tk.W)
        self.cache_status_label.pack(fill=tk.X, side=tk.LEFT)
        
        # 菜单
        self._create_menu()
        
        # 启动进度更新线程
        self._start_progress_update_thread()
    
    def _create_menu(self):
        """创建菜单"""
        self.menu_bar = tk.Menu(self)
        
        # 文件菜单
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="打开文件", command=self._open_file)
        self.file_menu.add_command(label="设置VLC路径", command=self._show_vlc_config_dialog)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="退出", command=self._on_closing)
        self.menu_bar.add_cascade(label="文件", menu=self.file_menu)
        
        # 工具菜单
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.tools_menu.add_command(label="清理缓存", command=self._clean_cache)
        self.tools_menu.add_command(label="查看缓存状态", command=self._show_cache_status)
        self.tools_menu.add_command(label="设置API", command=self._show_api_config_dialog)
        self.menu_bar.add_cascade(label="工具", menu=self.tools_menu)
        
        # 帮助菜单
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="关于", command=self._show_about)
        self.menu_bar.add_cascade(label="帮助", menu=self.help_menu)
        
        # 设置菜单
        self.config(menu=self.menu_bar)
    
    def _toggle_play_pause(self):
        """切换播放/暂停状态"""
        if not self.playback_controller.is_initialized:
            messagebox.showerror("错误", "VLC播放器未初始化，无法播放视频")
            return
        
        if not self.current_video_path:
            # 如果没有当前视频，尝试播放下一个
            self._play_next_video()
            return
        
        try:
            if self.playback_controller.is_playing_status():
                self.playback_controller.pause()
                self.play_button.config(text="播放")
            else:
                self.playback_controller.play()
                self.play_button.config(text="暂停")
        except Exception as e:
            logger.error(f"播放/暂停操作失败: {e}")
            messagebox.showerror("错误", f"播放/暂停操作失败: {str(e)}")
    
    def _stop_playback(self):
        """停止播放"""
        if not self.playback_controller.is_initialized:
            return
        
        try:
            self.playback_controller.stop()
            self.play_button.config(text="播放")
            self.current_video_path = None
        except Exception as e:
            logger.error(f"停止播放操作失败: {e}")
            messagebox.showerror("错误", f"停止播放操作失败: {str(e)}")
    
    def _play_next_video(self):
        """播放下一个视频"""
        if self.is_loading:
            return  # 防止重复加载
        
        self.is_loading = True
        self.play_button.config(text="加载中...")
        
        try:
            # 尝试从缓存中获取下一个视频
            next_video = self.cache_manager.get_next_video()
            
            if next_video:
                self._load_and_play_video(next_video)
            else:
                # 如果缓存中没有视频，尝试缓存一个新视频
                logger.info("缓存中没有可用视频，尝试获取新视频")
                self._load_new_video_from_api()
        except Exception as e:
            logger.error(f"播放下一个视频失败: {e}")
            messagebox.showerror("错误", f"播放下一个视频失败: {str(e)}")
        finally:
            self.is_loading = False
            self.play_button.config(text="播放")
    
    def _load_new_video_from_api(self):
        """从API获取新视频"""
        try:
            # 显示加载提示
            '''loading_window = tk.Toplevel(self)
            loading_window.title("加载中")
            loading_window.geometry("300x100")
            loading_window.transient(self)
            loading_window.grab_set()
            
            ttk.Label(loading_window, text="正在从API获取视频...").pack(pady=20)
            loading_window.update()
            '''
            # 获取视频链接
            video_url = self.api_service.get_video_link()
            
            if video_url:
                # 缓存视频
                video_path = self.cache_manager.cache_video(video_url)
                
                if video_path:
                    # 关闭加载提示
                    loading_window.destroy()
                    # 播放视频
                    self._load_and_play_video(video_path)
                else:
                    loading_window.destroy()
                    logger.error("视频缓存失败")
                    messagebox.showerror("错误", "视频缓存失败")
            else:
                loading_window.destroy()
                logger.error("无法从API获取视频链接")
                messagebox.showerror("错误", "无法从API获取视频链接")
        except Exception as e:
            logger.error(f"从API获取视频失败: {e}")
            messagebox.showerror("错误", f"从API获取视频失败: {str(e)}")
    
    def _load_and_play_video(self, video_path):
        """加载并播放视频"""
        if not self.playback_controller.is_initialized:
            messagebox.showerror("错误", "VLC播放器未初始化，无法播放视频")
            return
        
        try:
            # 获取窗口ID用于嵌入播放
            window_id = self.canvas.winfo_id()
            
            # 停止当前播放
            self.playback_controller.stop()
            
            # 加载新视频
            if self.playback_controller.load_media(video_path):
                # 设置播放窗口
                if sys.platform.startswith('linux'):
                    self.playback_controller.player.set_xwindow(window_id)
                elif sys.platform == "win32":
                    self.playback_controller.player.set_hwnd(window_id)
                elif sys.platform == "darwin":
                    self.playback_controller.player.set_nsobject(int(window_id))
                
                # 开始播放
                self.playback_controller.play()
                self.play_button.config(text="暂停")
                
                # 更新当前视频路径
                self.current_video_path = video_path
                
                # 设置播放结束回调
                self.playback_controller.set_end_callback(self._on_playback_ended)
                
                logger.info(f"成功播放视频: {video_path}")
            else:
                logger.error(f"加载视频失败: {video_path}")
                messagebox.showerror("错误", f"加载视频失败: {video_path}")
        except Exception as e:
            logger.error(f"加载并播放视频失败: {e}")
            messagebox.showerror("错误", f"加载并播放视频失败: {str(e)}")
    
    def _on_playback_ended(self):
        """播放结束回调函数"""
        logger.info("视频播放结束，自动播放下一个")
        self.after(1000, self._play_next_video)  # 延迟1秒后播放下一个
    
    def _on_volume_change(self, value):
        """音量变化回调"""
        volume = int(float(value))
        self.volume_label.config(text=f"{volume}%")
        
        if self.playback_controller.is_initialized:
            self.playback_controller.set_volume(volume)
    
    def _on_progress_change(self, value):
        """进度条变化回调"""
        if not self.playback_controller.is_initialized or not self.playback_controller.is_playing_status():
            return
        
        try:
            position = float(value) / 100.0
            self.playback_controller.set_position(position)
        except Exception as e:
            logger.error(f"设置播放进度失败: {e}")
    
    def _start_progress_update_thread(self):
        """启动进度更新线程"""
        def update_progress():
            while True:
                try:
                    if self.playback_controller.is_initialized and self.playback_controller.is_playing_status():
                        # 获取当前播放时间和总长度
                        current_time = self.playback_controller.get_current_time()
                        total_time = self.playback_controller.get_length()
                        
                        if total_time > 0:
                            # 计算进度百分比
                            progress = (current_time / total_time) * 100
                            
                            # 更新进度条和时间显示
                            self.progress_scale.set(progress)
                            
                            # 格式化时间显示
                            current_str = time.strftime('%M:%S', time.gmtime(current_time / 1000))
                            total_str = time.strftime('%M:%S', time.gmtime(total_time / 1000))
                            self.time_label.config(text=f"{current_str}/{total_str}")
                    
                    # 更新缓存状态
                    cache_count = self.cache_manager.get_cache_count()
                    uncached_count = self.cache_manager.get_uncached_count()
                    self.cache_status_var.set(f"缓存状态: 总计{cache_count}, 未播放{uncached_count}")
                    
                    # 每500毫秒更新一次
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"进度更新线程错误: {e}")
                    time.sleep(0.5)  # 发生错误时暂停一下再继续
        
        # 创建并启动线程
        progress_thread = threading.Thread(target=update_progress, daemon=True)
        progress_thread.start()
    
    def _start_cache_thread(self):
        """启动后台缓存线程"""
        def cache_videos():
            while not self.stop_cache_event.is_set():
                try:
                    # 检查未播放缓存数量
                    uncached_count = self.cache_manager.get_uncached_count()
                    
                    # 如果未播放缓存少于最大值，尝试缓存新视频
                    if uncached_count < self.cache_manager.max_uncached:
                        logger.info(f"后台缓存: 当前未播放缓存数 {uncached_count}/{self.cache_manager.max_uncached}")
                        
                        # 获取视频链接
                        video_url = self.api_service.get_video_link()
                        
                        if video_url:
                            # 缓存视频
                            self.is_caching = True
                            self.cache_manager.cache_video(video_url)
                            self.is_caching = False
                        else:
                            logger.warning("后台缓存: 无法获取视频链接")
                            time.sleep(5)  # 无法获取链接时暂停5秒
                    else:
                        # 缓存数量已足够，等待一段时间
                        logger.debug(f"后台缓存: 缓存数量已足够 ({uncached_count}/{self.cache_manager.max_uncached})")
                        time.sleep(10)
                except Exception as e:
                    logger.error(f"后台缓存线程错误: {e}")
                    time.sleep(5)  # 发生错误时暂停5秒
        
        # 创建并启动线程
        self.cache_thread = threading.Thread(target=cache_videos, daemon=True)
        self.cache_thread.start()
    
    def _open_file(self):
        """打开本地文件"""
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv")]
        )
        
        if file_path:
            self._load_and_play_video(file_path)
    
    def _show_vlc_config_dialog(self):
        """显示VLC路径配置对话框"""
        dialog = tk.Toplevel(self)
        dialog.title("设置VLC路径")
        dialog.geometry("500x200")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="请输入VLC播放器的安装路径:").pack(pady=10)
        
        path_var = tk.StringVar()
        path_entry = ttk.Entry(dialog, textvariable=path_var, width=50)
        path_entry.pack(pady=10, padx=20, fill=tk.X)
        
        # 尝试获取默认路径
        default_paths = [
            "C:\\Program Files\\VideoLAN\\VLC",
            "C:\\Program Files (x86)\\VideoLAN\\VLC"
        ]
        for path in default_paths:
            if os.path.exists(path):
                path_var.set(path)
                break
        
        def browse_path():
            path = filedialog.askdirectory(title="选择VLC安装目录")
            if path:
                path_var.set(path)
        
        def apply_settings():
            vlc_path = path_var.get()
            if vlc_path:
                if self.playback_controller.set_vlc_path(vlc_path):
                    messagebox.showinfo("成功", "VLC路径设置成功")
                    dialog.destroy()
                else:
                    messagebox.showerror("错误", "VLC路径设置失败，请检查路径是否正确")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10, fill=tk.X)
        
        ttk.Button(button_frame, text="浏览...", command=browse_path).pack(side=tk.LEFT, padx=20)
        ttk.Button(button_frame, text="应用", command=apply_settings).pack(side=tk.RIGHT, padx=20)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _show_api_config_dialog(self):
        """显示API配置对话框"""
        dialog = tk.Toplevel(self)
        dialog.title("设置API")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="API配置").pack(pady=10)
        
        # 重试次数设置
        ttk.Label(dialog, text="重试次数:").pack(anchor=tk.W, padx=20)
        retry_var = tk.IntVar(value=self.api_service.retry_count)
        retry_spinbox = ttk.Spinbox(dialog, from_=1, to=10, textvariable=retry_var, width=5)
        retry_spinbox.pack(anchor=tk.W, padx=20, pady=5)
        
        # 切换阈值设置
        ttk.Label(dialog, text="API切换阈值:").pack(anchor=tk.W, padx=20)
        switch_var = tk.IntVar(value=self.api_service.switch_threshold)
        switch_spinbox = ttk.Spinbox(dialog, from_=1, to=10, textvariable=switch_var, width=5)
        switch_spinbox.pack(anchor=tk.W, padx=20, pady=5)
        
        def apply_settings():
            try:
                self.api_service.retry_count = retry_var.get()
                self.api_service.switch_threshold = switch_var.get()
                messagebox.showinfo("成功", "API配置已更新")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"更新API配置失败: {str(e)}")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20, fill=tk.X)
        
        ttk.Button(button_frame, text="应用", command=apply_settings).pack(side=tk.RIGHT, padx=20)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _show_cache_status(self):
        """显示缓存状态"""
        cache_count = self.cache_manager.get_cache_count()
        uncached_count = self.cache_manager.get_uncached_count()
        cache_size = self.cache_manager.get_cache_size()
        
        # 格式化缓存大小
        if cache_size < 1024:
            size_str = f"{cache_size} B"
        elif cache_size < 1024 * 1024:
            size_str = f"{cache_size / 1024:.2f} KB"
        elif cache_size < 1024 * 1024 * 1024:
            size_str = f"{cache_size / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{cache_size / (1024 * 1024 * 1024):.2f} GB"
        
        messagebox.showinfo(
            "缓存状态",
            f"总缓存数: {cache_count}\n" \
            f"未播放缓存: {uncached_count}\n" \
            f"缓存总大小: {size_str}\n" \
            f"缓存目录: {self.cache_manager.cache_dir}\n" \
            f"最大缓存数: {self.cache_manager.max_cache}\n" \
            f"最大未播放缓存: {self.cache_manager.max_uncached}"
        )
    
    def _clean_cache(self):
        """清理缓存"""
        if messagebox.askyesno("确认", "确定要清理所有缓存吗？"):
            try:
                # 停止当前播放
                self._stop_playback()
                
                # 清空缓存队列
                while self.cache_manager.video_queue:
                    video_path = self.cache_manager.video_queue.popleft()
                    if os.path.exists(video_path):
                        os.remove(video_path)
                
                while self.cache_manager.played_videos:
                    video_path = self.cache_manager.played_videos.popleft()
                    if os.path.exists(video_path):
                        os.remove(video_path)
                
                logger.info("缓存已清理")
                messagebox.showinfo("成功", "缓存已清理完成")
            except Exception as e:
                logger.error(f"清理缓存失败: {e}")
                messagebox.showerror("错误", f"清理缓存失败: {str(e)}")
    
    def _show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于",
            "抖音风格视频播放器\n" \
            "版本: 1.0\n" \
            "功能: 在线视频播放、自动缓存、连续播放\n" \
            "使用VLC作为视频播放引擎"
        )
    
    def _on_closing(self):
        """窗口关闭处理"""
        # 设置停止事件
        self.stop_cache_event.set()
        
        # 停止播放
        if self.playback_controller.is_initialized:
            self.playback_controller.stop()
        
        # 等待缓存线程结束（最多等待5秒）
        if self.cache_thread and self.cache_thread.is_alive():
            self.cache_thread.join(timeout=5)
        
        logger.info("应用程序已关闭")
        self.destroy()

def main():
    """应用程序入口"""
    try:
        logger.info("应用程序启动")
        app = MainWindow()
        app.mainloop()
    except Exception as e:
        logger.error(f"应用程序运行错误: {e}")
        messagebox.showerror("错误", f"应用程序运行错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
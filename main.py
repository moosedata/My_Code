import sys
from main_window import main

if __name__ == '__main__':
    # 确保中文显示正常
    import matplotlib  # 这里导入了matplotlib
    matplotlib.rcParams['font.family'] = ['SimHei', 'WenQuanYi Micro Hei', 'Heiti TC']
    
    # 启动应用
    main()

# 说明:
# 1. 此文件为应用的入口点
# 2. 导入并调用main_window.py中的main函数
# 3. 设置matplotlib字体以确保中文正常显示
# 4. 简单明了，将应用的启动逻辑与界面逻辑分离
"""
打包后的应用入口文件
处理打包后的路径问题
"""
import os
import sys

# 如果是打包后的可执行文件，需要调整路径
if getattr(sys, 'frozen', False):
    # 打包后的可执行文件
    base_path = sys._MEIPASS
    # 设置模板文件夹路径
    template_folder = os.path.join(base_path, 'templates')
else:
    # 开发模式
    base_path = os.path.dirname(os.path.abspath(__file__))
    template_folder = os.path.join(base_path, 'templates')

# 导入原始应用
from app import app

# 更新模板文件夹路径
app.template_folder = template_folder

# 确保上传和临时目录存在（在用户目录下创建）
if getattr(sys, 'frozen', False):
    # 打包模式：在用户目录下创建应用数据目录
    import appdirs
    app_data_dir = appdirs.user_data_dir('双面打印助手', 'PrintHelper')
    UPLOAD_FOLDER = os.path.join(app_data_dir, 'uploads')
    TEMP_FOLDER = os.path.join(app_data_dir, 'temp')
else:
    # 开发模式：使用当前目录
    UPLOAD_FOLDER = os.path.join(base_path, 'uploads')
    TEMP_FOLDER = os.path.join(base_path, 'temp')

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# 更新应用配置
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMP_FOLDER'] = TEMP_FOLDER

if __name__ == '__main__':
    print(f"应用启动中...")
    print(f"上传目录: {UPLOAD_FOLDER}")
    print(f"临时目录: {TEMP_FOLDER}")
    print(f"访问地址: http://localhost:8000")
    app.run(debug=False, host='0.0.0.0', port=8000)


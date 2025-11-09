"""
打包脚本：将Flask应用打包为可执行文件
使用PyInstaller进行打包
"""
import PyInstaller.__main__
import os
import sys

# 获取项目根目录
base_dir = os.path.dirname(os.path.abspath(__file__))

# PyInstaller参数
args = [
    'app.py',  # 主程序文件
    '--name=双面打印助手',  # 可执行文件名称
    '--onefile',  # 打包为单个文件
    '--windowed',  # Windows下不显示控制台（macOS/Linux使用--noconsole）
    '--add-data=templates;templates',  # 包含模板文件（Windows使用分号）
    '--hidden-import=flask',  # 显式导入Flask
    '--hidden-import=flask_cors',  # 显式导入flask_cors
    '--hidden-import=pypdf',  # 显式导入pypdf
    '--hidden-import=docx2pdf',  # 显式导入docx2pdf（可选）
    '--hidden-import=win32com.client',  # Windows Word支持（可选）
    '--collect-all=flask',  # 收集Flask的所有数据
    '--collect-all=pypdf',  # 收集pypdf的所有数据
]

# macOS/Linux使用冒号分隔，Windows使用分号
if sys.platform != 'win32':
    # 替换Windows风格的分号为Unix风格的冒号
    args = [arg.replace(';', ':') if 'templates' in arg else arg for arg in args]
    # macOS/Linux显示控制台窗口（可选，用于调试）
    if '--windowed' in args:
        args.remove('--windowed')
        args.append('--noconsole')  # 或者保留控制台用于查看日志

print("开始打包...")
print(f"工作目录: {base_dir}")
print(f"参数: {args}")

# 执行打包
PyInstaller.__main__.run(args)

print("\n打包完成！")
print("可执行文件位置: dist/双面打印助手" + (".exe" if sys.platform == 'win32' else ""))


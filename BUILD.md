# 打包为可执行文件说明

本项目可以使用 PyInstaller 将 Flask 应用打包为可执行文件。

## 安装打包工具

```bash
pip install pyinstaller
```

可选：如果需要更好的路径处理（打包模式下的用户数据目录）：
```bash
pip install appdirs
```

## 打包方法

### 方法1：使用 spec 文件（推荐）

```bash
pyinstaller build.spec
```

### 方法2：使用命令行

**Windows:**
```bash
pyinstaller --name="双面打印助手" --onefile --add-data "templates;templates" --hidden-import flask --hidden-import flask_cors --hidden-import pypdf app.py
```

**macOS/Linux:**
```bash
pyinstaller --name="双面打印助手" --onefile --add-data "templates:templates" --hidden-import flask --hidden-import flask_cors --hidden-import pypdf app.py
```

### 方法3：使用打包脚本

```bash
python build_exe.py
```

## 打包后的文件位置

打包完成后，可执行文件位于：
- `dist/双面打印助手` (macOS/Linux)
- `dist/双面打印助手.exe` (Windows)

## 注意事项

1. **模板文件**：确保 `templates` 文件夹被正确包含
2. **依赖库**：所有 Python 依赖都会被包含在可执行文件中
3. **系统命令**：`lp`、`lpstat` 等系统命令需要在目标系统上可用
4. **Word转换**：LibreOffice 需要单独安装，不会被打包
5. **文件路径**：打包后的应用会在用户数据目录创建 `uploads` 和 `temp` 文件夹

## 测试打包后的应用

1. 运行生成的可执行文件
2. 打开浏览器访问 `http://localhost:8000`
3. 测试文件上传和打印功能

## 跨平台打包

- **Windows**: 在 Windows 系统上打包
- **macOS**: 在 macOS 系统上打包
- **Linux**: 在 Linux 系统上打包

注意：PyInstaller 不支持交叉编译，需要在目标平台上进行打包。

## 减小文件大小

如果需要减小可执行文件大小，可以：

1. 使用 `--exclude-module` 排除不需要的模块
2. 使用 `--strip` 选项（Linux）
3. 使用 UPX 压缩（如果可用）

## 常见问题

### 1. 模板文件找不到

确保在 spec 文件或命令行中正确指定了 `templates` 文件夹。

### 2. 导入错误

在 `hiddenimports` 中添加缺失的模块。

### 3. 路径问题

使用 `app_packaged.py` 作为入口文件，它会自动处理打包后的路径问题。


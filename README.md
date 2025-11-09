# 双面打印助手

一个Web后端应用，用于处理不支持自动翻页的打印机。将PDF或Word文档分为两部分打印：
- 第一部分：奇数页，从小到大顺序打印
- 第二部分：偶数页，从大到小顺序打印（手动翻页后）

## 功能特点

- 📄 支持PDF和Word文档（.pdf, .doc, .docx）上传和处理
- 🔄 自动将Word文档转换为PDF
- 🖨️ 支持手动选择打印机
- 📑 自动分离奇数页和偶数页
- 🔄 分步打印，打印完奇数页后显示继续按钮
- 🎨 现代化的Web界面

## 系统要求

- Python 3.12+
- macOS 或 Linux（使用 `lp` 命令）或 Windows（使用 `print` 命令）
- **Word文档支持**（可选）：
  - **推荐**：安装 LibreOffice（格式保持最好）
    - macOS: `brew install --cask libreoffice`
    - Linux: `sudo apt-get install libreoffice` 或 `sudo yum install libreoffice`
    - Windows: 从 [LibreOffice官网](https://www.libreoffice.org/) 下载安装
  - **备选**：Windows系统可安装 `pywin32` 使用Microsoft Word进行转换

## 安装步骤

1. 克隆或下载项目到本地

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 启动应用：
```bash
python app.py
```

2. 打开浏览器访问：`http://localhost:8000`

3. 使用步骤：
   - 点击或拖拽上传PDF或Word文件（.pdf, .doc, .docx）
   - 选择要使用的打印机（或使用默认打印机）
   - 点击"上传并处理文件"（Word文档会自动转换为PDF）
   - 点击"打印奇数页（从小到大）"开始打印
   - 等待奇数页打印完成后，手动翻页
   - 点击"继续：打印偶数页（从大到小）"完成打印

## 工作原理

1. **文件上传**：用户上传PDF或Word文件到服务器
2. **格式转换**（仅Word文档）：
   - 如果上传的是Word文档（.doc, .docx），系统会自动转换为PDF
   - 转换方法优先级：
     1. LibreOffice命令行工具（推荐，格式保持最好）
     2. docx2pdf库（需要LibreOffice支持）
     3. Windows Word COM对象（仅Windows，需要安装pywin32）
3. **页面分离**：服务器将PDF分为两个文件：
   - `odd_pages.pdf`：包含所有奇数页（1, 3, 5, ...），按原顺序
   - `even_pages.pdf`：包含所有偶数页（2, 4, 6, ...），按倒序排列
4. **分步打印**：
   - 先打印奇数页（从小到大）
   - 打印完成后显示继续按钮
   - 用户手动翻页后，打印偶数页（从大到小）

## 目录结构

```
print/
├── app.py              # Flask后端应用
├── templates/
│   └── index.html      # 前端页面
├── uploads/            # 上传的文件存储目录
├── temp/               # 临时文件目录
├── requirements.txt    # Python依赖
└── README.md          # 说明文档
```

## API接口

- `GET /` - 主页面
- `GET /api/printers` - 获取可用打印机列表
- `POST /api/upload` - 上传PDF文件并处理
- `POST /api/print/odd` - 打印奇数页
- `POST /api/print/even` - 打印偶数页
- `DELETE /api/cleanup/<session_id>` - 清理会话临时文件

## 注意事项

- 确保系统已安装并配置好打印机
- 打印任务提交后，请等待打印完成再点击继续按钮
- 临时文件会在会话结束后自动清理
- 如果遇到打印问题，请检查系统打印服务是否正常运行

## 故障排除

### 无法检测到打印机
- macOS/Linux：确保 `lpstat` 命令可用
- Windows：确保 `wmic` 命令可用

### 打印失败
- 检查打印机是否在线
- 检查打印机名称是否正确
- 检查系统打印服务是否正常运行

### Word文档转换失败
- **macOS/Linux**：确保已安装LibreOffice，并且 `soffice` 命令在PATH中
  - 检查：在终端运行 `which soffice` 或 `soffice --version`
  - 如果未安装：`brew install --cask libreoffice`（macOS）或使用包管理器安装（Linux）
- **Windows**：
  - 推荐：安装LibreOffice
  - 备选：安装Microsoft Word和pywin32库：`pip install pywin32`
- 如果所有转换方法都失败，请使用PDF文件代替

## 许可证

MIT License


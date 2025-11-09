"""
打印服务后端应用
支持将PDF文档和Word文档分为奇数页和偶数页分别打印，支持手动选择打印机
"""
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import subprocess
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import json
import traceback
import sys
import re

app = Flask(__name__)
CORS(app)

# 是否为开发模式（可以通过环境变量设置）
# 注意：在 app.run(debug=True) 时，会在主函数中设置为True
DEBUG_MODE = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEBUG', '').lower() == 'true'

# 配置
UPLOAD_FOLDER = 'uploads'
TEMP_FOLDER = 'temp'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

# 如果通过app.config设置，则使用配置值（用于打包后的应用）
if hasattr(app, 'config') and app.config.get('UPLOAD_FOLDER'):
    UPLOAD_FOLDER = app.config.get('UPLOAD_FOLDER')
if hasattr(app, 'config') and app.config.get('TEMP_FOLDER'):
    TEMP_FOLDER = app.config.get('TEMP_FOLDER')

# 确保文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)


def format_error_message(error, include_traceback=True):
    """
    格式化错误信息，包括堆栈跟踪
    
    Args:
        error: 异常对象
        include_traceback: 是否包含堆栈跟踪
        
    Returns:
        dict: 包含错误信息的字典
    """
    # 检查是否为调试模式（检查app.debug或全局DEBUG_MODE）
    is_debug = app.debug or DEBUG_MODE
    
    error_info = {
        'error': str(error),
        'type': type(error).__name__
    }
    
    if include_traceback and is_debug:
        error_info['traceback'] = traceback.format_exc()
        error_info['full_traceback'] = traceback.format_exception(
            type(error), error, error.__traceback__
        )
    
    return error_info


def allowed_file(filename):
    """
    检查文件扩展名是否允许
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 如果文件扩展名允许则返回True
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def find_lpstat_command():
    """
    查找lpstat命令的完整路径
    
    Returns:
        str: lpstat命令的完整路径，如果找不到则返回None
    """
    # 常见的lpstat命令路径（macOS优先）
    possible_paths = [
        '/usr/bin/lpstat',  # macOS/Linux标准路径
        '/usr/local/bin/lpstat',  # 其他可能路径
        '/bin/lpstat',  # 某些系统
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    # 尝试使用which命令查找（使用shell环境）
    try:
        # 在macOS上，使用/bin/sh来确保PATH正确
        result = subprocess.run(
            ['/bin/sh', '-c', 'which lpstat'],
            capture_output=True,
            text=True,
            timeout=5,
            env=os.environ.copy()
        )
        if result.returncode == 0:
            found_path = result.stdout.strip()
            if found_path and os.path.exists(found_path):
                return found_path
    except:
        pass
    
    return None


def get_default_printer():
    """
    获取默认打印机名称
    
    Returns:
        str: 默认打印机名称，如果没有则返回None
    """
    lpstat_command = find_lpstat_command()
    if not lpstat_command:
        return None
    
    # 在macOS上，确保PATH包含/usr/bin
    env = os.environ.copy()
    if '/usr/bin' not in env.get('PATH', ''):
        env['PATH'] = '/usr/bin:/usr/local/bin:/bin:/usr/sbin:/sbin:' + env.get('PATH', '')
    
    try:
        result = subprocess.run(
            [lpstat_command, '-d'],
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        for line in result.stdout.split('\n'):
            if 'system default destination:' in line.lower():
                parts = line.split(':')
                if len(parts) > 1:
                    return parts[1].strip()
        return None
    except:
        return None


def get_available_printers():
    """
    获取系统可用的打印机列表
    
    Returns:
        list: 打印机名称列表
    """
    printers = []
    lpstat_command = find_lpstat_command()
    
    # 在macOS上，确保PATH包含/usr/bin
    env = os.environ.copy()
    if '/usr/bin' not in env.get('PATH', ''):
        env['PATH'] = '/usr/bin:/usr/local/bin:/bin:/usr/sbin:/sbin:' + env.get('PATH', '')
    
    if lpstat_command:
        try:
            # 方法1: 使用 lpstat -a 获取所有接受打印任务的打印机
            result = subprocess.run(
                [lpstat_command, '-a'],
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                
                # 中文系统：匹配行首到"正在接受请求"
                match = re.match(r'^(.*?)\s*(正在接受请求|自从.*开始接受请求)', line)
                # 英文系统：匹配行首到"accepting requests"
                if not match:
                    match = re.match(r'^(.*?) accepting requests', line)
                
                if match:
                    printer_name = match.group(1).strip()
                    if printer_name and printer_name not in printers:
                        printers.append(printer_name)
        except:
            pass
        
        # 如果方法1失败，尝试方法2: 使用 lpstat -p 获取所有打印机
        if not printers:
            try:
                result = subprocess.run(
                    [lpstat_command, '-p'],
                    capture_output=True,
                    text=True,
                    check=True,
                    env=env
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('printer'):
                        parts = line.split()
                        if len(parts) > 1:
                            printer_name = parts[1]
                            if printer_name not in printers:
                                printers.append(printer_name)
            except:
                pass
    
    # 如果还是失败，尝试Windows方法
    if not printers:
        try:
            result = subprocess.run(
                ['wmic', 'printer', 'get', 'name'],
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy()
            )
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and line != 'Name' and line not in printers:
                    printers.append(line)
        except:
            pass
    
    return printers


def convert_word_to_pdf(word_path, output_dir):
    """
    将Word文档转换为PDF
    
    Args:
        word_path: Word文档路径
        output_dir: 输出目录
        
    Returns:
        str: 转换后的PDF文件路径
        
    Raises:
        Exception: 转换失败时抛出异常
    """
    pdf_path = os.path.join(output_dir, 'converted.pdf')
    
    # 方法1: 尝试使用LibreOffice（推荐，格式保持最好）
    # 尝试多个可能的LibreOffice路径
    soffice_paths = [
        'soffice',  # 标准PATH中的命令
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',  # macOS标准位置
        '/usr/bin/soffice',  # Linux标准位置
        '/usr/local/bin/soffice',  # 其他可能位置
    ]
    
    for soffice_cmd in soffice_paths:
        try:
            # 检查命令是否存在
            if soffice_cmd != 'soffice':
                if not os.path.exists(soffice_cmd):
                    continue
            
            result = subprocess.run(
                [soffice_cmd, '--headless', '--convert-to', 'pdf', '--outdir', output_dir, word_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            # LibreOffice输出的PDF文件名可能与输入文件名相同
            base_name = os.path.splitext(os.path.basename(word_path))[0]
            possible_pdf = os.path.join(output_dir, f'{base_name}.pdf')
            if os.path.exists(possible_pdf):
                if possible_pdf != pdf_path:
                    os.rename(possible_pdf, pdf_path)
                return pdf_path
            # 如果没找到预期的文件名，检查输出目录中是否有PDF文件
            for file in os.listdir(output_dir):
                if file.endswith('.pdf'):
                    found_pdf = os.path.join(output_dir, file)
                    if found_pdf != pdf_path:
                        os.rename(found_pdf, pdf_path)
                    return pdf_path
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    # 方法2: 尝试使用docx2pdf库（需要安装docx2pdf）
    try:
        from docx2pdf import convert
        convert(word_path, pdf_path)
        if os.path.exists(pdf_path):
            return pdf_path
    except ImportError:
        pass
    except Exception:
        pass
    
    # 方法3: 尝试使用Windows的Word COM对象（仅Windows）
    try:
        import win32com.client
        word_app = win32com.client.Dispatch('Word.Application')
        word_app.Visible = False
        doc = word_app.Documents.Open(os.path.abspath(word_path))
        doc.SaveAs(os.path.abspath(pdf_path), FileFormat=17)  # 17 = PDF格式
        doc.Close()
        word_app.Quit()
        if os.path.exists(pdf_path):
            return pdf_path
    except:
        pass
    
    # 如果所有方法都失败，抛出异常
    raise Exception('无法转换Word文档为PDF。请确保已安装LibreOffice（推荐）或Microsoft Word（Windows）')


def parse_page_range(page_range_str, total_pages):
    """
    解析页码范围字符串，如 "1,2,3-5,7,10-20"
    
    Args:
        page_range_str: 页码范围字符串，如 "1,2,3-5,7,10-20"，空字符串表示全部页面
        total_pages: PDF总页数
        
    Returns:
        list: 页面索引列表（从0开始），已排序且去重
    """
    if not page_range_str or not page_range_str.strip():
        # 如果没有指定页码范围，返回所有页面
        return list(range(total_pages))
    
    page_indices = set()
    parts = page_range_str.replace(' ', '').split(',')
    
    for part in parts:
        if not part:
            continue
        
        if '-' in part:
            # 处理范围，如 "3-5"
            try:
                start, end = part.split('-', 1)
                start_page = int(start) - 1  # 转换为0-based索引
                end_page = int(end) - 1
                
                # 确保范围有效
                if start_page < 0:
                    start_page = 0
                if end_page >= total_pages:
                    end_page = total_pages - 1
                if start_page <= end_page:
                    page_indices.update(range(start_page, end_page + 1))
            except ValueError:
                raise ValueError(f'无效的页码范围格式: {part}')
        else:
            # 处理单个页码，如 "1"
            try:
                page_num = int(part) - 1  # 转换为0-based索引
                if 0 <= page_num < total_pages:
                    page_indices.add(page_num)
            except ValueError:
                raise ValueError(f'无效的页码: {part}')
    
    # 返回排序后的列表
    return sorted(list(page_indices))


def split_pdf_pages(pdf_path, output_dir, page_range_str=None):
    """
    将PDF分为奇数页和偶数页两个文件
    
    Args:
        pdf_path: 原始PDF文件路径
        output_dir: 输出目录
        page_range_str: 页码范围字符串，如 "1,2,3-5,7,10-20"，None或空字符串表示全部页面
        
    Returns:
        tuple: (奇数页文件路径, 偶数页文件路径, 总页数, 选择的页数)
    """
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    # 解析页码范围
    selected_indices = parse_page_range(page_range_str, total_pages)
    selected_count = len(selected_indices)
    
    if selected_count == 0:
        raise ValueError('没有选择任何页面')
    
    # 根据选择的页面索引，提取对应的页面
    selected_pages = [reader.pages[i] for i in selected_indices]
    
    # 在选择的页面中，重新划分奇偶页（基于在原始文档中的位置）
    # 注意：这里基于选择的页面在原始文档中的实际页码位置来判断奇偶
    odd_pages = []
    even_pages = []
    
    for idx in selected_indices:
        # idx是0-based索引，所以第1页是idx=0（奇数），第2页是idx=1（偶数）
        if idx % 2 == 0:  # 原始文档中的奇数页（1, 3, 5, ...）
            odd_pages.append(reader.pages[idx])
        else:  # 原始文档中的偶数页（2, 4, 6, ...）
            even_pages.append(reader.pages[idx])
    
    # 创建奇数页PDF（从小到大）
    odd_writer = PdfWriter()
    for page in odd_pages:
        odd_writer.add_page(page)
    
    odd_path = os.path.join(output_dir, 'odd_pages.pdf')
    with open(odd_path, 'wb') as f:
        odd_writer.write(f)
    
    # 创建偶数页PDF（从大到小）
    even_writer = PdfWriter()
    for page in reversed(even_pages):
        even_writer.add_page(page)
    
    even_path = os.path.join(output_dir, 'even_pages.pdf')
    with open(even_path, 'wb') as f:
        even_writer.write(f)
    
    return odd_path, even_path, total_pages, selected_count


def find_lp_command():
    """
    查找lp命令的完整路径
    
    Returns:
        str: lp命令的完整路径，如果找不到则返回None
    """
    # 常见的lp命令路径（macOS优先）
    possible_paths = [
        '/usr/bin/lp',  # macOS/Linux标准路径
        '/usr/local/bin/lp',  # 其他可能路径
        '/bin/lp',  # 某些系统
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    # 尝试使用which命令查找（使用shell环境）
    try:
        # 在macOS上，使用/bin/sh来确保PATH正确
        result = subprocess.run(
            ['/bin/sh', '-c', 'which lp'],
            capture_output=True,
            text=True,
            timeout=5,
            env=os.environ.copy()
        )
        if result.returncode == 0:
            found_path = result.stdout.strip()
            if found_path and os.path.exists(found_path):
                return found_path
    except:
        pass
    
    return None


def get_print_job_status(printer_name=None):
    """
    获取打印任务状态
    
    Args:
        printer_name: 打印机名称，如果为None则查询默认打印机
        
    Returns:
        dict: 包含打印任务状态的字典
    """
    lpstat_command = find_lpstat_command()
    if not lpstat_command:
        return {'error': '找不到lpstat命令'}
    
    env = os.environ.copy()
    if '/usr/bin' not in env.get('PATH', ''):
        env['PATH'] = '/usr/bin:/usr/local/bin:/bin:/usr/sbin:/sbin:' + env.get('PATH', '')
    
    try:
        # 查询打印队列
        if printer_name:
            result = subprocess.run(
                [lpstat_command, '-o', printer_name],
                capture_output=True,
                text=True,
                env=env,
                timeout=5
            )
        else:
            result = subprocess.run(
                [lpstat_command, '-o'],
                capture_output=True,
                text=True,
                env=env,
                timeout=5
            )
        
        jobs = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # 解析打印任务信息
            # 格式: "printer-name-123  user  pages  date"
            parts = line.split()
            if len(parts) >= 2:
                job_id = parts[0]  # 任务ID，如 "printer-name-123"
                status = 'queued'  # 默认状态
                
                # 检查状态关键词
                line_lower = line.lower()
                if 'printing' in line_lower or '正在打印' in line_lower:
                    status = 'printing'
                elif 'completed' in line_lower or '已完成' in line_lower:
                    status = 'completed'
                elif 'held' in line_lower or '已暂停' in line_lower:
                    status = 'held'
                elif 'cancelled' in line_lower or '已取消' in line_lower:
                    status = 'cancelled'
                
                jobs.append({
                    'job_id': job_id,
                    'status': status,
                    'info': line
                })
        
        return {
            'success': True,
            'jobs': jobs,
            'job_count': len(jobs),
            'has_jobs': len(jobs) > 0
        }
    except subprocess.TimeoutExpired:
        return {'error': '查询超时'}
    except Exception as e:
        return {'error': f'查询失败: {str(e)}'}


def print_pdf(pdf_path, printer_name=None):
    """
    打印PDF文件
    
    Args:
        pdf_path: PDF文件路径
        printer_name: 打印机名称，如果为None则使用默认打印机
        
    Returns:
        tuple: (是否成功, 错误信息, 打印任务ID)
    """
    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        return False, f'文件不存在: {pdf_path}', None
    
    # 检查文件是否可读
    if not os.access(pdf_path, os.R_OK):
        return False, f'文件不可读: {pdf_path}', None
    
    # 查找lp命令
    lp_command = find_lp_command()
    if not lp_command:
        # 尝试直接使用标准路径（macOS）
        if os.path.exists('/usr/bin/lp') and os.access('/usr/bin/lp', os.X_OK):
            lp_command = '/usr/bin/lp'
        else:
            return False, '找不到打印命令(lp)，请确保系统已安装CUPS打印服务。尝试的路径: /usr/bin/lp', None
    
    # 在macOS上，确保PATH包含/usr/bin
    env = os.environ.copy()
    if '/usr/bin' not in env.get('PATH', ''):
        env['PATH'] = '/usr/bin:/usr/local/bin:/bin:/usr/sbin:/sbin:' + env.get('PATH', '')
    
    # 验证命令是否真的存在
    if not os.path.exists(lp_command):
        return False, f'打印命令不存在: {lp_command}', None
    
    if not os.access(lp_command, os.X_OK):
        return False, f'打印命令不可执行: {lp_command}', None
    
    try:
        if printer_name:
            # 使用指定打印机
            # 在macOS上，尝试使用shell执行以确保环境正确
            cmd = f'{lp_command} -d "{printer_name}" "{pdf_path}"'
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
        else:
            # 检查是否有默认打印机
            default_printer = get_default_printer()
            if not default_printer:
                return False, '没有默认打印机，请选择打印机', None
            
            # 使用默认打印机
            # 在macOS上，尝试使用shell执行以确保环境正确
            cmd = f'{lp_command} "{pdf_path}"'
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
        
        # 尝试从输出中提取任务ID
        job_id = None
        if result.stdout:
            # lp命令输出格式: "request id is printer-name-123 (1 file(s))"
            import re
            match = re.search(r'request id is\s+(\S+)', result.stdout, re.IGNORECASE)
            if match:
                job_id = match.group(1)
        
        return True, None, job_id
    except subprocess.CalledProcessError as e:
        # 获取详细错误信息
        error_msg = e.stderr if e.stderr else e.stdout if e.stdout else str(e)
        # 常见错误信息处理
        if 'Unable to locate printer' in error_msg or 'printer does not exist' in error_msg:
            return False, f'找不到打印机: {printer_name or "默认打印机"}', None
        elif 'permission denied' in error_msg.lower():
            return False, '打印权限被拒绝，请检查系统权限设置', None
        elif 'no default destination' in error_msg.lower():
            return False, '没有默认打印机，请选择打印机', None
        elif 'No such file or directory' in error_msg:
            # macOS特殊处理：可能是动态库问题
            return False, f'打印命令执行失败: {error_msg.strip()}. 使用的命令路径: {lp_command}', None
        else:
            return False, f'打印失败: {error_msg.strip() or str(e)}. 使用的命令路径: {lp_command}', None
    except subprocess.TimeoutExpired:
        return False, '打印超时，请检查打印机状态', None
    except FileNotFoundError as e:
        return False, f'找不到打印命令: {str(e)}。命令路径: {lp_command}。请确保系统已安装CUPS打印服务', None
    except Exception as e:
        return False, f'打印失败: {str(e)}。命令路径: {lp_command}', None


@app.route('/')
def index():
    """
    主页面
    
    Returns:
        str: HTML页面
    """
    return render_template('index.html')


@app.route('/api/printers', methods=['GET'])
def get_printers():
    """
    获取可用打印机列表和默认打印机信息
    
    Returns:
        json: 打印机列表和默认打印机信息
    """
    printers = get_available_printers()
    default_printer = get_default_printer()
    
    return jsonify({
        'printers': printers,
        'default_printer': default_printer,
        'has_default': default_printer is not None
    })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    上传PDF或Word文件并分离页面
    
    Returns:
        json: 上传结果和文件信息
    """
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': '只支持PDF和Word文档（.pdf, .doc, .docx）'}), 400
    
    # 获取页码范围参数
    page_range = request.form.get('page_range', '').strip()
    
    # 保存上传的文件
    filename = file.filename
    upload_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(upload_path)
    
    # 创建临时目录用于存储分离的PDF
    temp_dir = tempfile.mkdtemp(dir=TEMP_FOLDER)
    
    try:
        # 检查文件类型，如果是Word文档则先转换为PDF
        file_ext = filename.rsplit('.', 1)[1].lower()
        pdf_path = upload_path
        
        if file_ext in ['doc', 'docx']:
            # 转换Word为PDF
            pdf_path = convert_word_to_pdf(upload_path, temp_dir)
        
        # 分离PDF页面（支持页码范围）
        odd_path, even_path, total_pages, selected_count = split_pdf_pages(
            pdf_path, temp_dir, page_range if page_range else None
        )
        
        # 计算奇偶页数量
        reader = PdfReader(pdf_path)
        selected_indices = parse_page_range(page_range if page_range else None, total_pages)
        odd_count = sum(1 for idx in selected_indices if idx % 2 == 0)
        even_count = len(selected_indices) - odd_count
        
        # 保存会话信息
        session_info = {
            'filename': filename,
            'upload_path': upload_path,
            'temp_dir': temp_dir,
            'odd_path': odd_path,
            'even_path': even_path,
            'total_pages': total_pages,
            'selected_count': selected_count,
            'page_range': page_range if page_range else None,
            'odd_printed': False,
            'even_printed': False
        }
        
        # 保存会话信息到文件
        session_file = os.path.join(temp_dir, 'session.json')
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_info, f, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'session_id': os.path.basename(temp_dir),
            'total_pages': total_pages,
            'selected_pages': selected_count,
            'odd_pages': odd_count,
            'even_pages': even_count,
            'page_range': page_range if page_range else '全部页面'
        })
    except ValueError as e:
        return jsonify({'error': f'页码范围格式错误: {str(e)}'}), 400
    except Exception as e:
        error_info = format_error_message(e)
        response_data = {
            'error': f'处理文件失败: {error_info["error"]}',
            'error_type': error_info['type']
        }
        if app.debug or DEBUG_MODE:
            response_data['traceback'] = error_info.get('traceback', '')
        return jsonify(response_data), 500


@app.route('/api/print/odd', methods=['POST'])
def print_odd_pages():
    """
    打印奇数页
    
    Returns:
        json: 打印结果
    """
    data = request.json
    session_id = data.get('session_id')
    printer_name = data.get('printer_name')
    
    if not session_id:
        return jsonify({'error': '缺少session_id'}), 400
    
    session_file = os.path.join(TEMP_FOLDER, session_id, 'session.json')
    
    if not os.path.exists(session_file):
        return jsonify({'error': '会话不存在'}), 404
    
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            session_info = json.load(f)
        
        odd_path = session_info['odd_path']
        
        # 打印奇数页
        success, error_msg, job_id = print_pdf(odd_path, printer_name)
        
        if success:
            session_info['odd_printed'] = True
            session_info['odd_job_id'] = job_id
            session_info['printer_name'] = printer_name
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_info, f, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'message': '奇数页打印任务已提交',
                'job_id': job_id
            })
        else:
            return jsonify({'error': error_msg or '打印失败'}), 500
    
    except Exception as e:
        error_info = format_error_message(e)
        response_data = {
            'error': f'打印错误: {error_info["error"]}',
            'error_type': error_info['type']
        }
        if app.debug or DEBUG_MODE:
            response_data['traceback'] = error_info.get('traceback', '')
        return jsonify(response_data), 500


@app.route('/api/print/even', methods=['POST'])
def print_even_pages():
    """
    打印偶数页
    
    Returns:
        json: 打印结果
    """
    data = request.json
    session_id = data.get('session_id')
    printer_name = data.get('printer_name')
    
    if not session_id:
        return jsonify({'error': '缺少session_id'}), 400
    
    session_file = os.path.join(TEMP_FOLDER, session_id, 'session.json')
    
    if not os.path.exists(session_file):
        return jsonify({'error': '会话不存在'}), 404
    
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            session_info = json.load(f)
        
        even_path = session_info['even_path']
        
        # 打印偶数页
        success, error_msg, job_id = print_pdf(even_path, printer_name)
        
        if success:
            session_info['even_printed'] = True
            session_info['even_job_id'] = job_id
            session_info['printer_name'] = printer_name
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_info, f, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'message': '偶数页打印任务已提交',
                'job_id': job_id
            })
        else:
            return jsonify({'error': error_msg or '打印失败'}), 500
    
    except Exception as e:
        error_info = format_error_message(e)
        response_data = {
            'error': f'打印错误: {error_info["error"]}',
            'error_type': error_info['type']
        }
        if app.debug or DEBUG_MODE:
            response_data['traceback'] = error_info.get('traceback', '')
        return jsonify(response_data), 500


@app.route('/api/print/status', methods=['GET'])
def get_print_status():
    """
    获取打印任务状态
    
    Returns:
        json: 打印任务状态
    """
    printer_name = request.args.get('printer_name')
    session_id = request.args.get('session_id')
    
    # 如果提供了session_id，从会话中获取打印机名称
    if session_id:
        session_file = os.path.join(TEMP_FOLDER, session_id, 'session.json')
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_info = json.load(f)
                printer_name = session_info.get('printer_name') or printer_name
            except:
                pass
    
    status = get_print_job_status(printer_name)
    return jsonify(status)


@app.route('/api/cleanup/<session_id>', methods=['DELETE'])
def cleanup_session(session_id):
    """
    清理会话临时文件
    
    Args:
        session_id: 会话ID
        
    Returns:
        json: 清理结果
    """
    try:
        import shutil
        session_dir = os.path.join(TEMP_FOLDER, session_id)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
        return jsonify({'success': True})
    except Exception as e:
        error_info = format_error_message(e)
        response_data = {
            'error': f'清理失败: {error_info["error"]}',
            'error_type': error_info['type']
        }
        if app.debug or DEBUG_MODE:
            response_data['traceback'] = error_info.get('traceback', '')
        return jsonify(response_data), 500


# 添加全局错误处理器
@app.errorhandler(500)
def internal_error(error):
    """
    处理500内部服务器错误
    
    Args:
        error: 错误对象
        
    Returns:
        json: 错误响应
    """
    error_info = format_error_message(error)
    response_data = {
        'error': f'服务器内部错误: {error_info["error"]}',
        'error_type': error_info['type']
    }
    if app.debug or DEBUG_MODE:
        response_data['traceback'] = error_info.get('traceback', '')
    return jsonify(response_data), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """
    处理所有未捕获的异常
    
    Args:
        e: 异常对象
        
    Returns:
        json: 错误响应
    """
    error_info = format_error_message(e)
    response_data = {
        'error': f'发生错误: {error_info["error"]}',
        'error_type': error_info['type']
    }
    if app.debug or DEBUG_MODE:
        response_data['traceback'] = error_info.get('traceback', '')
    return jsonify(response_data), 500


if __name__ == '__main__':
    # 开发模式下启用详细错误信息（app.debug=True会自动启用）
    app.run(debug=True, host='0.0.0.0', port=8000)


import json
from pathlib import Path
from typing import Optional, Dict, Any, Union

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from i18n import i18n

# 获取模板目录路径
TEMPLATE_DIR = Path(__file__).parent / 'templates'

# 懒加载 Jinja2 环境
_env: Optional[Environment] = None


def _get_jinja_env() -> Environment:
    """获取 Jinja2 环境实例（懒加载）"""
    global _env
    if _env is None:
        if not TEMPLATE_DIR.exists():
            raise FileNotFoundError(f"模板目录不存在: {TEMPLATE_DIR}")
        _env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    return _env


def _render_template(template_name: str, **kwargs) -> str:
    """渲染模板的通用方法

    Args:
        template_name: 模板文件名
        **kwargs: 模板变量

    Returns:
        渲染后的字符串

    Raises:
        TemplateNotFound: 模板文件不存在
        Exception: 模板渲染失败
    """
    try:
        env = _get_jinja_env()
        template = env.get_template(template_name)
        # 添加i18n到模板上下文
        kwargs['i18n'] = i18n
        return template.render(**kwargs)
    except TemplateNotFound as e:
        raise TemplateNotFound(f"模板文件 {template_name} 不存在") from e
    except Exception as e:
        raise Exception(f"渲染模板 {template_name} 失败: {str(e)}") from e


def get_file_system_prompt() -> str:
    """获取审核系统提示词

    Returns:
        系统提示词字符串
    """
    # 尝试使用国际化模板
    locale = i18n.get_locale()
    template_name = f'file_system_{locale}.j2'

    try:
        return _render_template(template_name)
    except TemplateNotFound:
        # 如果国际化模板不存在，使用默认模板
        return _render_template('file_system.j2')


def get_file_user_prompt(change: Dict[str, Any]) -> str:
    """获取审核用户提示词

    Args:
        change: 文件变更信息字典，包含以下字段：
            - a_mode: 文件模式A
            - b_mode: 文件模式B
            - deleted_file: 是否删除文件
            - diff: 差异内容
            - generated_file: 是否生成文件
            - new_file: 是否新文件
            - new_path: 新路径
            - old_path: 旧路径
            - renamed_file: 是否重命名文件

    Returns:
        用户提示词字符串

    Example:
        >>> change = {
        ...     'a_mode': '100644',
        ...     'b_mode': '100644',
        ...     'deleted_file': False,
        ...     'diff': '@@ -1,6 +1,7 @@\n def merge(b, c):\n-    print(b + c)\n+    print(b + c + a)',
        ...     'generated_file': False,
        ...     'new_file': False,
        ...     'new_path': 'a.py',
        ...     'old_path': 'a.py',
        ...     'renamed_file': False
        ... }
        >>> prompt = get_file_user_prompt(change)
    """
    if not isinstance(change, dict):
        raise TypeError("change 参数必须是字典类型")

    required_fields = ['new_path', 'old_path', 'diff']
    missing_fields = [field for field in required_fields if field not in change]
    if missing_fields:
        raise ValueError(f"change 字典缺少必需字段: {missing_fields}")

    # 尝试使用国际化模板
    try:
        return _render_template('file_user_i18n.j2', change=change)
    except TemplateNotFound:
        # 如果国际化模板不存在，使用默认模板
        return _render_template('file_user.j2', change=change)


def get_discussion_content(llm_resp: Dict[str, Any]) -> str:
    """获取讨论内容"""
    # 尝试使用国际化模板
    try:
        return _render_template('discussion_i18n.j2', **llm_resp)
    except TemplateNotFound:
        # 如果国际化模板不存在，使用默认模板
        return _render_template('discussion.j2', llm_resp=llm_resp)


def deserialize_llm_resp(llm_resp: Dict[str, Any]) -> str:
    """反序列化llm_resp的json格式"""
    return f"""```json
{json.dumps(llm_resp, indent=4, ensure_ascii=False)}
```"""


def parse_response(result_text: str, duration: Union[int, float]) -> Dict[str, Any]:
    """解析响应
    
    Args:
        result_text: 包含JSON的响应文本
        duration: 响应耗时
        
    Returns:
        解析后的字典，包含duration字段
        
    Raises:
        ValueError: 解析失败或未找到有效JSON
    """
    try:
        # 尝试提取JSON部分
        start_idx = result_text.find('{')
        end_idx = result_text.rfind('}') + 1

        if start_idx == -1 or end_idx == 0:
            raise ValueError("未找到有效的JSON部分")

        json_text = result_text[start_idx:end_idx]
        parsed_data = json.loads(json_text)

        if not isinstance(parsed_data, dict):
            raise ValueError("JSON内容不是字典格式")

        return {**parsed_data, 'duration': duration}
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {e}") from e
    except Exception as e:
        raise ValueError(f"解析响应失败: {e}") from e


# 支持的文件扩展名集合（使用集合提高查找效率）
SUPPORTED_EXTENSIONS = {
    # C/C++
    ".c", ".h", ".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++",
    # C#
    ".cs",
    # Go
    ".go",
    # Rust
    ".rs",
    # Java
    ".java",
    # Kotlin
    ".kt", ".kts",
    # Swift
    ".swift",
    # Objective-C/C++
    ".m", ".mm",
    # iOS 界面/配置
    ".storyboard", ".xib", ".xcassets",
    # 鸿蒙 (HarmonyOS ArkTS)
    ".ets", ".hml",
    # JavaScript/TypeScript
    ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx",
    # 小程序相关
    ".wxml", ".wxs",  # 微信小程序
    ".axml", ".sjs",  # 支付宝小程序
    ".ttml",  # 抖音/字节小程序
    ".ksml",  # 快手小程序
    ".swan",  # 百度小程序
    # Flutter
    ".dart",
    # Vue
    ".vue",
    # Web相关
    ".html", ".htm", ".css", ".scss", ".less",
    # PHP
    ".php", ".phtml",
    # Python
    ".py", ".pyw", ".pyi",
    # Ruby
    ".rb", ".erb", ".rake",
    # Shell
    ".sh", ".bash", ".zsh", ".ksh",
    # Lua
    ".lua",
    # 配置文件
    ".json", ".yaml", ".yml", ".xml",
    # Makefile
    ".mk",
}

# 特殊文件名（不带扩展名）
SPECIAL_FILENAMES = {"Makefile"}


def is_supported_file(file_path: str) -> bool:
    """判断文件是否为支持的文件类型
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否为支持的文件类型
        
    Example:
        >>> is_supported_file("main.py")
        True
        >>> is_supported_file("README.md")
        False
        >>> is_supported_file("Makefile")
        True
    """
    if not file_path:
        return False

    # 检查特殊文件名
    if file_path in SPECIAL_FILENAMES:
        return True

    # 检查文件扩展名
    path = Path(file_path)
    if path.suffix.lower() in SUPPORTED_EXTENSIONS:
        return True

    return False

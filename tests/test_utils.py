#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils 模块测试
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from jinja2 import TemplateNotFound

from utils import (
    _get_jinja_env, _render_template, get_file_system_prompt,
    get_file_user_prompt, get_discussion_content, parse_response,
    is_supported_file, SUPPORTED_EXTENSIONS
)


class TestJinjaEnvironment:
    """Jinja2 环境测试"""
    
    def test_get_jinja_env(self, temp_template_dir):
        """测试获取 Jinja2 环境"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            env = _get_jinja_env()
            assert env is not None
            assert env.loader is not None
    
    def test_get_jinja_env_missing_dir(self):
        """测试模板目录不存在的情况"""
        with patch('utils.TEMPLATE_DIR', Path('/nonexistent/path')):
            with pytest.raises(FileNotFoundError, match="模板目录不存在"):
                _get_jinja_env()
    
    def test_jinja_env_singleton(self, temp_template_dir):
        """测试 Jinja2 环境单例模式"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            # 重置全局变量
            import utils
            utils._env = None
            
            env1 = _get_jinja_env()
            env2 = _get_jinja_env()
            assert env1 is env2


class TestTemplateRendering:
    """模板渲染测试"""
    
    def test_render_template_success(self, temp_template_dir):
        """测试成功渲染模板"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            # 重置环境
            import utils
            utils._env = None
            
            result = _render_template('file_system_zh_CN.j2')
            assert result == '你是一个代码审查助手。请审查以下代码变更。'
    
    def test_render_template_with_variables(self, temp_template_dir):
        """测试带变量的模板渲染"""
        # 创建带变量的模板
        template_content = '文件: {{ filename }}, 作者: {{ author }}'
        (temp_template_dir / 'test_vars.j2').write_text(template_content)
        
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            result = _render_template('test_vars.j2', filename='test.py', author='张三')
            assert result == '文件: test.py, 作者: 张三'
    
    def test_render_template_not_found(self, temp_template_dir):
        """测试模板文件不存在"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            with pytest.raises(TemplateNotFound, match="模板文件 nonexistent.j2 不存在"):
                _render_template('nonexistent.j2')
    
    def test_render_template_with_i18n(self, temp_template_dir):
        """测试模板中的国际化功能"""
        # 创建使用 i18n 的模板
        template_content = '{{ i18n.t("status.accepted") }}'
        (temp_template_dir / 'test_i18n.j2').write_text(template_content)
        
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            result = _render_template('test_i18n.j2')
            # 验证 i18n 对象被正确传递
            assert 'accepted' in result or '已接受' in result


class TestSystemPrompt:
    """系统提示词测试"""
    
    def test_get_file_system_prompt_with_locale(self, temp_template_dir):
        """测试根据语言获取系统提示词"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            # 测试中文
            with patch('utils.i18n.get_locale', return_value='zh_CN'):
                prompt = get_file_system_prompt()
                assert prompt == '你是一个代码审查助手。请审查以下代码变更。'
            
            # 测试英文
            with patch('utils.i18n.get_locale', return_value='en_US'):
                prompt = get_file_system_prompt()
                assert prompt == 'You are a code review assistant. Please review the following code changes.'
    
    def test_get_file_system_prompt_fallback(self, temp_template_dir):
        """测试系统提示词回退机制"""
        # 创建默认模板
        (temp_template_dir / 'file_system.j2').write_text('Default system prompt')
        
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            # 测试不存在的语言，应该回退到默认模板
            with patch('utils.i18n.get_locale', return_value='fr_FR'):
                prompt = get_file_system_prompt()
                assert prompt == 'Default system prompt'


class TestUserPrompt:
    """用户提示词测试"""
    
    def test_get_file_user_prompt_success(self, temp_template_dir, sample_change_data):
        """测试成功获取用户提示词"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            prompt = get_file_user_prompt(sample_change_data)
            assert 'a.py' in prompt
            assert 'def merge(b, c):' in prompt
    
    def test_get_file_user_prompt_invalid_input(self):
        """测试无效输入"""
        # 测试非字典类型
        with pytest.raises(TypeError, match="change 参数必须是字典类型"):
            get_file_user_prompt("invalid")
        
        # 测试缺少必需字段
        with pytest.raises(ValueError, match="change 字典缺少必需字段"):
            get_file_user_prompt({'old_path': 'test.py'})
    
    def test_get_file_user_prompt_required_fields(self, temp_template_dir):
        """测试必需字段验证"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            # 包含所有必需字段
            valid_change = {
                'new_path': 'test.py',
                'old_path': 'test.py',
                'diff': '@@ -1,1 +1,1 @@\n-old\n+new'
            }
            
            prompt = get_file_user_prompt(valid_change)
            assert 'test.py' in prompt
    
    def test_get_file_user_prompt_fallback(self, temp_template_dir, sample_change_data):
        """测试用户提示词回退机制"""
        # 创建默认模板
        (temp_template_dir / 'file_user.j2').write_text('Default user prompt: {{ change.new_path }}')
        
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            # 删除国际化模板，测试回退
            (temp_template_dir / 'file_user_i18n.j2').unlink()
            
            prompt = get_file_user_prompt(sample_change_data)
            assert prompt == 'Default user prompt: a.py'


class TestDiscussionContent:
    """讨论内容测试"""
    
    def test_get_discussion_content_success(self, temp_template_dir, sample_llm_response):
        """测试成功获取讨论内容"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            content = get_discussion_content(sample_llm_response)
            assert '## 代码审查结果' in content
            assert '评分: 7/10' in content
            assert '代码质量良好，需要小幅改进' in content
    
    def test_get_discussion_content_fallback(self, temp_template_dir, sample_llm_response):
        """测试讨论内容回退机制"""
        # 创建默认模板
        (temp_template_dir / 'discussion.j2').write_text('Score: {{ score }}, Summary: {{ summary }}')
        
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            # 删除国际化模板
            (temp_template_dir / 'discussion_i18n.j2').unlink()
            
            content = get_discussion_content(sample_llm_response)
            assert content == 'Score: 7, Summary: 代码质量良好，需要小幅改进'


class TestResponseParsing:
    """响应解析测试"""
    
    def test_parse_response_success(self):
        """测试成功解析响应"""
        response_text = '''
        这是一些前置文本
        {
            "issues": ["问题1", "问题2"],
            "suggestions": ["建议1", "建议2"],
            "score": 8,
            "summary": "总体良好"
        }
        这是一些后置文本
        '''
        
        result = parse_response(response_text, 2.5)
        
        assert result['issues'] == ["问题1", "问题2"]
        assert result['suggestions'] == ["建议1", "建议2"]
        assert result['score'] == 8
        assert result['summary'] == "总体良好"
        assert result['duration'] == 2.5
    
    def test_parse_response_no_json(self):
        """测试没有 JSON 的响应"""
        response_text = "这是一个没有 JSON 的响应"
        
        with pytest.raises(ValueError, match="未找到有效的JSON部分"):
            parse_response(response_text, 1.0)
    
    def test_parse_response_invalid_json(self):
        """测试无效 JSON"""
        response_text = '''
        {
            "invalid": json,
            "missing": quote
        }
        '''
        
        with pytest.raises(ValueError, match="JSON解析失败"):
            parse_response(response_text, 1.0)
    
    def test_parse_response_non_dict_json(self):
        """测试非字典 JSON"""
        response_text = '["这是一个数组", "不是字典"]'
        
        with pytest.raises(ValueError, match="JSON内容不是字典格式"):
            parse_response(response_text, 1.0)
    
    def test_parse_response_nested_json(self):
        """测试嵌套 JSON"""
        response_text = '''
        {
            "data": {
                "issues": ["嵌套问题"],
                "metadata": {
                    "version": "1.0",
                    "timestamp": "2024-01-01"
                }
            },
            "score": 9
        }
        '''
        
        result = parse_response(response_text, 3.0)
        
        assert result['data']['issues'] == ["嵌套问题"]
        assert result['data']['metadata']['version'] == "1.0"
        assert result['score'] == 9
        assert result['duration'] == 3.0
    
    def test_parse_response_chinese_content(self):
        """测试中文内容解析"""
        response_text = '''
        {
            "问题": ["中文问题描述"],
            "建议": ["中文建议内容"],
            "评分": 7,
            "总结": "代码质量需要改进，特别是在错误处理方面。"
        }
        '''
        
        result = parse_response(response_text, 1.5)
        
        assert result['问题'] == ["中文问题描述"]
        assert result['建议'] == ["中文建议内容"]
        assert result['评分'] == 7
        assert result['总结'] == "代码质量需要改进，特别是在错误处理方面。"
        assert result['duration'] == 1.5


class TestFileSupportCheck:
    """文件支持检查测试"""
    
    def test_supported_extensions_exist(self):
        """测试支持的扩展名集合存在"""
        assert isinstance(SUPPORTED_EXTENSIONS, set)
        assert len(SUPPORTED_EXTENSIONS) > 0
    
    def test_is_supported_file_python(self):
        """测试 Python 文件支持"""
        assert is_supported_file('test.py') is True
        assert is_supported_file('src/main.py') is True
        assert is_supported_file('/path/to/script.py') is True
    
    def test_is_supported_file_javascript(self):
        """测试 JavaScript 文件支持"""
        assert is_supported_file('app.js') is True
        assert is_supported_file('component.jsx') is True
        assert is_supported_file('types.ts') is True
        assert is_supported_file('component.tsx') is True
    
    def test_is_supported_file_java(self):
        """测试 Java 文件支持"""
        assert is_supported_file('Main.java') is True
        assert is_supported_file('src/com/example/App.java') is True
    
    def test_is_supported_file_c_cpp(self):
        """测试 C/C++ 文件支持"""
        assert is_supported_file('main.c') is True
        assert is_supported_file('app.cpp') is True
        assert is_supported_file('header.h') is True
        assert is_supported_file('header.hpp') is True
    
    def test_is_supported_file_go(self):
        """测试 Go 文件支持"""
        assert is_supported_file('main.go') is True
        assert is_supported_file('src/handler.go') is True
    
    def test_is_supported_file_unsupported(self):
        """测试不支持的文件"""
        assert is_supported_file('README.md') is False
        assert is_supported_file('config.txt') is False
        assert is_supported_file('image.png') is False
        assert is_supported_file('data.json') is False
        assert is_supported_file('style.css') is False
    
    def test_is_supported_file_case_sensitivity(self):
        """测试大小写敏感性"""
        assert is_supported_file('Test.PY') is False  # 大写扩展名不支持
        assert is_supported_file('Test.py') is True   # 小写扩展名支持
    
    def test_is_supported_file_no_extension(self):
        """测试没有扩展名的文件"""
        assert is_supported_file('Makefile') is False
        assert is_supported_file('README') is False
        assert is_supported_file('') is False
    
    def test_is_supported_file_multiple_dots(self):
        """测试多个点的文件名"""
        assert is_supported_file('test.min.js') is True
        assert is_supported_file('config.local.py') is True
        assert is_supported_file('app.test.ts') is True
    
    def test_supported_extensions_completeness(self):
        """测试支持的扩展名完整性"""
        # 验证常见编程语言的扩展名都被包含
        expected_extensions = {
            '.py', '.js', '.ts', '.java', '.go', '.rs', '.c', '.cpp', '.h',
            '.cs', '.kt', '.swift', '.dart', '.php', '.rb', '.scala'
        }
        
        for ext in expected_extensions:
            assert ext in SUPPORTED_EXTENSIONS, f"扩展名 {ext} 应该被支持"


class TestUtilsIntegration:
    """utils 模块集成测试"""
    
    def test_complete_template_workflow(self, temp_template_dir, sample_change_data, sample_llm_response):
        """测试完整的模板工作流"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            # 1. 获取系统提示词
            system_prompt = get_file_system_prompt()
            assert len(system_prompt) > 0
            
            # 2. 获取用户提示词
            user_prompt = get_file_user_prompt(sample_change_data)
            assert 'a.py' in user_prompt
            
            # 3. 获取讨论内容
            discussion = get_discussion_content(sample_llm_response)
            assert '代码审查结果' in discussion
    
    def test_error_handling_chain(self, temp_template_dir):
        """测试错误处理链"""
        with patch('utils.TEMPLATE_DIR', temp_template_dir):
            import utils
            utils._env = None
            
            # 测试模板不存在时的错误传播
            with pytest.raises(TemplateNotFound):
                _render_template('nonexistent_template.j2')
            
            # 测试无效变更数据的错误传播
            with pytest.raises(TypeError):
                get_file_user_prompt(None)
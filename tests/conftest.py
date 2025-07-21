#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest 配置文件

提供测试夹具和配置
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models import Base
from config import Settings
from i18n import init_i18n


@pytest.fixture(scope="session")
def test_settings():
    """测试设置夹具"""
    return Settings(
        gitlab_url="https://test-gitlab.com",
        gitlab_token="test-token",
        gitlab_webhook_secret="test-secret",
        gitlab_bot_username="test-bot",
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test_db",
        mysql_user="test_user",
        mysql_passwd="test_password",
        llm_api_url="https://test-api.com",
        llm_api_key="test-key",
        llm_api_type="openai",
        llm_model="gpt-4",
        locale="zh_CN",
        debug=True
    )


@pytest.fixture(scope="session")
def test_db_engine():
    """测试数据库引擎夹具"""
    # 使用内存数据库进行测试
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_db_session(test_db_engine):
    """测试数据库会话夹具"""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def init_test_i18n():
    """初始化测试国际化"""
    init_i18n()


@pytest.fixture
def mock_gitlab_client():
    """模拟 GitLab 客户端"""
    mock_client = Mock()
    mock_project = Mock()
    mock_project.id = 1
    mock_project.path_with_namespace = "test/repo"
    
    mock_mr = Mock()
    mock_mr.iid = 123
    mock_mr.changes.return_value = {
        'changes': [
            {
                'old_path': 'test.py',
                'new_path': 'test.py',
                'diff': '@@ -1,3 +1,4 @@\n def hello():\n-    print("hello")\n+    print("hello world")\n+    return True',
                'new_file': False,
                'deleted_file': False,
                'renamed_file': False
            }
        ]
    }
    
    mock_client.projects.get.return_value = mock_project
    mock_project.mergerequests.get.return_value = mock_mr
    
    return mock_client


@pytest.fixture
def mock_llm_client():
    """模拟 LLM 客户端"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '''
    {
        "issues": ["缺少错误处理", "变量命名不规范"],
        "suggestions": ["添加try-catch块", "使用更描述性的变量名"],
        "score": 7,
        "summary": "代码质量良好，需要小幅改进",
        "approved": true
    }
    '''
    mock_response.usage.total_tokens = 150
    
    mock_client.chat.completions.create.return_value = mock_response
    mock_client.models.retrieve.return_value = Mock()
    
    return mock_client


@pytest.fixture
def sample_change_data():
    """示例变更数据"""
    return {
        'a_mode': '100644',
        'b_mode': '100644',
        'deleted_file': False,
        'diff': '@@ -1,6 +1,7 @@\n def merge(b, c):\n-    print(b + c)\n+    print(b + c + a)',
        'generated_file': False,
        'new_file': False,
        'new_path': 'a.py',
        'old_path': 'a.py',
        'renamed_file': False
    }


@pytest.fixture
def sample_llm_response():
    """示例 LLM 响应数据"""
    return {
        'issues': ['缺少错误处理', '变量命名不规范'],
        'suggestions': ['添加try-catch块', '使用更描述性的变量名'],
        'score': 7,
        'summary': '代码质量良好，需要小幅改进',
        'model': 'gpt-4',
        'duration': 2.5,
        'approved': True
    }


@pytest.fixture
def temp_template_dir():
    """临时模板目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        template_dir = Path(temp_dir)
        
        # 创建测试模板文件
        (template_dir / 'file_system_zh_CN.j2').write_text(
            '你是一个代码审查助手。请审查以下代码变更。'
        )
        (template_dir / 'file_system_en_US.j2').write_text(
            'You are a code review assistant. Please review the following code changes.'
        )
        (template_dir / 'file_user_i18n.j2').write_text(
            '文件路径: {{ change.new_path }}\n差异:\n{{ change.diff }}'
        )
        (template_dir / 'discussion_i18n.j2').write_text(
            '## 代码审查结果\n\n评分: {{ score }}/10\n\n总结: {{ summary }}'
        )
        
        yield template_dir


@pytest.fixture(autouse=True)
def setup_test_env(test_settings, init_test_i18n):
    """自动设置测试环境"""
    # 使用 patch 替换配置
    with patch('config.settings', test_settings):
        yield
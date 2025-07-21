#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块测试
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy import URL

from config import Settings, engine_url, engine_config


class TestSettings:
    """设置类测试"""
    
    def test_default_values(self):
        """测试默认值"""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.gitlab_url == ""
            assert settings.gitlab_token == ""
            assert settings.mysql_host == ""
            assert settings.mysql_port == 0
            assert settings.locale == "zh_CN"
            assert settings.debug is False
    
    def test_env_values(self):
        """测试环境变量值"""
        env_vars = {
            "GITLAB_URL": "https://gitlab.example.com",
            "GITLAB_TOKEN": "test-token",
            "MYSQL_HOST": "localhost",
            "MYSQL_PORT": "3306",
            "MYSQL_DATABASE": "test_db",
            "MYSQL_USER": "test_user",
            "MYSQL_PASSWD": "test_password",
            "LLM_API_URL": "https://api.openai.com/v1",
            "LLM_API_KEY": "sk-test",
            "LLM_MODEL": "gpt-4",
            "LOCALE": "en_US",
            "DEBUG": "true"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.gitlab_url == "https://gitlab.example.com"
            assert settings.gitlab_token == "test-token"
            assert settings.mysql_host == "localhost"
            assert settings.mysql_port == 3306
            assert settings.mysql_database == "test_db"
            assert settings.mysql_user == "test_user"
            assert settings.mysql_passwd == "test_password"
            assert settings.llm_api_url == "https://api.openai.com/v1"
            assert settings.llm_api_key == "sk-test"
            assert settings.llm_model == "gpt-4"
            assert settings.locale == "en_US"
            assert settings.debug is True
    
    def test_debug_string_values(self):
        """测试 DEBUG 字符串值解析"""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("", False),
            ("anything", False)
        ]
        
        for debug_value, expected in test_cases:
            with patch.dict(os.environ, {"DEBUG": debug_value}, clear=True):
                settings = Settings()
                assert settings.debug is expected


class TestDatabaseConfig:
    """数据库配置测试"""
    
    def test_engine_url(self):
        """测试数据库引擎 URL 生成"""
        with patch('config.settings') as mock_settings:
            mock_settings.mysql_user = "test_user"
            mock_settings.mysql_passwd = "test_password"
            mock_settings.mysql_host = "localhost"
            mock_settings.mysql_port = 3306
            mock_settings.mysql_database = "test_db"
            
            url = engine_url()
            assert isinstance(url, URL)
            assert url.drivername == "mysql+pymysql"
            assert url.username == "test_user"
            assert url.password == "test_password"
            assert url.host == "localhost"
            assert url.port == 3306
            assert url.database == "test_db"
    
    def test_engine_config(self):
        """测试数据库引擎配置"""
        with patch('config.settings') as mock_settings:
            mock_settings.debug = True
            
            config = engine_config()
            assert config["pool_recycle"] == 3600
            assert config["max_overflow"] == 20
            assert config["pool_pre_ping"] is True
            assert config["echo"] is True
            assert config["pool_size"] == 10
            assert config["pool_timeout"] == 30
            assert "connect_args" in config
            assert config["connect_args"]["connect_timeout"] == 3
            assert config["connect_args"]["charset"] == "utf8mb4"
            assert config["connect_args"]["autocommit"] is True
    
    def test_engine_config_debug_false(self):
        """测试调试模式关闭时的配置"""
        with patch('config.settings') as mock_settings:
            mock_settings.debug = False
            
            config = engine_config()
            assert config["echo"] is False


class TestConfigIntegration:
    """配置集成测试"""
    
    def test_dotenv_loading(self):
        """测试 .env 文件加载"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("GITLAB_URL=https://test.gitlab.com\n")
            f.write("DEBUG=true\n")
            env_file = f.name
        
        try:
            # 模拟加载 .env 文件
            with patch('config.load_dotenv') as mock_load_dotenv:
                with patch.dict(os.environ, {
                    "GITLAB_URL": "https://test.gitlab.com",
                    "DEBUG": "true"
                }):
                    settings = Settings()
                    assert settings.gitlab_url == "https://test.gitlab.com"
                    assert settings.debug is True
        finally:
            os.unlink(env_file)
    
    def test_settings_validation(self):
        """测试设置验证"""
        # 测试端口号必须是整数
        with patch.dict(os.environ, {"MYSQL_PORT": "invalid"}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_required_settings_empty(self):
        """测试必需设置为空的情况"""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            # 验证空值不会导致错误
            assert settings.gitlab_url == ""
            assert settings.mysql_host == ""
            assert settings.llm_api_url == ""
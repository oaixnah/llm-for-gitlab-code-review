#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主应用模块测试
"""

from unittest.mock import patch, Mock, MagicMock
import json
import logging

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

# 需要在导入 main 之前设置模拟
with patch('main.Settings'), \
     patch('main.gitlab.Gitlab'), \
     patch('main.LLMService'), \
     patch('main.ReviewManager'), \
     patch('main.init_i18n'):
    from main import app, webhook_handler, review_manager


class TestAppInitialization:
    """应用初始化测试"""
    
    def test_app_creation(self):
        """测试 FastAPI 应用创建"""
        assert app is not None
        assert app.title == "GitLab Code Review LLM Service"
        assert app.version == "1.0.0"
    
    @patch('main.Settings')
    @patch('main.gitlab.Gitlab')
    @patch('main.LLMService')
    @patch('main.ReviewManager')
    @patch('main.init_i18n')
    def test_dependencies_initialization(self, mock_init_i18n, mock_review_manager, 
                                       mock_llm_service, mock_gitlab, mock_settings):
        """测试依赖项初始化"""
        # 重新导入以触发初始化
        import importlib
        import main
        importlib.reload(main)
        
        # 验证各个组件被正确初始化
        mock_settings.assert_called_once()
        mock_gitlab.assert_called_once()
        mock_llm_service.assert_called_once()
        mock_review_manager.assert_called_once()
        mock_init_i18n.assert_called_once()


class TestWebhookHandler:
    """Webhook 处理器测试"""
    
    def setup_method(self):
        """测试设置"""
        self.client = TestClient(app)
    
    def test_webhook_merge_request_opened(self):
        """测试合并请求打开事件"""
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "object_attributes": {
                "action": "open",
                "id": 123,
                "target_project_id": 1
            },
            "project": {
                "id": 1
            }
        }
        
        with patch.object(review_manager, 'process_merge_request', return_value=True) as mock_process:
            response = self.client.post("/webhook", json=webhook_data)
            
            assert response.status_code == 200
            assert response.json() == {"status": "success", "message": "Merge request processed successfully"}
            
            # 验证处理器被调用
            mock_process.assert_called_once_with(1, 123)
    
    def test_webhook_merge_request_updated(self):
        """测试合并请求更新事件"""
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "object_attributes": {
                "action": "update",
                "id": 124,
                "target_project_id": 2
            },
            "project": {
                "id": 2
            }
        }
        
        with patch.object(review_manager, 'process_merge_request', return_value=True) as mock_process:
            response = self.client.post("/webhook", json=webhook_data)
            
            assert response.status_code == 200
            assert response.json() == {"status": "success", "message": "Merge request processed successfully"}
            
            mock_process.assert_called_once_with(2, 124)
    
    def test_webhook_merge_request_reopen(self):
        """测试合并请求重新打开事件"""
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "object_attributes": {
                "action": "reopen",
                "id": 125,
                "target_project_id": 3
            },
            "project": {
                "id": 3
            }
        }
        
        with patch.object(review_manager, 'process_merge_request', return_value=True) as mock_process:
            response = self.client.post("/webhook", json=webhook_data)
            
            assert response.status_code == 200
            mock_process.assert_called_once_with(3, 125)
    
    def test_webhook_merge_request_ignored_actions(self):
        """测试忽略的合并请求动作"""
        ignored_actions = ["close", "merge", "approved", "unapproved"]
        
        for action in ignored_actions:
            webhook_data = {
                "object_kind": "merge_request",
                "event_type": "merge_request",
                "object_attributes": {
                    "action": action,
                    "id": 126,
                    "target_project_id": 4
                },
                "project": {
                    "id": 4
                }
            }
            
            with patch.object(review_manager, 'process_merge_request') as mock_process:
                response = self.client.post("/webhook", json=webhook_data)
                
                assert response.status_code == 200
                assert response.json() == {"status": "ignored", "message": f"Action '{action}' is not processed"}
                
                # 验证处理器没有被调用
                mock_process.assert_not_called()
    
    def test_webhook_non_merge_request_events(self):
        """测试非合并请求事件"""
        non_mr_events = [
            {"object_kind": "push", "event_type": "push"},
            {"object_kind": "issue", "event_type": "issue"},
            {"object_kind": "note", "event_type": "note"},
            {"object_kind": "pipeline", "event_type": "pipeline"}
        ]
        
        for event_data in non_mr_events:
            with patch.object(review_manager, 'process_merge_request') as mock_process:
                response = self.client.post("/webhook", json=event_data)
                
                assert response.status_code == 200
                assert response.json() == {"status": "ignored", "message": "Not a merge request event"}
                
                mock_process.assert_not_called()
    
    def test_webhook_missing_required_fields(self):
        """测试缺少必需字段的 webhook"""
        incomplete_data_sets = [
            # 缺少 object_kind
            {
                "event_type": "merge_request",
                "object_attributes": {"action": "open", "id": 123, "target_project_id": 1}
            },
            # 缺少 object_attributes
            {
                "object_kind": "merge_request",
                "event_type": "merge_request"
            },
            # 缺少 action
            {
                "object_kind": "merge_request",
                "event_type": "merge_request",
                "object_attributes": {"id": 123, "target_project_id": 1}
            },
            # 缺少 id
            {
                "object_kind": "merge_request",
                "event_type": "merge_request",
                "object_attributes": {"action": "open", "target_project_id": 1}
            },
            # 缺少 target_project_id
            {
                "object_kind": "merge_request",
                "event_type": "merge_request",
                "object_attributes": {"action": "open", "id": 123}
            }
        ]
        
        for incomplete_data in incomplete_data_sets:
            response = self.client.post("/webhook", json=incomplete_data)
            
            # 应该返回 400 错误或忽略
            assert response.status_code in [200, 400]
            
            if response.status_code == 200:
                # 如果返回 200，应该是忽略消息
                response_data = response.json()
                assert response_data["status"] in ["ignored", "error"]
    
    def test_webhook_processing_error(self):
        """测试处理过程中的错误"""
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "object_attributes": {
                "action": "open",
                "id": 127,
                "target_project_id": 5
            },
            "project": {
                "id": 5
            }
        }
        
        # 模拟处理错误
        with patch.object(review_manager, 'process_merge_request', 
                         side_effect=Exception("Processing failed")) as mock_process:
            response = self.client.post("/webhook", json=webhook_data)
            
            assert response.status_code == 500
            response_data = response.json()
            assert response_data["status"] == "error"
            assert "Processing failed" in response_data["message"]
            
            mock_process.assert_called_once_with(5, 127)
    
    def test_webhook_invalid_json(self):
        """测试无效的 JSON 数据"""
        response = self.client.post("/webhook", data="invalid json")
        
        # FastAPI 应该返回 422 错误（无法解析 JSON）
        assert response.status_code == 422
    
    def test_webhook_empty_payload(self):
        """测试空的 payload"""
        response = self.client.post("/webhook", json={})
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "ignored"
        assert "Not a merge request event" in response_data["message"]


class TestHealthCheck:
    """健康检查测试"""
    
    def setup_method(self):
        """测试设置"""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """测试根端点"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        response_data = response.json()
        assert "message" in response_data
        assert "GitLab Code Review LLM Service" in response_data["message"]
    
    def test_health_endpoint_if_exists(self):
        """测试健康检查端点（如果存在）"""
        # 尝试访问常见的健康检查端点
        health_endpoints = ["/health", "/healthz", "/status"]
        
        for endpoint in health_endpoints:
            response = self.client.get(endpoint)
            # 如果端点存在，应该返回 200；如果不存在，返回 404
            assert response.status_code in [200, 404]


class TestLoggingConfiguration:
    """日志配置测试"""
    
    @patch('main.Settings')
    def test_logging_setup_debug_mode(self, mock_settings):
        """测试调试模式下的日志配置"""
        # 模拟调试模式
        mock_settings_instance = Mock()
        mock_settings_instance.debug = True
        mock_settings.return_value = mock_settings_instance
        
        with patch('logging.basicConfig') as mock_basic_config:
            # 重新导入以触发日志配置
            import importlib
            import main
            importlib.reload(main)
            
            # 验证日志配置被调用
            mock_basic_config.assert_called()
            
            # 检查是否设置了正确的日志级别
            call_args = mock_basic_config.call_args
            if call_args and 'level' in call_args[1]:
                assert call_args[1]['level'] == logging.DEBUG
    
    @patch('main.Settings')
    def test_logging_setup_production_mode(self, mock_settings):
        """测试生产模式下的日志配置"""
        # 模拟生产模式
        mock_settings_instance = Mock()
        mock_settings_instance.debug = False
        mock_settings.return_value = mock_settings_instance
        
        with patch('logging.basicConfig') as mock_basic_config:
            # 重新导入以触发日志配置
            import importlib
            import main
            importlib.reload(main)
            
            # 验证日志配置被调用
            mock_basic_config.assert_called()
            
            # 检查是否设置了正确的日志级别
            call_args = mock_basic_config.call_args
            if call_args and 'level' in call_args[1]:
                assert call_args[1]['level'] == logging.INFO


class TestIntegrationScenarios:
    """集成场景测试"""
    
    def setup_method(self):
        """测试设置"""
        self.client = TestClient(app)
    
    def test_complete_merge_request_workflow(self):
        """测试完整的合并请求工作流"""
        # 模拟一个完整的 GitLab webhook 负载
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "user": {
                "id": 1,
                "name": "Test User",
                "username": "testuser",
                "email": "test@example.com"
            },
            "project": {
                "id": 1,
                "name": "Test Project",
                "description": "A test project",
                "web_url": "https://gitlab.example.com/test/project",
                "namespace": "test",
                "visibility_level": 20
            },
            "object_attributes": {
                "id": 123,
                "target_branch": "main",
                "source_branch": "feature/test",
                "source_project_id": 1,
                "target_project_id": 1,
                "title": "Test merge request",
                "description": "This is a test merge request",
                "state": "opened",
                "action": "open",
                "merge_status": "can_be_merged",
                "url": "https://gitlab.example.com/test/project/-/merge_requests/123",
                "source": {
                    "name": "Test Project",
                    "description": "A test project",
                    "web_url": "https://gitlab.example.com/test/project",
                    "namespace": "test",
                    "visibility_level": 20
                },
                "target": {
                    "name": "Test Project",
                    "description": "A test project",
                    "web_url": "https://gitlab.example.com/test/project",
                    "namespace": "test",
                    "visibility_level": 20
                },
                "last_commit": {
                    "id": "abc123def456",
                    "message": "Add new feature",
                    "timestamp": "2023-01-01T12:00:00Z",
                    "url": "https://gitlab.example.com/test/project/-/commit/abc123def456",
                    "author": {
                        "name": "Test User",
                        "email": "test@example.com"
                    }
                },
                "work_in_progress": False,
                "assignee_id": None,
                "assignee_ids": [],
                "reviewer_ids": []
            },
            "labels": [],
            "changes": {
                "updated_at": {
                    "previous": "2023-01-01T11:00:00Z",
                    "current": "2023-01-01T12:00:00Z"
                }
            },
            "repository": {
                "name": "Test Project",
                "url": "git@gitlab.example.com:test/project.git",
                "description": "A test project",
                "homepage": "https://gitlab.example.com/test/project"
            }
        }
        
        with patch.object(review_manager, 'process_merge_request', return_value=True) as mock_process:
            response = self.client.post("/webhook", json=webhook_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "success"
            assert "processed successfully" in response_data["message"]
            
            # 验证使用正确的参数调用了处理器
            mock_process.assert_called_once_with(1, 123)
    
    def test_multiple_concurrent_webhooks(self):
        """测试多个并发 webhook 请求"""
        import threading
        import time
        
        results = []
        
        def send_webhook(mr_id):
            webhook_data = {
                "object_kind": "merge_request",
                "event_type": "merge_request",
                "object_attributes": {
                    "action": "open",
                    "id": mr_id,
                    "target_project_id": 1
                },
                "project": {"id": 1}
            }
            
            with patch.object(review_manager, 'process_merge_request', return_value=True):
                response = self.client.post("/webhook", json=webhook_data)
                results.append((mr_id, response.status_code, response.json()))
        
        # 创建多个线程同时发送 webhook
        threads = []
        for i in range(5):
            thread = threading.Thread(target=send_webhook, args=(100 + i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有请求都成功处理
        assert len(results) == 5
        for mr_id, status_code, response_data in results:
            assert status_code == 200
            assert response_data["status"] == "success"
    
    def test_webhook_with_special_characters(self):
        """测试包含特殊字符的 webhook"""
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "object_attributes": {
                "action": "open",
                "id": 128,
                "target_project_id": 1,
                "title": "修复 bug：处理特殊字符 & 符号 < > \" '",
                "description": "这个 MR 包含中文和特殊字符：\n- 修复了编码问题\n- 添加了 UTF-8 支持\n- 处理了 JSON 转义"
            },
            "project": {"id": 1}
        }
        
        with patch.object(review_manager, 'process_merge_request', return_value=True) as mock_process:
            response = self.client.post("/webhook", json=webhook_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "success"
            
            mock_process.assert_called_once_with(1, 128)
    
    def test_webhook_large_payload(self):
        """测试大型 payload"""
        # 创建一个包含大量数据的 webhook
        large_description = "This is a very long description. " * 1000  # 约 34KB
        
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "object_attributes": {
                "action": "open",
                "id": 129,
                "target_project_id": 1,
                "description": large_description
            },
            "project": {"id": 1},
            "changes": {
                "files": [f"file_{i}.py" for i in range(100)]  # 100 个文件
            }
        }
        
        with patch.object(review_manager, 'process_merge_request', return_value=True) as mock_process:
            response = self.client.post("/webhook", json=webhook_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "success"
            
            mock_process.assert_called_once_with(1, 129)


class TestErrorRecovery:
    """错误恢复测试"""
    
    def setup_method(self):
        """测试设置"""
        self.client = TestClient(app)
    
    def test_recovery_after_processing_error(self):
        """测试处理错误后的恢复"""
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "object_attributes": {
                "action": "open",
                "id": 130,
                "target_project_id": 1
            },
            "project": {"id": 1}
        }
        
        # 第一次请求失败
        with patch.object(review_manager, 'process_merge_request', 
                         side_effect=Exception("Temporary failure")):
            response1 = self.client.post("/webhook", json=webhook_data)
            assert response1.status_code == 500
        
        # 第二次请求成功
        with patch.object(review_manager, 'process_merge_request', return_value=True):
            response2 = self.client.post("/webhook", json=webhook_data)
            assert response2.status_code == 200
            assert response2.json()["status"] == "success"
    
    def test_partial_data_handling(self):
        """测试部分数据处理"""
        # 测试各种不完整但仍可处理的数据
        partial_data_sets = [
            # 最小有效数据
            {
                "object_kind": "merge_request",
                "object_attributes": {
                    "action": "open",
                    "id": 131,
                    "target_project_id": 1
                }
            },
            # 缺少一些可选字段
            {
                "object_kind": "merge_request",
                "event_type": "merge_request",
                "object_attributes": {
                    "action": "update",
                    "id": 132,
                    "target_project_id": 1
                }
                # 缺少 project 字段
            }
        ]
        
        for i, partial_data in enumerate(partial_data_sets):
            with patch.object(review_manager, 'process_merge_request', return_value=True) as mock_process:
                response = self.client.post("/webhook", json=partial_data)
                
                # 应该能够处理或优雅地忽略
                assert response.status_code in [200, 400]
                
                if response.status_code == 200:
                    response_data = response.json()
                    assert response_data["status"] in ["success", "ignored"]
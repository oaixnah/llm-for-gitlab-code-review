#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 模块测试
"""

import time
from unittest.mock import Mock, patch, MagicMock

import pytest
from openai import OpenAI
from openai.types.chat import ChatCompletion

from llm import Service


class TestLLMService:
    """LLM 服务测试"""
    
    def test_init_success(self):
        """测试成功初始化"""
        with patch('llm.OpenAIClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            service = Service(
                model="gpt-4",
                api_url="https://api.openai.com/v1",
                api_key="sk-test",
                max_retries=3,
                timeout=30.0
            )
            
            assert service.model == "gpt-4"
            assert service.max_retries == 3
            assert service.timeout == 30.0
            assert service.client == mock_client
            
            # 验证客户端初始化参数
            mock_client_class.assert_called_once_with(
                api_key="sk-test",
                base_url="https://api.openai.com/v1",
                timeout=30.0
            )
    
    def test_init_with_defaults(self):
        """测试使用默认参数初始化"""
        with patch('llm.OpenAIClient') as mock_client_class:
            with patch('llm.settings') as mock_settings:
                mock_settings.llm_model = "gpt-3.5-turbo"
                mock_settings.llm_api_url = "https://test.api.com"
                mock_settings.llm_api_key = "test-key"
                
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                service = Service()
                
                assert service.model == "gpt-3.5-turbo"
                assert service.max_retries == 3
                assert service.timeout == 30.0
    
    def test_init_failure(self):
        """测试初始化失败"""
        with patch('llm.OpenAIClient') as mock_client_class:
            mock_client_class.side_effect = Exception("初始化失败")
            
            with pytest.raises(Exception, match="初始化失败"):
                Service()
    
    def test_check_success(self, mock_llm_client):
        """测试服务检查成功"""
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            service = Service(model="gpt-4")
            
            result = service.check()
            
            assert result is True
            mock_llm_client.models.retrieve.assert_called_once_with("gpt-4")
    
    def test_check_failure(self):
        """测试服务检查失败"""
        with patch('llm.OpenAIClient') as mock_client_class:
            mock_client = Mock()
            mock_client.models.retrieve.side_effect = Exception("模型不存在")
            mock_client_class.return_value = mock_client
            
            service = Service(model="invalid-model")
            
            result = service.check()
            
            assert result is False
    
    def test_chat_success(self, mock_llm_client):
        """测试成功的聊天请求"""
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            with patch('llm.parse_response') as mock_parse:
                mock_parse.return_value = {
                    'issues': ['测试问题'],
                    'suggestions': ['测试建议'],
                    'score': 8,
                    'duration': 2.5
                }
                
                service = Service()
                messages = [{"role": "user", "content": "请审查代码"}]
                
                result = service.chat(messages)
                
                assert result['issues'] == ['测试问题']
                assert result['score'] == 8
                assert 'duration' in result
                
                # 验证 API 调用参数
                mock_llm_client.chat.completions.create.assert_called_once()
                call_args = mock_llm_client.chat.completions.create.call_args[1]
                assert call_args['messages'] == messages
                assert call_args['max_tokens'] == 4096
                assert call_args['temperature'] == 0.7
    
    def test_chat_with_custom_params(self, mock_llm_client):
        """测试带自定义参数的聊天请求"""
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            with patch('llm.parse_response') as mock_parse:
                mock_parse.return_value = {'result': 'success', 'duration': 1.0}
                
                service = Service()
                messages = [{"role": "user", "content": "测试"}]
                
                result = service.chat(
                    messages,
                    temperature=0.5,
                    max_tokens=2048,
                    top_p=0.9
                )
                
                # 验证自定义参数被传递
                call_args = mock_llm_client.chat.completions.create.call_args[1]
                assert call_args['temperature'] == 0.5
                assert call_args['max_tokens'] == 2048
                assert call_args['top_p'] == 0.9
    
    def test_chat_empty_messages(self):
        """测试空消息列表"""
        with patch('llm.OpenAIClient'):
            service = Service()
            
            with pytest.raises(ValueError, match="消息列表不能为空"):
                service.chat([])
    
    def test_chat_empty_response(self, mock_llm_client):
        """测试空响应"""
        # 模拟空响应
        mock_response = Mock()
        mock_response.choices = []
        mock_llm_client.chat.completions.create.return_value = mock_response
        
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            service = Service()
            messages = [{"role": "user", "content": "测试"}]
            
            with pytest.raises(ValueError, match="LLM返回空响应"):
                service.chat(messages)
    
    def test_chat_empty_content(self, mock_llm_client):
        """测试空内容响应"""
        # 模拟空内容响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = None
        mock_llm_client.chat.completions.create.return_value = mock_response
        
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            service = Service()
            messages = [{"role": "user", "content": "测试"}]
            
            with pytest.raises(ValueError, match="LLM返回空响应"):
                service.chat(messages)
    
    def test_chat_retry_mechanism(self):
        """测试重试机制"""
        with patch('llm.OpenAIClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # 前两次调用失败，第三次成功
            mock_client.chat.completions.create.side_effect = [
                Exception("网络错误"),
                Exception("服务器错误"),
                Mock(choices=[Mock(message=Mock(content='{"result": "success"}'))], usage=Mock(total_tokens=100))
            ]
            
            with patch('llm.parse_response') as mock_parse:
                mock_parse.return_value = {'result': 'success', 'duration': 1.0}
                
                with patch('time.sleep'):  # 跳过实际等待
                    service = Service(max_retries=3)
                    messages = [{"role": "user", "content": "测试"}]
                    
                    result = service.chat(messages)
                    
                    assert result['result'] == 'success'
                    assert mock_client.chat.completions.create.call_count == 3
    
    def test_chat_retry_exhausted(self):
        """测试重试次数用尽"""
        with patch('llm.OpenAIClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # 所有调用都失败
            mock_client.chat.completions.create.side_effect = Exception("持续失败")
            
            with patch('time.sleep'):  # 跳过实际等待
                service = Service(max_retries=2)
                messages = [{"role": "user", "content": "测试"}]
                
                with pytest.raises(Exception, match="LLM请求失败，已重试2次"):
                    service.chat(messages)
                
                assert mock_client.chat.completions.create.call_count == 2
    
    def test_chat_exponential_backoff(self):
        """测试指数退避"""
        with patch('llm.OpenAIClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("失败")
            
            with patch('time.sleep') as mock_sleep:
                service = Service(max_retries=3)
                messages = [{"role": "user", "content": "测试"}]
                
                with pytest.raises(Exception):
                    service.chat(messages)
                
                # 验证指数退避：第一次等待1秒，第二次等待2秒
                expected_calls = [((1,),), ((2,),)]
                assert mock_sleep.call_args_list == expected_calls
    
    def test_chat_duration_tracking(self, mock_llm_client):
        """测试持续时间跟踪"""
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            with patch('llm.parse_response') as mock_parse:
                with patch('time.time') as mock_time:
                    # 模拟时间流逝
                    mock_time.side_effect = [1000.0, 1002.5]  # 开始时间和结束时间
                    
                    mock_parse.return_value = {'result': 'success'}
                    
                    service = Service()
                    messages = [{"role": "user", "content": "测试"}]
                    
                    service.chat(messages)
                    
                    # 验证 parse_response 被调用时传入了正确的持续时间
                    mock_parse.assert_called_once()
                    args = mock_parse.call_args[0]
                    duration = args[1]
                    assert duration == 2.5
    
    def test_chat_token_usage_logging(self, mock_llm_client, caplog):
        """测试 token 使用量日志记录"""
        # 设置响应包含 token 使用量
        mock_response = mock_llm_client.chat.completions.create.return_value
        mock_response.usage.total_tokens = 150
        
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            with patch('llm.parse_response') as mock_parse:
                mock_parse.return_value = {'result': 'success', 'duration': 1.0}
                
                service = Service()
                messages = [{"role": "user", "content": "测试"}]
                
                service.chat(messages)
                
                # 验证日志包含 token 信息
                assert "tokens: 150" in caplog.text
    
    def test_chat_no_token_usage(self, mock_llm_client, caplog):
        """测试没有 token 使用量信息的情况"""
        # 设置响应不包含 token 使用量
        mock_response = mock_llm_client.chat.completions.create.return_value
        mock_response.usage = None
        
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            with patch('llm.parse_response') as mock_parse:
                mock_parse.return_value = {'result': 'success', 'duration': 1.0}
                
                service = Service()
                messages = [{"role": "user", "content": "测试"}]
                
                service.chat(messages)
                
                # 验证日志包含 unknown token 信息
                assert "tokens: unknown" in caplog.text


class TestLLMServiceIntegration:
    """LLM 服务集成测试"""
    
    def test_complete_workflow(self, mock_llm_client):
        """测试完整工作流"""
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            with patch('llm.parse_response') as mock_parse:
                mock_parse.return_value = {
                    'issues': ['缺少错误处理'],
                    'suggestions': ['添加try-catch块'],
                    'score': 7,
                    'summary': '代码质量良好',
                    'approved': True,
                    'duration': 2.0
                }
                
                service = Service()
                
                # 1. 检查服务
                assert service.check() is True
                
                # 2. 进行聊天
                messages = [
                    {"role": "system", "content": "你是代码审查助手"},
                    {"role": "user", "content": "请审查这段代码"}
                ]
                
                result = service.chat(messages)
                
                # 3. 验证结果
                assert result['issues'] == ['缺少错误处理']
                assert result['suggestions'] == ['添加try-catch块']
                assert result['score'] == 7
                assert result['approved'] is True
                assert 'duration' in result
    
    def test_error_recovery(self):
        """测试错误恢复"""
        with patch('llm.OpenAIClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # 第一次检查失败，第二次成功
            mock_client.models.retrieve.side_effect = [
                Exception("网络错误"),
                Mock()  # 成功响应
            ]
            
            service = Service()
            
            # 第一次检查失败
            assert service.check() is False
            
            # 第二次检查成功
            assert service.check() is True
    
    def test_concurrent_requests_simulation(self, mock_llm_client):
        """测试并发请求模拟"""
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            with patch('llm.parse_response') as mock_parse:
                mock_parse.return_value = {'result': 'success', 'duration': 1.0}
                
                service = Service()
                messages = [{"role": "user", "content": "测试"}]
                
                # 模拟多个并发请求
                results = []
                for i in range(5):
                    result = service.chat(messages)
                    results.append(result)
                
                # 验证所有请求都成功
                assert len(results) == 5
                for result in results:
                    assert result['result'] == 'success'
                
                # 验证 API 被调用了5次
                assert mock_llm_client.chat.completions.create.call_count == 5
    
    def test_different_message_formats(self, mock_llm_client):
        """测试不同的消息格式"""
        with patch('llm.OpenAIClient', return_value=mock_llm_client):
            with patch('llm.parse_response') as mock_parse:
                mock_parse.return_value = {'result': 'success', 'duration': 1.0}
                
                service = Service()
                
                # 测试不同的消息格式
                test_cases = [
                    # 单条用户消息
                    [{"role": "user", "content": "简单测试"}],
                    
                    # 系统消息 + 用户消息
                    [
                        {"role": "system", "content": "你是助手"},
                        {"role": "user", "content": "请帮助我"}
                    ],
                    
                    # 完整对话
                    [
                        {"role": "system", "content": "你是代码审查助手"},
                        {"role": "user", "content": "请审查代码"},
                        {"role": "assistant", "content": "我来帮你审查"},
                        {"role": "user", "content": "这是新的代码"}
                    ]
                ]
                
                for messages in test_cases:
                    result = service.chat(messages)
                    assert result['result'] == 'success'
                
                # 验证所有格式都被正确处理
                assert mock_llm_client.chat.completions.create.call_count == len(test_cases)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReviewManager 模块测试
"""

from unittest.mock import patch, Mock, MagicMock, call
import json

import pytest
from gitlab.exceptions import GitlabError

from review_manager import ReviewManager
from models import Review, ReviewDiscussion, ReviewFileRecord


class TestReviewManagerInit:
    """ReviewManager 初始化测试"""
    
    def test_init_success(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试成功初始化"""
        manager = ReviewManager()
        
        assert manager.settings == mock_settings
        assert manager.gitlab_client == mock_gitlab_client
        assert manager.llm_service == mock_llm_service
    
    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化"""
        custom_settings = Mock()
        custom_gitlab = Mock()
        custom_llm = Mock()
        
        manager = ReviewManager(
            settings=custom_settings,
            gitlab_client=custom_gitlab,
            llm_service=custom_llm
        )
        
        assert manager.settings == custom_settings
        assert manager.gitlab_client == custom_gitlab
        assert manager.llm_service == custom_llm


class TestProcessMergeRequest:
    """处理合并请求测试"""
    
    def test_process_merge_request_success(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试成功处理合并请求"""
        # 设置模拟数据
        project_id = 1
        merge_request_id = 123
        
        # 模拟 GitLab 项目和 MR
        mock_project = Mock()
        mock_mr = Mock()
        mock_mr.changes.return_value = [
            {
                'old_path': 'src/main.py',
                'new_path': 'src/main.py',
                'diff': '@@ -1,3 +1,4 @@\n def hello():\n+    print("world")\n     pass'
            }
        ]
        
        mock_gitlab_client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        
        # 模拟 LLM 响应
        mock_llm_service.chat.return_value = {
            'content': json.dumps({
                'approved': True,
                'score': 8,
                'issue': ['小问题'],
                'suggestion': ['改进建议'],
                'summary': '代码质量良好'
            }),
            'usage': {'total_tokens': 100}
        }
        
        # 模拟数据库操作
        with patch('review_manager.update_or_create_review', return_value=1), \
             patch('review_manager.create_review_discussion', return_value=1), \
             patch('review_manager.create_review_file_record', return_value=1), \
             patch('review_manager.create_review_file_llm_message', return_value=1), \
             patch('review_manager.get_discussion_id', return_value=None):
            
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            result = manager.process_merge_request(project_id, merge_request_id)
            
            assert result is True
            
            # 验证 GitLab API 调用
            mock_gitlab_client.projects.get.assert_called_once_with(project_id)
            mock_project.mergerequests.get.assert_called_once_with(merge_request_id)
            
            # 验证 LLM 调用
            assert mock_llm_service.chat.called
    
    def test_process_merge_request_no_changes(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试处理没有变更的合并请求"""
        project_id = 1
        merge_request_id = 123
        
        # 模拟没有变更的 MR
        mock_project = Mock()
        mock_mr = Mock()
        mock_mr.changes.return_value = []
        
        mock_gitlab_client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        
        with patch('review_manager.update_or_create_review', return_value=1):
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            result = manager.process_merge_request(project_id, merge_request_id)
            
            assert result is True
            # 验证没有调用 LLM
            assert not mock_llm_service.chat.called
    
    def test_process_merge_request_gitlab_error(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试 GitLab API 错误"""
        project_id = 1
        merge_request_id = 123
        
        # 模拟 GitLab 错误
        mock_gitlab_client.projects.get.side_effect = GitlabError("项目不存在")
        
        manager = ReviewManager(
            settings=mock_settings,
            gitlab_client=mock_gitlab_client,
            llm_service=mock_llm_service
        )
        
        with pytest.raises(GitlabError, match="项目不存在"):
            manager.process_merge_request(project_id, merge_request_id)
    
    def test_process_merge_request_llm_error(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试 LLM 服务错误"""
        project_id = 1
        merge_request_id = 123
        
        # 设置正常的 GitLab 响应
        mock_project = Mock()
        mock_mr = Mock()
        mock_mr.changes.return_value = [
            {
                'old_path': 'test.py',
                'new_path': 'test.py',
                'diff': '@@ -1,1 +1,2 @@\n print("hello")\n+print("world")'
            }
        ]
        
        mock_gitlab_client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        
        # 模拟 LLM 错误
        mock_llm_service.chat.side_effect = Exception("LLM 服务不可用")
        
        with patch('review_manager.update_or_create_review', return_value=1), \
             patch('review_manager.create_review_discussion', return_value=1), \
             patch('review_manager.get_discussion_id', return_value=None):
            
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            with pytest.raises(Exception, match="LLM 服务不可用"):
                manager.process_merge_request(project_id, merge_request_id)
    
    def test_process_merge_request_invalid_llm_response(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试无效的 LLM 响应"""
        project_id = 1
        merge_request_id = 123
        
        # 设置正常的 GitLab 响应
        mock_project = Mock()
        mock_mr = Mock()
        mock_mr.changes.return_value = [
            {
                'old_path': 'test.py',
                'new_path': 'test.py',
                'diff': '@@ -1,1 +1,2 @@\n print("hello")\n+print("world")'
            }
        ]
        
        mock_gitlab_client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        
        # 模拟无效的 LLM 响应
        mock_llm_service.chat.return_value = {
            'content': 'invalid json',
            'usage': {'total_tokens': 50}
        }
        
        with patch('review_manager.update_or_create_review', return_value=1), \
             patch('review_manager.create_review_discussion', return_value=1), \
             patch('review_manager.get_discussion_id', return_value=None), \
             patch('review_manager.create_review_file_llm_message', return_value=1):
            
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            # 应该处理 JSON 解析错误但不抛出异常
            result = manager.process_merge_request(project_id, merge_request_id)
            
            # 即使 LLM 响应无效，也应该返回 True（已记录错误）
            assert result is True


class TestProcessFileChange:
    """处理文件变更测试"""
    
    def test_process_file_change_new_discussion(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试处理新文件变更（创建新讨论）"""
        project_id = 1
        merge_request_id = 123
        file_change = {
            'old_path': 'src/main.py',
            'new_path': 'src/main.py',
            'diff': '@@ -1,3 +1,4 @@\n def hello():\n+    print("world")\n     pass'
        }
        
        # 模拟 LLM 响应
        mock_llm_service.chat.return_value = {
            'content': json.dumps({
                'approved': True,
                'score': 9,
                'issue': [],
                'suggestion': ['很好的改进'],
                'summary': '代码改进合理'
            }),
            'usage': {'total_tokens': 80}
        }
        
        with patch('review_manager.get_discussion_id', return_value=None), \
             patch('review_manager.create_review_discussion', return_value=1) as mock_create_discussion, \
             patch('review_manager.create_review_file_record', return_value=1) as mock_create_record, \
             patch('review_manager.create_review_file_llm_message', return_value=1) as mock_create_message:
            
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            result = manager._process_file_change(project_id, merge_request_id, file_change)
            
            assert result is True
            
            # 验证创建了新讨论
            mock_create_discussion.assert_called_once()
            mock_create_record.assert_called_once()
            assert mock_create_message.call_count == 2  # user + assistant 消息
    
    def test_process_file_change_existing_discussion(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试处理已存在讨论的文件变更"""
        project_id = 1
        merge_request_id = 123
        file_change = {
            'old_path': 'src/main.py',
            'new_path': 'src/main.py',
            'diff': '@@ -1,3 +1,4 @@\n def hello():\n+    print("world")\n     pass'
        }
        
        # 模拟 LLM 响应
        mock_llm_service.chat.return_value = {
            'content': json.dumps({
                'approved': False,
                'score': 6,
                'issue': ['需要改进'],
                'suggestion': ['添加注释'],
                'summary': '需要小幅改进'
            }),
            'usage': {'total_tokens': 90}
        }
        
        with patch('review_manager.get_discussion_id', return_value='existing_discussion_123'), \
             patch('review_manager.create_review_discussion') as mock_create_discussion, \
             patch('review_manager.create_review_file_record', return_value=1) as mock_create_record, \
             patch('review_manager.create_review_file_llm_message', return_value=1) as mock_create_message:
            
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            result = manager._process_file_change(project_id, merge_request_id, file_change)
            
            assert result is True
            
            # 验证没有创建新讨论
            mock_create_discussion.assert_not_called()
            mock_create_record.assert_called_once()
            assert mock_create_message.call_count == 2
    
    def test_process_file_change_unsupported_file(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试处理不支持的文件类型"""
        project_id = 1
        merge_request_id = 123
        file_change = {
            'old_path': 'image.png',
            'new_path': 'image.png',
            'diff': 'Binary files differ'
        }
        
        with patch('review_manager.is_supported_file', return_value=False):
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            result = manager._process_file_change(project_id, merge_request_id, file_change)
            
            assert result is True
            # 验证没有调用 LLM
            assert not mock_llm_service.chat.called
    
    def test_process_file_change_empty_diff(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试处理空的 diff"""
        project_id = 1
        merge_request_id = 123
        file_change = {
            'old_path': 'src/main.py',
            'new_path': 'src/main.py',
            'diff': ''
        }
        
        with patch('review_manager.is_supported_file', return_value=True):
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            result = manager._process_file_change(project_id, merge_request_id, file_change)
            
            assert result is True
            # 验证没有调用 LLM（因为没有实际变更）
            assert not mock_llm_service.chat.called


class TestGenerateDiscussionId:
    """生成讨论ID测试"""
    
    def test_generate_discussion_id_consistent(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试生成的讨论ID一致性"""
        manager = ReviewManager(
            settings=mock_settings,
            gitlab_client=mock_gitlab_client,
            llm_service=mock_llm_service
        )
        
        # 相同输入应该生成相同的ID
        id1 = manager._generate_discussion_id(1, 123, 'src/main.py')
        id2 = manager._generate_discussion_id(1, 123, 'src/main.py')
        
        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) > 0
    
    def test_generate_discussion_id_different_inputs(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试不同输入生成不同的ID"""
        manager = ReviewManager(
            settings=mock_settings,
            gitlab_client=mock_gitlab_client,
            llm_service=mock_llm_service
        )
        
        # 不同输入应该生成不同的ID
        id1 = manager._generate_discussion_id(1, 123, 'src/main.py')
        id2 = manager._generate_discussion_id(1, 124, 'src/main.py')
        id3 = manager._generate_discussion_id(2, 123, 'src/main.py')
        id4 = manager._generate_discussion_id(1, 123, 'src/utils.py')
        
        assert id1 != id2
        assert id1 != id3
        assert id1 != id4
        assert id2 != id3
        assert id2 != id4
        assert id3 != id4


class TestReviewManagerIntegration:
    """ReviewManager 集成测试"""
    
    def test_complete_review_workflow(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试完整的代码审查工作流"""
        project_id = 1
        merge_request_id = 123
        
        # 设置复杂的 GitLab 响应
        mock_project = Mock()
        mock_mr = Mock()
        mock_mr.changes.return_value = [
            {
                'old_path': 'src/main.py',
                'new_path': 'src/main.py',
                'diff': '@@ -1,5 +1,8 @@\n def main():\n+    # 新增注释\n     print("Hello")\n+    print("World")\n     return 0'
            },
            {
                'old_path': 'src/utils.py',
                'new_path': 'src/utils.py',
                'diff': '@@ -10,3 +10,6 @@\n def helper():\n     pass\n+\n+def new_function():\n+    return True'
            }
        ]
        
        mock_gitlab_client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        
        # 设置 LLM 响应（为每个文件返回不同的结果）
        llm_responses = [
            {
                'content': json.dumps({
                    'approved': True,
                    'score': 8,
                    'issue': ['注释可以更详细'],
                    'suggestion': ['添加函数文档'],
                    'summary': 'main.py 改进良好'
                }),
                'usage': {'total_tokens': 120}
            },
            {
                'content': json.dumps({
                    'approved': False,
                    'score': 6,
                    'issue': ['新函数缺少文档', '函数名不够描述性'],
                    'suggestion': ['添加函数文档', '重命名函数'],
                    'summary': 'utils.py 需要改进'
                }),
                'usage': {'total_tokens': 150}
            }
        ]
        
        mock_llm_service.chat.side_effect = llm_responses
        
        # 模拟数据库操作
        with patch('review_manager.update_or_create_review', return_value=1), \
             patch('review_manager.create_review_discussion', side_effect=[1, 2]), \
             patch('review_manager.create_review_file_record', side_effect=[1, 2]), \
             patch('review_manager.create_review_file_llm_message', side_effect=[1, 2, 3, 4]), \
             patch('review_manager.get_discussion_id', return_value=None), \
             patch('review_manager.is_supported_file', return_value=True):
            
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            result = manager.process_merge_request(project_id, merge_request_id)
            
            assert result is True
            
            # 验证 LLM 被调用了两次（每个文件一次）
            assert mock_llm_service.chat.call_count == 2
            
            # 验证 GitLab API 调用
            mock_gitlab_client.projects.get.assert_called_once_with(project_id)
            mock_project.mergerequests.get.assert_called_once_with(merge_request_id)
    
    def test_partial_failure_handling(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试部分失败的处理"""
        project_id = 1
        merge_request_id = 123
        
        # 设置 GitLab 响应
        mock_project = Mock()
        mock_mr = Mock()
        mock_mr.changes.return_value = [
            {
                'old_path': 'src/main.py',
                'new_path': 'src/main.py',
                'diff': '@@ -1,1 +1,2 @@\n print("hello")\n+print("world")'
            },
            {
                'old_path': 'src/utils.py',
                'new_path': 'src/utils.py',
                'diff': '@@ -1,1 +1,2 @@\n def test():\n+    pass'
            }
        ]
        
        mock_gitlab_client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        
        # 第一个文件成功，第二个文件失败
        llm_responses = [
            {
                'content': json.dumps({
                    'approved': True,
                    'score': 8,
                    'issue': [],
                    'suggestion': [],
                    'summary': '良好'
                }),
                'usage': {'total_tokens': 100}
            }
        ]
        
        # 第二次调用抛出异常
        mock_llm_service.chat.side_effect = llm_responses + [Exception("LLM 错误")]
        
        with patch('review_manager.update_or_create_review', return_value=1), \
             patch('review_manager.create_review_discussion', side_effect=[1, 2]), \
             patch('review_manager.create_review_file_record', return_value=1), \
             patch('review_manager.create_review_file_llm_message', return_value=1), \
             patch('review_manager.get_discussion_id', return_value=None), \
             patch('review_manager.is_supported_file', return_value=True):
            
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            # 应该处理部分失败但不完全崩溃
            with pytest.raises(Exception, match="LLM 错误"):
                manager.process_merge_request(project_id, merge_request_id)
    
    def test_concurrent_processing_simulation(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试并发处理模拟"""
        # 这个测试模拟多个 ReviewManager 实例同时处理不同的 MR
        project_id = 1
        
        # 创建多个管理器实例
        managers = [
            ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            for _ in range(3)
        ]
        
        # 为每个管理器设置不同的 MR 数据
        mr_ids = [123, 124, 125]
        
        for i, (manager, mr_id) in enumerate(zip(managers, mr_ids)):
            # 设置独立的模拟响应
            mock_project = Mock()
            mock_mr = Mock()
            mock_mr.changes.return_value = [
                {
                    'old_path': f'src/file_{i}.py',
                    'new_path': f'src/file_{i}.py',
                    'diff': f'@@ -1,1 +1,2 @@\n print("file_{i}")\n+print("updated")'
                }
            ]
            
            # 每个管理器应该生成不同的讨论ID
            discussion_id_1 = manager._generate_discussion_id(project_id, mr_id, f'src/file_{i}.py')
            discussion_id_2 = managers[0]._generate_discussion_id(project_id, mr_ids[0], 'src/file_0.py')
            
            if i > 0:
                assert discussion_id_1 != discussion_id_2


class TestErrorHandling:
    """错误处理测试"""
    
    def test_database_connection_error(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试数据库连接错误"""
        project_id = 1
        merge_request_id = 123
        
        # 设置正常的 GitLab 响应
        mock_project = Mock()
        mock_mr = Mock()
        mock_mr.changes.return_value = []
        
        mock_gitlab_client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        
        # 模拟数据库错误
        with patch('review_manager.update_or_create_review', side_effect=Exception("数据库连接失败")):
            manager = ReviewManager(
                settings=mock_settings,
                gitlab_client=mock_gitlab_client,
                llm_service=mock_llm_service
            )
            
            with pytest.raises(Exception, match="数据库连接失败"):
                manager.process_merge_request(project_id, merge_request_id)
    
    def test_network_timeout_simulation(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试网络超时模拟"""
        project_id = 1
        merge_request_id = 123
        
        # 模拟网络超时
        mock_gitlab_client.projects.get.side_effect = Exception("网络超时")
        
        manager = ReviewManager(
            settings=mock_settings,
            gitlab_client=mock_gitlab_client,
            llm_service=mock_llm_service
        )
        
        with pytest.raises(Exception, match="网络超时"):
            manager.process_merge_request(project_id, merge_request_id)
    
    def test_invalid_project_or_mr(self, mock_settings, mock_gitlab_client, mock_llm_service):
        """测试无效的项目或MR ID"""
        project_id = 999
        merge_request_id = 999
        
        # 模拟项目不存在
        mock_gitlab_client.projects.get.side_effect = GitlabError("404: Project not found")
        
        manager = ReviewManager(
            settings=mock_settings,
            gitlab_client=mock_gitlab_client,
            llm_service=mock_llm_service
        )
        
        with pytest.raises(GitlabError, match="404: Project not found"):
            manager.process_merge_request(project_id, merge_request_id)
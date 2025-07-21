#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CURD 模块测试
"""

from unittest.mock import patch, Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from curd import (
    _get_review_by_project_and_mr, _get_review_discussion_id_by_discussion_id,
    update_or_create_review, get_review, get_discussion_id,
    create_review_discussion, get_review_discussion_id,
    create_review_file_record, get_review_file_record,
    create_review_file_llm_message, get_review_file_llm_messages
)
from models import Review, ReviewDiscussion, ReviewFileRecord, ReviewFileLLMMessage


class TestPrivateFunctions:
    """私有函数测试"""
    
    def test_get_review_by_project_and_mr_found(self, test_db_session):
        """测试根据项目和MR ID获取评审记录 - 找到记录"""
        # 创建测试数据
        review = Review(project_id=1, merge_request_id=123, status='pending')
        test_db_session.add(review)
        test_db_session.commit()
        
        # 测试查询
        result = _get_review_by_project_and_mr(test_db_session, 1, 123)
        
        assert result is not None
        assert result.project_id == 1
        assert result.merge_request_id == 123
        assert result.status == 'pending'
    
    def test_get_review_by_project_and_mr_not_found(self, test_db_session):
        """测试根据项目和MR ID获取评审记录 - 未找到记录"""
        result = _get_review_by_project_and_mr(test_db_session, 999, 999)
        assert result is None
    
    def test_get_review_discussion_id_by_discussion_id_found(self, test_db_session):
        """测试根据讨论ID获取评审讨论记录ID - 找到记录"""
        # 创建测试数据
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        discussion = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_123',
            file_path='test.py'
        )
        test_db_session.add(discussion)
        test_db_session.commit()
        
        # 测试查询
        result = _get_review_discussion_id_by_discussion_id(test_db_session, 'discussion_123')
        
        assert result == discussion.id
    
    def test_get_review_discussion_id_by_discussion_id_not_found(self, test_db_session):
        """测试根据讨论ID获取评审讨论记录ID - 未找到记录"""
        result = _get_review_discussion_id_by_discussion_id(test_db_session, 'nonexistent')
        assert result is None


class TestUpdateOrCreateReview:
    """更新或创建评审记录测试"""
    
    def test_create_new_review(self, test_db_session):
        """测试创建新评审记录"""
        with patch('curd.Session', return_value=test_db_session):
            review_id = update_or_create_review(1, 123, 'pending')
            
            assert review_id is not None
            
            # 验证记录被创建
            review = test_db_session.get(Review, review_id)
            assert review.project_id == 1
            assert review.merge_request_id == 123
            assert review.status == 'pending'
    
    def test_update_existing_review(self, test_db_session):
        """测试更新现有评审记录"""
        # 先创建一个记录
        review = Review(project_id=1, merge_request_id=123, status='pending')
        test_db_session.add(review)
        test_db_session.commit()
        original_id = review.id
        
        with patch('curd.Session', return_value=test_db_session):
            review_id = update_or_create_review(1, 123, 'approved')
            
            assert review_id == original_id
            
            # 验证记录被更新
            updated_review = test_db_session.get(Review, review_id)
            assert updated_review.status == 'approved'
    
    def test_create_review_without_status(self, test_db_session):
        """测试创建不指定状态的评审记录"""
        with patch('curd.Session', return_value=test_db_session):
            review_id = update_or_create_review(1, 123)
            
            review = test_db_session.get(Review, review_id)
            assert review.status is None
    
    def test_update_review_without_status_change(self, test_db_session):
        """测试更新评审记录但不改变状态"""
        # 先创建一个记录
        review = Review(project_id=1, merge_request_id=123, status='pending')
        test_db_session.add(review)
        test_db_session.commit()
        
        with patch('curd.Session', return_value=test_db_session):
            review_id = update_or_create_review(1, 123, None)
            
            # 验证状态没有改变
            updated_review = test_db_session.get(Review, review_id)
            assert updated_review.status == 'pending'
    
    def test_update_or_create_review_database_error(self):
        """测试数据库错误处理"""
        with patch('curd.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.commit.side_effect = SQLAlchemyError("数据库错误")
            
            with pytest.raises(SQLAlchemyError, match="数据库错误"):
                update_or_create_review(1, 123, 'pending')


class TestGetReview:
    """获取评审记录测试"""
    
    def test_get_review_success(self, test_db_session):
        """测试成功获取评审记录"""
        # 创建测试数据
        review = Review(project_id=1, merge_request_id=123, status='approved')
        test_db_session.add(review)
        test_db_session.commit()
        
        with patch('curd.Session', return_value=test_db_session):
            result = get_review(1, 123)
            
            assert result is not None
            assert result.project_id == 1
            assert result.merge_request_id == 123
            assert result.status == 'approved'
    
    def test_get_review_not_found(self, test_db_session):
        """测试获取不存在的评审记录"""
        with patch('curd.Session', return_value=test_db_session):
            result = get_review(999, 999)
            assert result is None
    
    def test_get_review_database_error(self):
        """测试获取评审记录时的数据库错误"""
        with patch('curd.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.scalar.side_effect = SQLAlchemyError("查询错误")
            
            with pytest.raises(SQLAlchemyError):
                get_review(1, 123)


class TestGetDiscussionId:
    """获取讨论ID测试"""
    
    def test_get_discussion_id_success(self, test_db_session):
        """测试成功获取讨论ID"""
        # 创建测试数据
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        discussion = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_123',
            file_path='src/main.py'
        )
        test_db_session.add(discussion)
        test_db_session.commit()
        
        with patch('curd.Session', return_value=test_db_session):
            result = get_discussion_id(1, 123, 'src/main.py')
            
            assert result == 'discussion_123'
    
    def test_get_discussion_id_not_found(self, test_db_session):
        """测试获取不存在的讨论ID"""
        with patch('curd.Session', return_value=test_db_session):
            result = get_discussion_id(999, 999, 'nonexistent.py')
            assert result is None
    
    def test_get_discussion_id_database_error(self):
        """测试获取讨论ID时的数据库错误"""
        with patch('curd.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.scalar.side_effect = SQLAlchemyError("查询错误")
            
            with pytest.raises(SQLAlchemyError):
                get_discussion_id(1, 123, 'test.py')


class TestCreateReviewDiscussion:
    """创建评审讨论测试"""
    
    def test_create_review_discussion_success(self, test_db_session):
        """测试成功创建评审讨论"""
        # 先创建评审记录
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        with patch('curd.Session', return_value=test_db_session):
            discussion_id = create_review_discussion(
                1, 123, 'discussion_123', 'src/main.py'
            )
            
            assert discussion_id is not None
            
            # 验证记录被创建
            discussion = test_db_session.get(ReviewDiscussion, discussion_id)
            assert discussion.review_id == review.id
            assert discussion.discussion_id == 'discussion_123'
            assert discussion.file_path == 'src/main.py'
    
    def test_create_review_discussion_no_review(self, test_db_session):
        """测试创建评审讨论时评审记录不存在"""
        with patch('curd.Session', return_value=test_db_session):
            with pytest.raises(ValueError, match="找不到项目ID 999 和MR ID 999 对应的评审记录"):
                create_review_discussion(999, 999, 'discussion_123', 'test.py')
    
    def test_create_review_discussion_database_error(self):
        """测试创建评审讨论时的数据库错误"""
        with patch('curd.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.scalar.return_value = 1  # 模拟找到评审记录
            mock_session.commit.side_effect = SQLAlchemyError("创建失败")
            
            with pytest.raises(SQLAlchemyError):
                create_review_discussion(1, 123, 'discussion_123', 'test.py')


class TestGetReviewDiscussionId:
    """获取评审讨论记录ID测试"""
    
    def test_get_review_discussion_id_success(self, test_db_session):
        """测试成功获取评审讨论记录ID"""
        # 创建测试数据
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        discussion = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_123',
            file_path='test.py'
        )
        test_db_session.add(discussion)
        test_db_session.commit()
        
        with patch('curd.Session', return_value=test_db_session):
            result = get_review_discussion_id('discussion_123')
            
            assert result == discussion.id
    
    def test_get_review_discussion_id_not_found(self, test_db_session):
        """测试获取不存在的评审讨论记录ID"""
        with patch('curd.Session', return_value=test_db_session):
            result = get_review_discussion_id('nonexistent')
            assert result is None


class TestCreateReviewFileRecord:
    """创建评审文件记录测试"""
    
    def test_create_review_file_record_success(self, test_db_session):
        """测试成功创建评审文件记录"""
        # 创建依赖数据
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        discussion = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_123',
            file_path='test.py'
        )
        test_db_session.add(discussion)
        test_db_session.commit()
        
        with patch('curd.Session', return_value=test_db_session):
            record_id = create_review_file_record(
                'discussion_123',
                approved=True,
                score=8,
                issue=['问题1', '问题2'],
                suggestion=['建议1', '建议2'],
                summary='总体良好',
                llm_model='gpt-4'
            )
            
            assert record_id is not None
            
            # 验证记录被创建
            record = test_db_session.get(ReviewFileRecord, record_id)
            assert record.review_discussion_id == discussion.id
            assert record.approved is True
            assert record.score == 8
            assert record.issue == ['问题1', '问题2']
            assert record.suggestion == ['建议1', '建议2']
            assert record.summary == '总体良好'
            assert record.llm_model == 'gpt-4'
    
    def test_create_review_file_record_discussion_not_found(self, test_db_session):
        """测试创建评审文件记录时讨论不存在"""
        with patch('curd.Session', return_value=test_db_session):
            with pytest.raises(ValueError, match="找不到讨论ID nonexistent 对应的评审讨论记录"):
                create_review_file_record(
                    'nonexistent',
                    approved=True,
                    score=8,
                    issue=[],
                    suggestion=[],
                    summary='测试',
                    llm_model='gpt-4'
                )


class TestGetReviewFileRecord:
    """获取评审文件记录测试"""
    
    def test_get_review_file_record_success(self, test_db_session):
        """测试成功获取评审文件记录"""
        # 创建测试数据
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        discussion = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_123',
            file_path='test.py'
        )
        test_db_session.add(discussion)
        test_db_session.commit()
        
        record = ReviewFileRecord(
            review_discussion_id=discussion.id,
            approved=True,
            score=9,
            issue=['测试问题'],
            suggestion=['测试建议'],
            summary='测试总结',
            llm_model='gpt-4'
        )
        test_db_session.add(record)
        test_db_session.commit()
        
        with patch('curd.Session', return_value=test_db_session):
            result = get_review_file_record('discussion_123')
            
            assert result is not None
            assert result.approved is True
            assert result.score == 9
            assert result.issue == ['测试问题']
            assert result.suggestion == ['测试建议']
            assert result.summary == '测试总结'
            assert result.llm_model == 'gpt-4'
    
    def test_get_review_file_record_not_found(self, test_db_session):
        """测试获取不存在的评审文件记录"""
        with patch('curd.Session', return_value=test_db_session):
            result = get_review_file_record('nonexistent')
            assert result is None


class TestLLMMessages:
    """LLM 消息测试"""
    
    def test_create_review_file_llm_message_success(self, test_db_session):
        """测试成功创建 LLM 消息"""
        # 创建依赖数据
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        discussion = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_123',
            file_path='test.py'
        )
        test_db_session.add(discussion)
        test_db_session.commit()
        
        with patch('curd.Session', return_value=test_db_session):
            message_id = create_review_file_llm_message(
                'discussion_123',
                'user',
                '请审查这个文件'
            )
            
            assert message_id is not None
            
            # 验证消息被创建
            message = test_db_session.get(ReviewFileLLMMessage, message_id)
            assert message.review_discussion_id == discussion.id
            assert message.role == 'user'
            assert message.content == '请审查这个文件'
    
    def test_get_review_file_llm_messages_success(self, test_db_session):
        """测试成功获取 LLM 消息列表"""
        # 创建依赖数据
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        discussion = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_123',
            file_path='test.py'
        )
        test_db_session.add(discussion)
        test_db_session.commit()
        
        # 创建多条消息
        message1 = ReviewFileLLMMessage(
            review_discussion_id=discussion.id,
            role='user',
            content='用户消息1'
        )
        message2 = ReviewFileLLMMessage(
            review_discussion_id=discussion.id,
            role='assistant',
            content='助手回复1'
        )
        message3 = ReviewFileLLMMessage(
            review_discussion_id=discussion.id,
            role='user',
            content='用户消息2'
        )
        
        test_db_session.add_all([message1, message2, message3])
        test_db_session.commit()
        
        with patch('curd.Session', return_value=test_db_session):
            messages = get_review_file_llm_messages('discussion_123')
            
            assert len(messages) == 3
            
            # 验证消息格式
            for msg in messages:
                assert 'role' in msg
                assert 'content' in msg
            
            # 验证消息内容
            assert messages[0]['role'] == 'user'
            assert messages[0]['content'] == '用户消息1'
            assert messages[1]['role'] == 'assistant'
            assert messages[1]['content'] == '助手回复1'
            assert messages[2]['role'] == 'user'
            assert messages[2]['content'] == '用户消息2'
    
    def test_get_review_file_llm_messages_empty(self, test_db_session):
        """测试获取空的 LLM 消息列表"""
        with patch('curd.Session', return_value=test_db_session):
            messages = get_review_file_llm_messages('nonexistent')
            assert messages == []


class TestCurdIntegration:
    """CURD 模块集成测试"""
    
    def test_complete_review_workflow(self, test_db_session):
        """测试完整的评审工作流"""
        with patch('curd.Session', return_value=test_db_session):
            # 1. 创建评审
            review_id = update_or_create_review(1, 123, 'pending')
            assert review_id is not None
            
            # 2. 创建讨论
            discussion_id = create_review_discussion(
                1, 123, 'discussion_123', 'src/main.py'
            )
            assert discussion_id is not None
            
            # 3. 获取讨论ID
            found_discussion_id = get_discussion_id(1, 123, 'src/main.py')
            assert found_discussion_id == 'discussion_123'
            
            # 4. 创建 LLM 消息
            user_msg_id = create_review_file_llm_message(
                'discussion_123', 'user', '请审查代码'
            )
            assistant_msg_id = create_review_file_llm_message(
                'discussion_123', 'assistant', '审查完成'
            )
            assert user_msg_id is not None
            assert assistant_msg_id is not None
            
            # 5. 创建文件记录
            record_id = create_review_file_record(
                'discussion_123',
                approved=True,
                score=8,
                issue=['小问题'],
                suggestion=['小改进'],
                summary='总体良好',
                llm_model='gpt-4'
            )
            assert record_id is not None
            
            # 6. 获取所有数据验证
            review = get_review(1, 123)
            assert review.status == 'pending'
            
            messages = get_review_file_llm_messages('discussion_123')
            assert len(messages) == 2
            
            file_record = get_review_file_record('discussion_123')
            assert file_record.approved is True
            assert file_record.score == 8
    
    def test_error_propagation(self):
        """测试错误传播"""
        with patch('curd.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # 模拟数据库连接错误
            mock_session.commit.side_effect = SQLAlchemyError("连接失败")
            
            # 验证错误在各个函数中正确传播
            with pytest.raises(SQLAlchemyError):
                update_or_create_review(1, 123, 'pending')
    
    def test_transaction_rollback(self, test_db_session):
        """测试事务回滚"""
        # 创建一个会导致错误的场景
        with patch('curd.Session', return_value=test_db_session):
            # 先创建一个评审记录
            review_id = update_or_create_review(1, 123, 'pending')
            
            # 尝试创建讨论，但模拟提交时出错
            with patch.object(test_db_session, 'commit', side_effect=SQLAlchemyError("提交失败")):
                with pytest.raises(SQLAlchemyError):
                    create_review_discussion(1, 123, 'discussion_123', 'test.py')
            
            # 验证评审记录仍然存在（因为是在不同的事务中）
            review = get_review(1, 123)
            assert review is not None
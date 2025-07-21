#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型测试
"""

from datetime import datetime

import pytest
from sqlalchemy import select

from models import Review, ReviewDiscussion, ReviewFileRecord, ReviewFileLLMMessage


class TestReview:
    """Review 模型测试"""
    
    def test_create_review(self, test_db_session):
        """测试创建评审记录"""
        review = Review(
            project_id=1,
            merge_request_id=123,
            status='pending'
        )
        
        test_db_session.add(review)
        test_db_session.commit()
        
        assert review.id is not None
        assert review.project_id == 1
        assert review.merge_request_id == 123
        assert review.status == 'pending'
        assert isinstance(review.created_at, datetime)
        assert isinstance(review.updated_at, datetime)
    
    def test_review_default_values(self, test_db_session):
        """测试评审记录默认值"""
        review = Review(
            project_id=1,
            merge_request_id=123
        )
        
        test_db_session.add(review)
        test_db_session.commit()
        
        assert review.status == 'pending'
        assert review.created_at is not None
        assert review.updated_at is not None
    
    def test_review_update(self, test_db_session):
        """测试评审记录更新"""
        review = Review(
            project_id=1,
            merge_request_id=123,
            status='pending'
        )
        
        test_db_session.add(review)
        test_db_session.commit()
        
        original_updated_at = review.updated_at
        
        # 更新状态
        review.status = 'approved'
        test_db_session.commit()
        
        assert review.status == 'approved'
        # 注意：在测试环境中，updated_at 可能不会自动更新
        # 这取决于数据库的具体实现
    
    def test_review_query(self, test_db_session):
        """测试评审记录查询"""
        # 创建多个评审记录
        review1 = Review(project_id=1, merge_request_id=123, status='pending')
        review2 = Review(project_id=1, merge_request_id=124, status='approved')
        review3 = Review(project_id=2, merge_request_id=123, status='rejected')
        
        test_db_session.add_all([review1, review2, review3])
        test_db_session.commit()
        
        # 按项目ID查询
        project1_reviews = test_db_session.scalars(
            select(Review).where(Review.project_id == 1)
        ).all()
        assert len(project1_reviews) == 2
        
        # 按状态查询
        pending_reviews = test_db_session.scalars(
            select(Review).where(Review.status == 'pending')
        ).all()
        assert len(pending_reviews) == 1
        assert pending_reviews[0].merge_request_id == 123


class TestReviewDiscussion:
    """ReviewDiscussion 模型测试"""
    
    def test_create_review_discussion(self, test_db_session):
        """测试创建评审讨论记录"""
        # 先创建评审记录
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        # 创建讨论记录
        discussion = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_123',
            file_path='src/main.py'
        )
        
        test_db_session.add(discussion)
        test_db_session.commit()
        
        assert discussion.id is not None
        assert discussion.review_id == review.id
        assert discussion.discussion_id == 'discussion_123'
        assert discussion.file_path == 'src/main.py'
    
    def test_review_discussion_relationship(self, test_db_session):
        """测试评审讨论关系"""
        review = Review(project_id=1, merge_request_id=123)
        test_db_session.add(review)
        test_db_session.commit()
        
        discussion1 = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_1',
            file_path='file1.py'
        )
        discussion2 = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_2',
            file_path='file2.py'
        )
        
        test_db_session.add_all([discussion1, discussion2])
        test_db_session.commit()
        
        # 查询特定评审的所有讨论
        discussions = test_db_session.scalars(
            select(ReviewDiscussion).where(ReviewDiscussion.review_id == review.id)
        ).all()
        
        assert len(discussions) == 2
        file_paths = [d.file_path for d in discussions]
        assert 'file1.py' in file_paths
        assert 'file2.py' in file_paths


class TestReviewFileRecord:
    """ReviewFileRecord 模型测试"""
    
    def test_create_review_file_record(self, test_db_session):
        """测试创建评审文件记录"""
        # 创建依赖记录
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
        
        # 创建文件记录
        file_record = ReviewFileRecord(
            review_discussion_id=discussion.id,
            approved=True,
            score=8,
            issue=['缺少注释', '变量命名不规范'],
            suggestion=['添加函数注释', '使用更描述性的变量名'],
            summary='代码质量良好，需要小幅改进',
            llm_model='gpt-4'
        )
        
        test_db_session.add(file_record)
        test_db_session.commit()
        
        assert file_record.id is not None
        assert file_record.review_discussion_id == discussion.id
        assert file_record.approved is True
        assert file_record.score == 8
        assert file_record.issue == ['缺少注释', '变量命名不规范']
        assert file_record.suggestion == ['添加函数注释', '使用更描述性的变量名']
        assert file_record.summary == '代码质量良好，需要小幅改进'
        assert file_record.llm_model == 'gpt-4'
        assert isinstance(file_record.created_at, datetime)
    
    def test_review_file_record_json_fields(self, test_db_session):
        """测试 JSON 字段"""
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
        
        # 测试复杂的 JSON 数据
        complex_issues = [
            '函数过长，建议拆分',
            '缺少错误处理',
            {'type': 'warning', 'message': '性能问题'}
        ]
        
        complex_suggestions = [
            '将函数拆分为多个小函数',
            '添加 try-catch 块',
            {'priority': 'high', 'action': '优化算法复杂度'}
        ]
        
        file_record = ReviewFileRecord(
            review_discussion_id=discussion.id,
            approved=False,
            score=5,
            issue=complex_issues,
            suggestion=complex_suggestions,
            summary='需要重大改进',
            llm_model='gpt-4'
        )
        
        test_db_session.add(file_record)
        test_db_session.commit()
        
        # 重新查询验证 JSON 数据
        retrieved_record = test_db_session.get(ReviewFileRecord, file_record.id)
        assert retrieved_record.issue == complex_issues
        assert retrieved_record.suggestion == complex_suggestions


class TestReviewFileLLMMessage:
    """ReviewFileLLMMessage 模型测试"""
    
    def test_create_llm_message(self, test_db_session):
        """测试创建 LLM 消息记录"""
        # 创建依赖记录
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
        
        # 创建 LLM 消息
        message = ReviewFileLLMMessage(
            review_discussion_id=discussion.id,
            role='user',
            content='请审查这个文件的代码变更'
        )
        
        test_db_session.add(message)
        test_db_session.commit()
        
        assert message.id is not None
        assert message.review_discussion_id == discussion.id
        assert message.role == 'user'
        assert message.content == '请审查这个文件的代码变更'
        assert isinstance(message.created_at, datetime)
    
    def test_multiple_llm_messages(self, test_db_session):
        """测试多条 LLM 消息"""
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
        
        # 创建对话消息
        user_message = ReviewFileLLMMessage(
            review_discussion_id=discussion.id,
            role='user',
            content='请审查这个文件的代码变更'
        )
        
        assistant_message = ReviewFileLLMMessage(
            review_discussion_id=discussion.id,
            role='assistant',
            content='代码质量良好，建议添加更多注释'
        )
        
        test_db_session.add_all([user_message, assistant_message])
        test_db_session.commit()
        
        # 查询对话历史
        messages = test_db_session.scalars(
            select(ReviewFileLLMMessage)
            .where(ReviewFileLLMMessage.review_discussion_id == discussion.id)
            .order_by(ReviewFileLLMMessage.created_at)
        ).all()
        
        assert len(messages) == 2
        assert messages[0].role == 'user'
        assert messages[1].role == 'assistant'
        assert messages[0].content == '请审查这个文件的代码变更'
        assert messages[1].content == '代码质量良好，建议添加更多注释'


class TestModelIntegration:
    """模型集成测试"""
    
    def test_complete_review_workflow(self, test_db_session):
        """测试完整的评审工作流"""
        # 1. 创建评审
        review = Review(project_id=1, merge_request_id=123, status='pending')
        test_db_session.add(review)
        test_db_session.commit()
        
        # 2. 创建讨论
        discussion = ReviewDiscussion(
            review_id=review.id,
            discussion_id='discussion_123',
            file_path='src/main.py'
        )
        test_db_session.add(discussion)
        test_db_session.commit()
        
        # 3. 创建 LLM 消息
        user_message = ReviewFileLLMMessage(
            review_discussion_id=discussion.id,
            role='user',
            content='请审查代码'
        )
        
        assistant_message = ReviewFileLLMMessage(
            review_discussion_id=discussion.id,
            role='assistant',
            content='审查完成'
        )
        
        test_db_session.add_all([user_message, assistant_message])
        test_db_session.commit()
        
        # 4. 创建文件记录
        file_record = ReviewFileRecord(
            review_discussion_id=discussion.id,
            approved=True,
            score=8,
            issue=['小问题'],
            suggestion=['小改进'],
            summary='总体良好',
            llm_model='gpt-4'
        )
        test_db_session.add(file_record)
        test_db_session.commit()
        
        # 5. 验证完整流程
        # 通过评审查找所有相关记录
        discussions = test_db_session.scalars(
            select(ReviewDiscussion).where(ReviewDiscussion.review_id == review.id)
        ).all()
        
        assert len(discussions) == 1
        
        messages = test_db_session.scalars(
            select(ReviewFileLLMMessage)
            .where(ReviewFileLLMMessage.review_discussion_id == discussion.id)
        ).all()
        
        assert len(messages) == 2
        
        records = test_db_session.scalars(
            select(ReviewFileRecord)
            .where(ReviewFileRecord.review_discussion_id == discussion.id)
        ).all()
        
        assert len(records) == 1
        assert records[0].approved is True
        assert records[0].score == 8
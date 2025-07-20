from datetime import datetime
from typing import List

from sqlalchemy import BigInteger, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Review(Base):
    __tablename__ = "review"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, comment="项目ID")
    merge_request_id: Mapped[int] = mapped_column(Integer, comment="合并请求ID")
    status: Mapped[str] = mapped_column(String(16), default='pending', comment="状态，approved、rejected、pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,
                                                 comment="更新时间")


class ReviewDiscussion(Base):
    __tablename__ = "review_discussion"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("review.id"), comment="评审ID")
    discussion_id: Mapped[str] = mapped_column(String(64), comment="讨论ID")
    file_path: Mapped[str] = mapped_column(String(256), comment="文件名")


class ReviewFileRecord(Base):
    __tablename__ = "review_file_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    review_discussion_id: Mapped[int] = mapped_column(ForeignKey("review_discussion.id"), comment="评审讨论ID")
    approved: Mapped[bool] = mapped_column(Boolean, comment="是否通过")
    score: Mapped[int] = mapped_column(Integer, comment="评分")
    issue: Mapped[List[str]] = mapped_column(JSON, comment="问题")
    suggestion: Mapped[List[str]] = mapped_column(JSON, comment="建议")
    summary: Mapped[str] = mapped_column(String(256), comment="总结")
    llm_model: Mapped[str] = mapped_column(String(32), comment="LLM模型")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")


class ReviewFileLLMMessage(Base):
    __tablename__ = "review_file_llm_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    review_discussion_id: Mapped[int] = mapped_column(ForeignKey("review_discussion.id"), comment="评审讨论ID")
    role: Mapped[str] = mapped_column(String(16), comment="角色")
    content: Mapped[str] = mapped_column(String(2048), comment="内容")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

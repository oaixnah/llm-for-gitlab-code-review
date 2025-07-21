from typing import Optional, List, Dict

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as SessionType

from config import Session
from i18n import i18n
from models import Review, ReviewDiscussion, ReviewFileRecord, ReviewFileLLMMessage


def _get_review_by_project_and_mr(session: SessionType, project_id: int, merge_request_id: int) -> Optional[Review]:
    """根据项目ID和MR ID获取评审记录

    Args:
        session: 数据库会话
        project_id: 项目ID
        merge_request_id: 合并请求ID

    Returns:
        Review对象或None
    """
    return session.scalar(
        select(Review).where(and_(
            Review.project_id == project_id,
            Review.merge_request_id == merge_request_id
        ))
    )


def _get_review_discussion_id_by_discussion_id(session: SessionType, discussion_id: str) -> Optional[int]:
    """根据讨论ID获取评审讨论记录ID

    Args:
        session: 数据库会话
        discussion_id: 讨论ID

    Returns:
        评审讨论记录ID或None
    """
    return session.scalar(
        select(ReviewDiscussion.id).where(
            ReviewDiscussion.discussion_id == discussion_id
        )
    )


def update_or_create_review(
        project_id: int,
        merge_request_id: int,
        status: Optional[str] = None
) -> int:
    """更新或创建评审记录

    Args:
        project_id: 项目ID
        merge_request_id: 合并请求ID
        status: 状态，approved、rejected、pending

    Returns:
        评审记录ID

    Raises:
        SQLAlchemyError: 数据库操作异常
    """
    try:
        with Session() as session:
            review = _get_review_by_project_and_mr(
                session, project_id, merge_request_id
            )

            if review:
                # 更新现有记录
                if status is not None:
                    review.status = status
            else:
                # 创建新记录
                review = Review(
                    project_id=project_id,
                    merge_request_id=merge_request_id,
                    status=status
                )
                session.add(review)

            session.commit()
            return review.id
    except SQLAlchemyError as e:
        raise SQLAlchemyError(
            i18n.t('response.update_or_create_review_failed', project_id=project_id, merge_request_id=merge_request_id,
                   error=str(e)))


def get_review(project_id: int, merge_request_id: int) -> Optional[Review]:
    """获取评审记录

    Args:
        project_id: 项目ID
        merge_request_id: 合并请求ID

    Returns:
        评审记录或None
    """
    try:
        with Session() as session:
            return _get_review_by_project_and_mr(session, project_id, merge_request_id)
    except SQLAlchemyError as e:
        raise SQLAlchemyError(
            i18n.t('response.get_review_failed', project_id=project_id, merge_request_id=merge_request_id,
                   error=str(e)))


def get_discussion_id(project_id: int, merge_request_id: int, file_path: str) -> Optional[str]:
    """获取评审讨论ID

    Args:
        project_id: 项目ID
        merge_request_id: 合并请求ID
        file_path: 文件路径

    Returns:
        评审讨论ID或None
    """
    try:
        with Session() as session:
            return session.scalar(
                select(ReviewDiscussion.discussion_id)
                .join(Review, ReviewDiscussion.review_id == Review.id)
                .where(
                    and_(
                        Review.project_id == project_id,
                        Review.merge_request_id == merge_request_id,
                        ReviewDiscussion.file_path == file_path
                    )
                )
            )
    except SQLAlchemyError as e:
        raise SQLAlchemyError(
            i18n.t('response.get_discussion_id_failed', project_id=project_id, merge_request_id=merge_request_id,
                   file_path=file_path, error=str(e)))


def create_review_discussion(
        project_id: int,
        merge_request_id: int,
        discussion_id: str,
        file_path: str
) -> int:
    """创建评审讨论记录

    Args:
        project_id: 项目ID
        merge_request_id: 合并请求ID
        discussion_id: 评审讨论ID
        file_path: 文件路径

    Returns:
        评审讨论记录ID

    Raises:
        ValueError: 找不到对应的评审记录
        SQLAlchemyError: 数据库操作异常
    """
    try:
        with Session() as session:
            review_id = session.scalar(
                select(Review.id).where(and_(
                    Review.project_id == project_id,
                    Review.merge_request_id == merge_request_id
                ))
            )

            if not review_id:
                raise ValueError(f"找不到项目ID {project_id} 和MR ID {merge_request_id} 对应的评审记录")

            discussion = ReviewDiscussion(
                review_id=review_id,
                discussion_id=discussion_id,
                file_path=file_path
            )
            session.add(discussion)
            session.commit()
            return discussion.id
    except SQLAlchemyError as e:
        raise SQLAlchemyError(
            i18n.t('response.create_review_discussion_failed', discussion_id=discussion_id, file_path=file_path,
                   error=str(e)))


def get_review_discussion_id(discussion_id: str) -> Optional[int]:
    """获取评审讨论记录ID

    Args:
        discussion_id: 评审讨论ID

    Returns:
        评审讨论记录ID或None
    """
    try:
        with Session() as session:
            return _get_review_discussion_id_by_discussion_id(
                session, discussion_id
            )
    except SQLAlchemyError as e:
        raise SQLAlchemyError(
            i18n.t('response.get_review_discussion_id_failed', discussion_id=discussion_id, error=str(e)))


def create_review_file_record(
        discussion_id: str,
        approved: bool,
        score: int,
        issues: List[str],
        suggestions: List[str],
        summary: str,
        llm_model: str,
) -> None:
    """创建评审文件记录

    Args:
        discussion_id: 评审讨论ID
        approved: 是否通过
        score: 评分
        issues: 问题列表
        suggestions: 建议列表
        summary: 总结
        llm_model: LLM模型

    Raises:
        ValueError: 找不到对应的评审讨论记录
        SQLAlchemyError: 数据库操作异常
    """
    try:
        with Session() as session:
            review_discussion_id = _get_review_discussion_id_by_discussion_id(
                session, discussion_id
            )

            if not review_discussion_id:
                raise ValueError(f"找不到讨论ID {discussion_id} 对应的评审讨论记录")

            file_record = ReviewFileRecord(
                review_discussion_id=review_discussion_id,
                approved=approved,
                score=score,
                issue=issues,
                suggestion=suggestions,
                summary=summary,
                llm_model=llm_model
            )
            session.add(file_record)
            session.commit()
    except SQLAlchemyError as e:
        raise SQLAlchemyError(
            i18n.t('response.create_review_file_record_failed', discussion_id=discussion_id, error=str(e)))


def create_review_file_llm_message(discussion_id: str, role: str, content: str) -> None:
    """创建评审文件LLM消息

    Args:
        discussion_id: 评审讨论ID
        role: 角色
        content: 内容

    Raises:
        ValueError: 找不到对应的评审讨论记录
        SQLAlchemyError: 数据库操作异常
    """
    try:
        with Session() as session:
            review_discussion_id = _get_review_discussion_id_by_discussion_id(
                session, discussion_id
            )

            if not review_discussion_id:
                raise ValueError(i18n.t('response.get_review_discussion_id_failed', discussion_id=discussion_id))

            llm_message = ReviewFileLLMMessage(
                review_discussion_id=review_discussion_id,
                role=role,
                content=content
            )
            session.add(llm_message)
            session.commit()
    except SQLAlchemyError as e:
        raise SQLAlchemyError(
            i18n.t('response.create_review_file_llm_message_failed', discussion_id=discussion_id, error=str(e)))


def get_review_file_llm_messages(discussion_id: str) -> List[Dict[str, str]]:
    """获取评审文件LLM消息

    Args:
        discussion_id: 评审讨论ID

    Returns:
        LLM消息列表，每个消息包含role和content字段
    """
    try:
        with Session() as session:
            messages = session.scalars(
                select(ReviewFileLLMMessage)
                .join(
                    ReviewDiscussion,
                    ReviewDiscussion.id == ReviewFileLLMMessage.review_discussion_id
                )
                .where(ReviewDiscussion.discussion_id == discussion_id)
                .order_by(ReviewFileLLMMessage.id)  # 按创建顺序排序
            ).all()

            return [
                {
                    "role": message.role,
                    "content": message.content
                }
                for message in messages
            ]
    except SQLAlchemyError as e:
        raise SQLAlchemyError(
            i18n.t('response.get_review_file_llm_messages_failed', discussion_id=discussion_id, error=str(e)))

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List

from gitlab import Gitlab, GitlabGetError
from gitlab.v4.objects import Project
from gitlab.v4.objects.merge_requests import ProjectMergeRequest
from gitlab.v4.objects.users import User

from config import settings
from curd import update_or_create_review, get_discussion_id, get_review_file_llm_messages, create_review_discussion, \
    create_review_file_record, create_review_file_llm_message
from i18n import i18n
from llm import Service as LLMService
from utils import is_supported_file, get_file_user_prompt, get_file_system_prompt, get_discussion_content, \
    deserialize_llm_resp

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """评审状态枚举"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class MergeRequestAction(Enum):
    """合并请求动作枚举"""
    OPEN = 'open'
    UPDATE = 'update'
    CLOSE = 'close'
    REOPEN = 'reopen'


@dataclass
class ReviewResult:
    """评审结果数据类"""
    approved: bool
    issues: List[str]
    suggestions: List[str]
    score: int
    summary: str
    duration: float


class ReviewManager:
    """评审管理器类"""
    MAX_CONCURRENT_REVIEWS = 10  # 最大并发评审数量

    def __init__(self):
        self.gl = Gitlab(
            url=settings.gitlab_url,
            oauth_token=settings.gitlab_token,
        )
        self.reviewers: Optional[User] = None
        self.llm_service = LLMService()
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REVIEWS)

    def check(self) -> bool:
        """连接性检查"""
        try:
            self.gl.auth()
            return True
        except Exception as e:
            logger.error(f"{i18n.t('log.gitlab_connection_failed')}: {e}")
            raise Exception(f"{i18n.t('log.gitlab_connection_failed')}: {e}")

    def is_reviewer(self, event_data: Dict[str, Any]) -> bool:
        """检查用户是否是审核者"""
        if self.reviewers is None:
            return False

        reviewer_ids = event_data.get('reviewer_ids', [])
        reviewers = event_data.get('reviewers', [])
        reviewer_user_ids = [u.get('id') for u in reviewers if isinstance(u, dict) and 'id' in u]

        return self.reviewers.id in reviewer_ids or self.reviewers.id in reviewer_user_ids

    async def process_merge_request_event(self, event_data: Dict[str, Any]) -> bool:
        """处理合并请求事件

        Args:
            event_data: GitLab webhook 事件数据

        Returns:
            bool: 是否成功处理事件
        """
        if event_data.get('object_kind') != 'merge_request':
            return False

        try:
            object_attributes = event_data.get('object_attributes', {})
            project_id = object_attributes.get('target_project_id')
            merge_request_iid = object_attributes.get('iid')
            action = object_attributes.get('action')  # open, update, close, reopen

            if not all([project_id, merge_request_iid, action]):
                logger.warning(i18n.t('log.event_missing_fields'))
                return False

            # 项目是否有效
            project = await self._get_project(project_id)
            if not project:
                return False

            # 是否参与审核
            if not self.is_reviewer(event_data):
                logger.info(i18n.t('log.project_not_participating', project=project.path_with_namespace))
                return False

            merge_request = project.mergerequests.get(merge_request_iid)

            # 检查是否应该处理评审
            if not await self._should_process_review(project, merge_request):
                return False

            # 根据动作类型处理
            await self._dispatch_action(action, project, merge_request)
            return True

        except Exception as e:
            logger.error(f"{i18n.t('log.mr_event_process_failed')} {e}")
            return False

    async def _get_project(self, project_id: int) -> Optional[Project]:
        """获取项目对象"""
        try:
            return self.gl.projects.get(project_id)
        except GitlabGetError:
            logger.warning(i18n.t('log.project_no_permission', project_id=project_id))
            return None
        except Exception as e:
            logger.error(i18n.t('log.project_get_failed', project_id=project_id) + f" {e}")
            return None

    @staticmethod
    async def _should_process_review(project: Project, merge_request: ProjectMergeRequest) -> bool:
        """检查是否应该处理评审"""
        try:
            # 只处理打开状态且未被批准的合并请求
            if merge_request.state != 'opened':
                logger.info(
                    i18n.t('log.mr_status_skip',
                           project=project.path_with_namespace,
                           iid=merge_request.iid,
                           state=merge_request.state)
                )
                return False

            # 检查是否已被批准
            try:
                approvals = merge_request.approvals.get()
                if approvals.approved:
                    logger.info(
                        i18n.t('log.mr_already_approved',
                               project=project.path_with_namespace,
                               iid=merge_request.iid)
                    )
                    return False
            except GitlabGetError:
                # 如果无法获取批准状态，继续处理
                pass

            return True
        except Exception as e:
            logger.error(i18n.t('log.mr_check_status_failed',
                                project=project.path_with_namespace,
                                iid=merge_request.iid) + f" {e}")
            return False

    async def _dispatch_action(self, action: str, project: Project, merge_request: ProjectMergeRequest):
        """根据动作类型分发处理"""
        if action in ('open', 'update', 'reopen'):
            logger.info(i18n.t('log.mr_action_start',
                               project=project.path_with_namespace,
                               iid=merge_request.iid,
                               action=action))
            await self._review_mr_change_files(project, merge_request)
        else:
            logger.info(i18n.t('log.mr_other_action', action=action))

    async def _review_mr_change_files(self, project: Project, merge_request: ProjectMergeRequest):
        """评审变更的代码文件"""
        mr_info = f"{project.path_with_namespace} (!{merge_request.iid})"

        try:
            update_or_create_review(project.id, merge_request.iid, ReviewStatus.PENDING.value)

            changes = merge_request.changes()
            if not changes.get('changes'):
                logger.info(i18n.t('log.mr_no_changes', mr_info=mr_info))
                return

            change_files = changes["changes"]
            logger.info(i18n.t('log.mr_review_start', mr_info=mr_info, count=len(change_files)))

            # 筛选需要评审的文件
            review_tasks = []
            for change in change_files:
                if self._should_review_file(change, project, merge_request):
                    task = self._review_single_file(project, merge_request, change, changes)
                    review_tasks.append(task)

            if not review_tasks:
                logger.info(i18n.t('log.mr_no_review_files', mr_info=mr_info))
                return

            # 文件数量限制检查
            if len(review_tasks) > 20:
                await self._create_file_limit_notification(merge_request, len(review_tasks))
                return

            # 并行执行文件评审
            results = await asyncio.gather(*review_tasks, return_exceptions=True)

            # 统计评审结果
            approved_count = 0
            error_count = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                    logger.error(f"文件评审异常: {result}")
                elif result:
                    approved_count += 1

            total_reviewed = len(review_tasks) - error_count
            logger.info(
                f"合并请求 {mr_info} 评审完成: {approved_count}/{total_reviewed} 个文件通过"
            )

            # 如果所有文件都通过评审，自动批准
            if approved_count == total_reviewed and total_reviewed > 0:
                await self._approve_merge_request(project, merge_request)

        except Exception as e:
            logger.error(f"评审变更文件失败: {e}")
            update_or_create_review(project.id, merge_request.iid, ReviewStatus.REJECTED.value)

    @staticmethod
    def _should_review_file(change: Dict[str, Any], project: Project, merge_request: ProjectMergeRequest) -> bool:
        """检查文件是否需要评审"""
        old_path = change.get('old_path', '')
        new_path = change.get('new_path', '')
        file_path = new_path or old_path

        mr_info = f"{project.path_with_namespace} (!{merge_request.iid})"

        # 检查文件类型支持
        if not is_supported_file(file_path):
            logger.debug(f"合并请求 {mr_info} 文件 {file_path} 不支持，跳过处理")
            return False

        # 跳过删除的文件
        if change.get('deleted_file'):
            logger.debug(f"合并请求 {mr_info} 文件 {file_path} 已删除，跳过处理")
            return False

        # 跳过重命名但内容未变更的文件
        if change.get('renamed_file') and not change.get('diff'):
            logger.debug(f"合并请求 {mr_info} 文件 {file_path} 仅重命名无内容变更，跳过处理")
            return False

        return True

    async def _review_single_file(self, project: Project, merge_request: ProjectMergeRequest,
                                  change: Dict[str, Any], changes: Dict[str, Any]) -> bool:
        """评审单个文件

        Returns:
            bool: 文件是否通过评审
        """
        async with self._semaphore:
            file_path = change.get('new_path') or change.get('old_path', 'unknown')
            try:
                # 检查是否已有讨论
                discussion_id = get_discussion_id(project.id, merge_request.iid, file_path)

                if discussion_id:
                    return await self._update_existing_discussion(
                        project, merge_request, change, discussion_id
                    )
                else:
                    return await self._create_new_discussion(
                        project, merge_request, change, changes
                    )

            except Exception as e:
                logger.error(f"评审文件 {file_path} 失败: {e}")
                return False

    async def _update_existing_discussion(self, project: Project, merge_request: ProjectMergeRequest,
                                          change: Dict[str, Any], discussion_id: str) -> bool:
        """更新已有讨论"""
        mr_info = f"{project.path_with_namespace} (!{merge_request.iid})"
        file_path = change.get('new_path') or change.get('old_path', 'unknown')

        try:
            # 检查讨论是否已解决
            discussion_obj = merge_request.discussions.get(discussion_id)
            discussion = discussion_obj.asdict()

            if discussion.get('resolved', False) or any(
                    note.get('resolved', False) for note in discussion.get('notes', [])):
                logger.info(f"合并请求 {mr_info} 文件 {file_path} 的讨论已解决，跳过处理")
                return True

            # 获取历史消息并进行评审
            history_msg = get_review_file_llm_messages(discussion_id)
            llm_resp = await self._perform_llm_review(change, history_msg)

            # 保存评审结果
            await self._save_discussion_records(discussion_id, llm_resp, change)

            # 添加评论
            comment = get_discussion_content(llm_resp)
            discussion_obj.notes.create({
                'body': comment,
                'discussion_id': discussion_id,
            })

            # 如果通过评审，标记为已解决
            approved = llm_resp.get('approved', False)
            if approved:
                await self._resolve_discussion(merge_request, discussion_id, project, change)
                logger.info(f"合并请求 {mr_info} 文件 {file_path} 评审通过")
            else:
                logger.info(f"合并请求 {mr_info} 文件 {file_path} 评审未通过")

            return approved

        except Exception as e:
            logger.error(f"更新讨论失败 (文件: {file_path}): {e}")
            return False

    async def _create_new_discussion(self, project: Project, merge_request: ProjectMergeRequest,
                                     change: Dict[str, Any], changes: Dict[str, Any]) -> bool:
        """创建新讨论"""
        mr_info = f"{project.path_with_namespace} (!{merge_request.iid})"
        file_path = change.get('new_path') or change.get('old_path', 'unknown')

        try:
            # 进行LLM评审
            llm_resp = await self._perform_llm_review(change, [])

            # 创建讨论
            comment = get_discussion_content(llm_resp)
            discussion_data = {
                'body': comment,
                'position': {
                    **changes.get('diff_refs', {}),
                    'old_path': change.get('old_path'),
                    'new_path': change.get('new_path'),
                    'position_type': 'file',
                }
            }

            discussion = merge_request.discussions.create(discussion_data)
            discussion_id = discussion.id

            logger.info(f"合并请求 {mr_info} 文件 {file_path} 讨论创建成功: {discussion_id}")

            # 保存记录
            create_review_discussion(project.id, merge_request.iid, discussion_id, file_path)
            await self._save_discussion_records(discussion_id, llm_resp, change)

            # 如果通过评审，标记为已解决
            approved = llm_resp.get('approved', False)
            if approved:
                await self._resolve_discussion(merge_request, discussion_id, project, change)
                logger.info(f"合并请求 {mr_info} 文件 {file_path} 评审通过")
            else:
                logger.info(f"合并请求 {mr_info} 文件 {file_path} 评审未通过")

            return approved

        except Exception as e:
            logger.error(f"创建讨论失败 (文件: {file_path}): {e}")
            return False

    async def _perform_llm_review(self, change: Dict[str, Any],
                                  history_msg: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """执行LLM评审"""
        if history_msg is None:
            history_msg = []

        try:
            messages = [
                {"role": "system", "content": get_file_system_prompt()},
                *history_msg,
                {"role": "user", "content": get_file_user_prompt(change)}
            ]

            return await asyncio.to_thread(self.llm_service.chat, messages)
        except Exception as e:
            logger.error(f"LLM评审失败: {e}")
            # 返回默认的拒绝结果
            return {
                'approved': False,
                'issues': [f'LLM评审服务异常: {str(e)}'],
                'suggestions': ['请检查LLM服务状态后重试'],
                'score': 0,
                'summary': 'LLM服务异常，无法完成评审'
            }

    async def _save_discussion_records(self, discussion_id: str, llm_resp: Dict[str, Any],
                                       change: Dict[str, Any]):
        """保存讨论记录"""
        try:
            # 保存评审记录
            create_review_file_record(
                discussion_id=discussion_id,
                llm_model=self.llm_service.model,
                **llm_resp
            )

            # 保存LLM消息记录 - 先保存用户消息，再保存助手回复
            create_review_file_llm_message(
                discussion_id=discussion_id,
                role='user',
                content=get_file_user_prompt(change)
            )

            create_review_file_llm_message(
                discussion_id=discussion_id,
                role='assistant',
                content=deserialize_llm_resp(llm_resp)
            )

        except Exception as e:
            logger.error(f"保存讨论记录失败 (discussion_id: {discussion_id}): {e}")

    @staticmethod
    async def _resolve_discussion(merge_request: ProjectMergeRequest, discussion_id: str,
                                  project: Project, change: Dict[str, Any]):
        """解决讨论"""
        file_path = change.get('new_path') or change.get('old_path', 'unknown')
        mr_info = f"{project.path_with_namespace} (!{merge_request.iid})"

        try:
            discussion = merge_request.discussions.get(discussion_id)
            discussion.resolved = True
            discussion.save()

            logger.debug(f"合并请求 {mr_info} 文件 {file_path} 讨论已标记为解决")
        except Exception as e:
            logger.error(f"解决讨论失败 (文件: {file_path}, discussion_id: {discussion_id}): {e}")

    @staticmethod
    async def _create_file_limit_notification(merge_request: ProjectMergeRequest, file_count: int):
        """创建文件数量限制通知"""
        try:
            notification_body = (
                f"📢 **文件变更数量过多通知**\n\n"
                f"本次合并请求包含 **{file_count}** 个文件变更，超过了单次评审限制（20个文件）。\n\n"
                f"为了保证评审质量和系统性能，建议：\n"
                f"1. 将大型变更拆分为多个较小的合并请求\n"
                f"2. 确保每个合并请求专注于单一功能或修复\n"
                f"3. 如有必要，可以手动触发部分文件的评审\n\n"
                f"如需强制评审，请联系管理员。"
            )

            merge_request.discussions.create({'body': notification_body})
            logger.info(f"已创建文件数量限制通知，文件数: {file_count}")
        except Exception as e:
            logger.error(f"创建文件数量限制通知失败: {e}")

    @staticmethod
    async def _approve_merge_request(project: Project, merge_request: ProjectMergeRequest):
        """批准合并请求"""
        try:
            mr_info = f"{project.path_with_namespace} (!{merge_request.iid})"
            logger.info(f"合并请求 {mr_info} 所有文件代码评审通过，准备批准")

            update_or_create_review(project.id, merge_request.iid, ReviewStatus.APPROVED.value)
            merge_request.approve()

            logger.info(f"合并请求 {mr_info} 已成功批准")
        except Exception as e:
            logger.error(f"批准合并请求失败: {e}")

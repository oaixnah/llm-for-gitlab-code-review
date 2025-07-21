#!/usr/bin/env python3
"""
测试数据生成脚本

用于生成各种测试场景的数据，包括：
- 模拟 GitLab webhook 数据
- 生成测试用的代码差异
- 创建性能测试数据
- 生成国际化测试数据
"""

import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any


class TestDataGenerator:
    """测试数据生成器"""
    
    def __init__(self, output_dir: str = "test_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 编程语言和文件扩展名
        self.languages = {
            "python": [".py"],
            "javascript": [".js", ".ts", ".jsx", ".tsx"],
            "java": [".java"],
            "go": [".go"],
            "rust": [".rs"],
            "cpp": [".cpp", ".cc", ".cxx", ".h", ".hpp"],
            "csharp": [".cs"],
            "php": [".php"],
            "ruby": [".rb"],
            "swift": [".swift"]
        }
        
        # 常见的文件路径模式
        self.path_patterns = [
            "src/{module}/{file}",
            "lib/{module}/{file}",
            "app/{module}/{file}",
            "components/{file}",
            "utils/{file}",
            "services/{file}",
            "models/{file}",
            "controllers/{file}",
            "views/{file}",
            "tests/{file}"
        ]
    
    def generate_random_string(self, length: int = 10) -> str:
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def generate_file_path(self, language: str = None) -> str:
        """生成文件路径"""
        if not language:
            language = random.choice(list(self.languages.keys()))
        
        extension = random.choice(self.languages[language])
        pattern = random.choice(self.path_patterns)
        
        module = self.generate_random_string(8).lower()
        filename = self.generate_random_string(12).lower() + extension
        
        return pattern.format(module=module, file=filename)
    
    def generate_code_diff(self, language: str = "python") -> str:
        """生成代码差异"""
        if language == "python":
            return self._generate_python_diff()
        elif language == "javascript":
            return self._generate_javascript_diff()
        else:
            return self._generate_generic_diff()
    
    def _generate_python_diff(self) -> str:
        """生成 Python 代码差异"""
        diffs = [
            '''@@ -1,5 +1,8 @@
 def calculate_sum(numbers):
+    if not numbers:
+        return 0
+    
     total = 0
     for num in numbers:
         total += num
     return total''',
            
            '''@@ -10,3 +10,6 @@
 class UserService:
     def get_user(self, user_id):
-        return self.db.query(User).filter(User.id == user_id).first()
+        user = self.db.query(User).filter(User.id == user_id).first()
+        if not user:
+            raise UserNotFoundError(f"User {user_id} not found")
+        return user''',
            
            '''@@ -1,4 +1,7 @@
 import os
 import sys
+import logging
+
+logger = logging.getLogger(__name__)
 
 def main():'''
        ]
        return random.choice(diffs)
    
    def _generate_javascript_diff(self) -> str:
        """生成 JavaScript 代码差异"""
        diffs = [
            '''@@ -1,5 +1,8 @@
 function validateEmail(email) {
+    if (!email) {
+        return false;
+    }
     const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
     return regex.test(email);
 }''',
            
            '''@@ -8,2 +8,5 @@
 const fetchUserData = async (userId) => {
-    const response = await fetch(`/api/users/${userId}`);
+    const response = await fetch(`/api/users/${userId}`);
+    if (!response.ok) {
+        throw new Error(`HTTP error! status: ${response.status}`);
+    }
     return response.json();'''
        ]
        return random.choice(diffs)
    
    def _generate_generic_diff(self) -> str:
        """生成通用代码差异"""
        return '''@@ -1,3 +1,6 @@
 // Original code
+// Added comment
+
 function example() {
     return true;
 }'''
    
    def generate_gitlab_webhook(self, event_type: str = "merge_request") -> Dict[str, Any]:
        """生成 GitLab webhook 数据"""
        if event_type == "merge_request":
            return self._generate_merge_request_webhook()
        else:
            return {"object_kind": event_type}
    
    def _generate_merge_request_webhook(self) -> Dict[str, Any]:
        """生成合并请求 webhook 数据"""
        project_id = random.randint(1, 1000)
        mr_iid = random.randint(1, 500)
        
        # 生成文件变更
        changes = []
        num_files = random.randint(1, 10)
        
        for _ in range(num_files):
            file_path = self.generate_file_path()
            language = self._detect_language(file_path)
            
            changes.append({
                "old_path": file_path,
                "new_path": file_path,
                "a_mode": "100644",
                "b_mode": "100644",
                "new_file": False,
                "renamed_file": False,
                "deleted_file": False,
                "diff": self.generate_code_diff(language)
            })
        
        return {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "user": {
                "id": random.randint(1, 100),
                "name": f"User {self.generate_random_string(6)}",
                "username": f"user_{self.generate_random_string(8).lower()}",
                "email": f"user@example.com"
            },
            "project": {
                "id": project_id,
                "name": f"Project {self.generate_random_string(8)}",
                "description": "Test project for code review",
                "web_url": f"https://gitlab.example.com/group/project-{project_id}",
                "avatar_url": None,
                "git_ssh_url": f"git@gitlab.example.com:group/project-{project_id}.git",
                "git_http_url": f"https://gitlab.example.com/group/project-{project_id}.git",
                "namespace": "group",
                "visibility_level": 20,
                "path_with_namespace": f"group/project-{project_id}",
                "default_branch": "main"
            },
            "object_attributes": {
                "assignee_id": None,
                "author_id": random.randint(1, 100),
                "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                "description": "Test merge request for automated code review",
                "head_pipeline_id": random.randint(1000, 9999),
                "id": random.randint(10000, 99999),
                "iid": mr_iid,
                "last_edited_at": None,
                "last_edited_by_id": None,
                "merge_commit_sha": None,
                "merge_error": None,
                "merge_params": {
                    "force_remove_source_branch": "1"
                },
                "merge_status": "can_be_merged",
                "merge_user_id": None,
                "merge_when_pipeline_succeeds": False,
                "milestone_id": None,
                "source_branch": f"feature/{self.generate_random_string(10).lower()}",
                "source_project_id": project_id,
                "state_id": 1,
                "target_branch": "main",
                "target_project_id": project_id,
                "time_estimate": 0,
                "title": f"Feature: {self.generate_random_string(15)}",
                "updated_at": datetime.now().isoformat(),
                "updated_by_id": random.randint(1, 100),
                "url": f"https://gitlab.example.com/group/project-{project_id}/-/merge_requests/{mr_iid}",
                "source": {
                    "id": project_id,
                    "name": f"Project {self.generate_random_string(8)}",
                    "description": "Test project",
                    "web_url": f"https://gitlab.example.com/group/project-{project_id}",
                    "avatar_url": None,
                    "git_ssh_url": f"git@gitlab.example.com:group/project-{project_id}.git",
                    "git_http_url": f"https://gitlab.example.com/group/project-{project_id}.git",
                    "namespace": "group",
                    "visibility_level": 20,
                    "path_with_namespace": f"group/project-{project_id}",
                    "default_branch": "main"
                },
                "target": {
                    "id": project_id,
                    "name": f"Project {self.generate_random_string(8)}",
                    "description": "Test project",
                    "web_url": f"https://gitlab.example.com/group/project-{project_id}",
                    "avatar_url": None,
                    "git_ssh_url": f"git@gitlab.example.com:group/project-{project_id}.git",
                    "git_http_url": f"https://gitlab.example.com/group/project-{project_id}.git",
                    "namespace": "group",
                    "visibility_level": 20,
                    "path_with_namespace": f"group/project-{project_id}",
                    "default_branch": "main"
                },
                "last_commit": {
                    "id": self.generate_random_string(40).lower(),
                    "message": f"Add {self.generate_random_string(10)} functionality",
                    "timestamp": datetime.now().isoformat(),
                    "url": f"https://gitlab.example.com/group/project-{project_id}/-/commit/{self.generate_random_string(40).lower()}",
                    "author": {
                        "name": f"Author {self.generate_random_string(6)}",
                        "email": "author@example.com"
                    }
                },
                "work_in_progress": False,
                "total_time_spent": 0,
                "human_total_time_spent": None,
                "human_time_estimate": None,
                "assignee_ids": [],
                "reviewer_ids": [],
                "action": random.choice(["open", "update", "reopen"])
            },
            "labels": [],
            "changes": {
                "updated_at": {
                    "previous": (datetime.now() - timedelta(minutes=30)).isoformat(),
                    "current": datetime.now().isoformat()
                }
            },
            "repository": {
                "name": f"Project {self.generate_random_string(8)}",
                "url": f"git@gitlab.example.com:group/project-{project_id}.git",
                "description": "Test project",
                "homepage": f"https://gitlab.example.com/group/project-{project_id}"
            }
        }
    
    def _detect_language(self, file_path: str) -> str:
        """根据文件路径检测编程语言"""
        extension = Path(file_path).suffix
        for lang, exts in self.languages.items():
            if extension in exts:
                return lang
        return "generic"
    
    def generate_performance_data(self, num_requests: int = 100) -> List[Dict[str, Any]]:
        """生成性能测试数据"""
        data = []
        
        for i in range(num_requests):
            # 模拟不同大小的合并请求
            num_files = random.choices(
                [1, 3, 5, 10, 20, 50],
                weights=[30, 25, 20, 15, 8, 2]
            )[0]
            
            webhook_data = self._generate_merge_request_webhook()
            
            # 添加性能相关的元数据
            webhook_data["_performance_metadata"] = {
                "request_id": i + 1,
                "num_files": num_files,
                "estimated_complexity": random.choice(["low", "medium", "high"]),
                "file_sizes": [random.randint(100, 10000) for _ in range(num_files)],
                "total_lines_changed": random.randint(10, 1000)
            }
            
            data.append(webhook_data)
        
        return data
    
    def generate_i18n_test_data(self) -> Dict[str, Dict[str, str]]:
        """生成国际化测试数据"""
        return {
            "zh_CN": {
                "system_prompt": "你是一个专业的代码审查助手。",
                "user_prompt": "请审查以下代码变更：",
                "discussion_content": "建议改进代码质量。",
                "error_message": "处理请求时发生错误。",
                "success_message": "代码审查完成。"
            },
            "en_US": {
                "system_prompt": "You are a professional code review assistant.",
                "user_prompt": "Please review the following code changes:",
                "discussion_content": "Suggest improvements to code quality.",
                "error_message": "An error occurred while processing the request.",
                "success_message": "Code review completed."
            },
            "ja_JP": {
                "system_prompt": "あなたはプロのコードレビューアシスタントです。",
                "user_prompt": "以下のコード変更をレビューしてください：",
                "discussion_content": "コード品質の改善を提案します。",
                "error_message": "リクエストの処理中にエラーが発生しました。",
                "success_message": "コードレビューが完了しました。"
            }
        }
    
    def save_data(self, data: Any, filename: str) -> None:
        """保存数据到文件"""
        file_path = self.output_dir / filename
        
        if filename.endswith('.json'):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(data))
        
        print(f"数据已保存到: {file_path}")
    
    def generate_all_test_data(self) -> None:
        """生成所有测试数据"""
        print("开始生成测试数据...")
        
        # 生成基本的 webhook 数据
        webhook_data = self.generate_gitlab_webhook()
        self.save_data(webhook_data, "sample_webhook.json")
        
        # 生成多个 webhook 数据用于批量测试
        multiple_webhooks = [self.generate_gitlab_webhook() for _ in range(10)]
        self.save_data(multiple_webhooks, "multiple_webhooks.json")
        
        # 生成性能测试数据
        performance_data = self.generate_performance_data(50)
        self.save_data(performance_data, "performance_test_data.json")
        
        # 生成国际化测试数据
        i18n_data = self.generate_i18n_test_data()
        self.save_data(i18n_data, "i18n_test_data.json")
        
        # 生成边界情况测试数据
        edge_cases = self._generate_edge_cases()
        self.save_data(edge_cases, "edge_cases.json")
        
        print("所有测试数据生成完成！")
    
    def _generate_edge_cases(self) -> List[Dict[str, Any]]:
        """生成边界情况测试数据"""
        cases = []
        
        # 空的合并请求
        empty_mr = self.generate_gitlab_webhook()
        empty_mr["object_attributes"]["description"] = ""
        empty_mr["object_attributes"]["title"] = ""
        cases.append({"name": "empty_merge_request", "data": empty_mr})
        
        # 大型合并请求（很多文件）
        large_mr = self.generate_gitlab_webhook()
        # 这里可以添加更多文件变更
        cases.append({"name": "large_merge_request", "data": large_mr})
        
        # 特殊字符的合并请求
        special_char_mr = self.generate_gitlab_webhook()
        special_char_mr["object_attributes"]["title"] = "测试 🚀 Special chars: @#$%^&*()"
        special_char_mr["object_attributes"]["description"] = "包含特殊字符的描述：中文、emoji 😊、符号 @#$%"
        cases.append({"name": "special_characters", "data": special_char_mr})
        
        # 无效的 webhook 数据
        invalid_webhook = {"object_kind": "invalid_event"}
        cases.append({"name": "invalid_webhook", "data": invalid_webhook})
        
        # 缺少必要字段的 webhook
        incomplete_webhook = self.generate_gitlab_webhook()
        del incomplete_webhook["object_attributes"]["iid"]
        cases.append({"name": "incomplete_webhook", "data": incomplete_webhook})
        
        return cases


def main():
    """主函数"""
    generator = TestDataGenerator()
    generator.generate_all_test_data()


if __name__ == "__main__":
    main()
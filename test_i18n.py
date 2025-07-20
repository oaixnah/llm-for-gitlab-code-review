#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国际化功能测试脚本

用于测试项目的国际化功能是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from i18n import i18n, init_i18n
from utils import get_file_system_prompt, get_file_user_prompt, get_discussion_content


def test_i18n_basic():
    """测试基本的国际化功能"""
    print("=== 测试基本国际化功能 ===")

    # 初始化国际化
    init_i18n()

    # 测试中文
    print("\n--- 测试中文 (zh_CN) ---")
    i18n.set_locale('zh_CN')
    print(f"当前语言: {i18n.get_locale()}")
    print(f"GitLab连接失败: {i18n.t('log.gitlab_connection_failed')}")
    print(f"事件类型: {i18n.t('log.ignore_event_type')}")
    print(f"状态-已接受: {i18n.t('status.accepted')}")

    # 测试英文
    print("\n--- 测试英文 (en_US) ---")
    i18n.set_locale('en_US')
    print(f"当前语言: {i18n.get_locale()}")
    print(f"GitLab连接失败: {i18n.t('log.gitlab_connection_failed')}")
    print(f"事件类型: {i18n.t('log.ignore_event_type')}")
    print(f"状态-已接受: {i18n.t('status.accepted')}")

    # 测试模板变量
    print("\n--- 测试模板变量 ---")
    msg = i18n.t('log.mr_action_start', project='test/repo', iid=123, action='open')
    print(f"合并请求消息: {msg}")

    # 测试不存在的键
    print("\n--- 测试不存在的键 ---")
    missing_key = i18n.t('non.existent.key')
    print(f"不存在的键: {missing_key}")


def test_templates():
    """测试模板功能"""
    print("\n=== 测试模板功能 ===")

    # 测试系统提示词模板
    print("\n--- 测试系统提示词模板 ---")

    # 中文模板
    i18n.set_locale('zh_CN')
    try:
        system_prompt_zh = get_file_system_prompt()
        print(f"中文系统提示词长度: {len(system_prompt_zh)} 字符")
        print(f"中文系统提示词预览: {system_prompt_zh[:100]}...")
    except Exception as e:
        print(f"中文系统提示词错误: {e}")

    # 英文模板
    i18n.set_locale('en_US')
    try:
        system_prompt_en = get_file_system_prompt()
        print(f"英文系统提示词长度: {len(system_prompt_en)} 字符")
        print(f"英文系统提示词预览: {system_prompt_en[:100]}...")
    except Exception as e:
        print(f"英文系统提示词错误: {e}")

    # 测试用户提示词模板
    print("\n--- 测试用户提示词模板 ---")

    sample_change = {
        'old_path': 'test.py',
        'new_path': 'test.py',
        'diff': '@@ -1,3 +1,4 @@\n def hello():\n-    print("hello")\n+    print("hello world")\n+    return True'
    }

    try:
        user_prompt = get_file_user_prompt(sample_change)
        print(f"用户提示词长度: {len(user_prompt)} 字符")
        print(f"用户提示词预览: {user_prompt[:200]}...")
    except Exception as e:
        print(f"用户提示词错误: {e}")

    # 测试讨论内容模板
    print("\n--- 测试讨论内容模板 ---")

    sample_llm_resp = {
        'issues': ['缺少错误处理', '变量命名不规范'],
        'suggestions': ['添加try-catch块', '使用更描述性的变量名'],
        'score': 7,
        'summary': '代码质量良好，需要小幅改进',
        'model': 'gpt-4',
        'duration': 2.5
    }

    try:
        discussion_content = get_discussion_content(sample_llm_resp)
        print(f"讨论内容长度: {len(discussion_content)} 字符")
        print(f"讨论内容:\n{discussion_content}")
    except Exception as e:
        print(f"讨论内容错误: {e}")


def test_locale_switching():
    """测试语言切换功能"""
    print("\n=== 测试语言切换功能 ===")

    locales = ['zh_CN', 'en_US', 'invalid_locale']

    for locale in locales:
        print(f"\n--- 切换到 {locale} ---")
        i18n.set_locale(locale)
        current = i18n.get_locale()
        print(f"设置语言: {locale}, 实际语言: {current}")

        # 测试一些基本翻译
        test_keys = [
            'status.accepted',
            'log.gitlab_connection_failed',
            'discussion.issues_title'
        ]

        for key in test_keys:
            value = i18n.t(key)
            print(f"  {key}: {value}")


def test_file_structure():
    """测试文件结构"""
    print("\n=== 测试文件结构 ===")

    # 检查必要的文件是否存在
    required_files = [
        'i18n.py',
        'locales/zh_CN.json',
        'locales/en_US.json',
        'templates/file_system_zh_CN.j2',
        'templates/file_system_en_US.j2',
        'templates/file_user_i18n.j2',
        'templates/discussion_i18n.j2'
    ]

    for file_path in required_files:
        full_path = project_root / file_path
        exists = full_path.exists()
        status = "✓" if exists else "✗"
        print(f"{status} {file_path}")

        if not exists:
            print(f"  警告: 缺少文件 {file_path}")


def main():
    """主测试函数"""
    print("国际化功能测试")
    print("=" * 50)

    try:
        test_file_structure()
        test_i18n_basic()
        test_locale_switching()
        test_templates()

        print("\n=== 测试完成 ===")
        print("✓ 所有测试已完成")

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

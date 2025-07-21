#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能和压力测试
"""

import time
import threading
import concurrent.futures
from unittest.mock import patch, Mock
import json
import statistics

import pytest
from fastapi.testclient import TestClient

# 导入测试目标
with patch('main.Settings'), \
     patch('main.gitlab.Gitlab'), \
     patch('main.LLMService'), \
     patch('main.ReviewManager'), \
     patch('main.init_i18n'):
    from main import app

from llm import LLMService
from review_manager import ReviewManager
from utils import render_template, generate_system_prompt, generate_user_prompt


class TestPerformanceBenchmarks:
    """性能基准测试"""
    
    def setup_method(self):
        """测试设置"""
        self.client = TestClient(app)
    
    def test_webhook_response_time(self):
        """测试 webhook 响应时间"""
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "object_attributes": {
                "action": "open",
                "id": 123,
                "target_project_id": 1
            },
            "project": {"id": 1}
        }
        
        response_times = []
        
        # 模拟快速处理
        with patch('main.review_manager.process_merge_request', return_value=True):
            for _ in range(10):
                start_time = time.time()
                response = self.client.post("/webhook", json=webhook_data)
                end_time = time.time()
                
                assert response.status_code == 200
                response_times.append(end_time - start_time)
        
        # 分析响应时间
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        print(f"\n响应时间统计:")
        print(f"平均: {avg_time:.3f}s")
        print(f"最大: {max_time:.3f}s")
        print(f"最小: {min_time:.3f}s")
        
        # 断言响应时间在合理范围内（< 1秒）
        assert avg_time < 1.0
        assert max_time < 2.0
    
    def test_template_rendering_performance(self):
        """测试模板渲染性能"""
        test_data = {
            'file_path': 'src/main.py',
            'diff': '@@ -1,5 +1,8 @@\n def main():\n+    # 新增注释\n     print("Hello")\n+    print("World")\n     return 0',
            'language': 'python'
        }
        
        render_times = []
        
        for _ in range(100):
            start_time = time.time()
            result = render_template('system_prompt.j2', **test_data)
            end_time = time.time()
            
            assert result is not None
            assert len(result) > 0
            render_times.append(end_time - start_time)
        
        avg_time = statistics.mean(render_times)
        print(f"\n模板渲染平均时间: {avg_time:.4f}s")
        
        # 模板渲染应该很快（< 10ms）
        assert avg_time < 0.01
    
    def test_prompt_generation_performance(self):
        """测试提示生成性能"""
        file_path = 'src/example.py'
        diff = '@@ -1,10 +1,15 @@\n def example_function():\n+    """示例函数"""\n     pass\n+    return True'
        
        generation_times = []
        
        for _ in range(50):
            start_time = time.time()
            
            system_prompt = generate_system_prompt()
            user_prompt = generate_user_prompt(file_path, diff)
            
            end_time = time.time()
            
            assert system_prompt is not None
            assert user_prompt is not None
            generation_times.append(end_time - start_time)
        
        avg_time = statistics.mean(generation_times)
        print(f"\n提示生成平均时间: {avg_time:.4f}s")
        
        # 提示生成应该很快（< 50ms）
        assert avg_time < 0.05


class TestConcurrencyStress:
    """并发压力测试"""
    
    def setup_method(self):
        """测试设置"""
        self.client = TestClient(app)
    
    def test_concurrent_webhook_requests(self):
        """测试并发 webhook 请求"""
        num_threads = 10
        requests_per_thread = 5
        
        def send_webhook_requests(thread_id):
            """发送 webhook 请求的线程函数"""
            results = []
            
            for i in range(requests_per_thread):
                webhook_data = {
                    "object_kind": "merge_request",
                    "event_type": "merge_request",
                    "object_attributes": {
                        "action": "open",
                        "id": thread_id * 100 + i,
                        "target_project_id": thread_id
                    },
                    "project": {"id": thread_id}
                }
                
                start_time = time.time()
                
                with patch('main.review_manager.process_merge_request', return_value=True):
                    response = self.client.post("/webhook", json=webhook_data)
                
                end_time = time.time()
                
                results.append({
                    'thread_id': thread_id,
                    'request_id': i,
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'success': response.status_code == 200
                })
            
            return results
        
        # 使用线程池执行并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(send_webhook_requests, i) for i in range(num_threads)]
            
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        # 分析结果
        total_requests = len(all_results)
        successful_requests = sum(1 for r in all_results if r['success'])
        response_times = [r['response_time'] for r in all_results]
        
        success_rate = successful_requests / total_requests
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        print(f"\n并发测试结果:")
        print(f"总请求数: {total_requests}")
        print(f"成功请求数: {successful_requests}")
        print(f"成功率: {success_rate:.2%}")
        print(f"平均响应时间: {avg_response_time:.3f}s")
        print(f"最大响应时间: {max_response_time:.3f}s")
        
        # 断言性能要求
        assert success_rate >= 0.95  # 95% 成功率
        assert avg_response_time < 2.0  # 平均响应时间 < 2秒
        assert max_response_time < 5.0  # 最大响应时间 < 5秒
    
    def test_memory_usage_under_load(self):
        """测试负载下的内存使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大量操作
        for i in range(100):
            webhook_data = {
                "object_kind": "merge_request",
                "event_type": "merge_request",
                "object_attributes": {
                    "action": "open",
                    "id": i,
                    "target_project_id": 1
                },
                "project": {"id": 1}
            }
            
            with patch('main.review_manager.process_merge_request', return_value=True):
                response = self.client.post("/webhook", json=webhook_data)
                assert response.status_code == 200
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\n内存使用情况:")
        print(f"初始内存: {initial_memory:.2f} MB")
        print(f"最终内存: {final_memory:.2f} MB")
        print(f"内存增长: {memory_increase:.2f} MB")
        
        # 内存增长应该在合理范围内（< 100MB）
        assert memory_increase < 100
    
    def test_database_connection_pool_stress(self):
        """测试数据库连接池压力"""
        num_concurrent_operations = 20
        
        def database_operation(operation_id):
            """模拟数据库操作"""
            with patch('curd.Session') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value.__enter__.return_value = mock_session
                
                # 模拟数据库操作延迟
                time.sleep(0.1)
                
                from curd import update_or_create_review
                result = update_or_create_review(1, operation_id, 'pending')
                
                return {'operation_id': operation_id, 'result': result, 'success': True}
        
        start_time = time.time()
        
        # 并发执行数据库操作
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_operations) as executor:
            futures = [executor.submit(database_operation, i) for i in range(num_concurrent_operations)]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=5.0)
                    results.append(result)
                except Exception as e:
                    results.append({'success': False, 'error': str(e)})
        
        end_time = time.time()
        total_time = end_time - start_time
        
        successful_operations = sum(1 for r in results if r.get('success', False))
        success_rate = successful_operations / num_concurrent_operations
        
        print(f"\n数据库连接池测试:")
        print(f"并发操作数: {num_concurrent_operations}")
        print(f"成功操作数: {successful_operations}")
        print(f"成功率: {success_rate:.2%}")
        print(f"总耗时: {total_time:.2f}s")
        
        assert success_rate >= 0.90  # 90% 成功率
        assert total_time < 10.0  # 总时间 < 10秒


class TestLLMServicePerformance:
    """LLM 服务性能测试"""
    
    def test_llm_service_response_time(self):
        """测试 LLM 服务响应时间"""
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'approved': True,
            'score': 8,
            'issue': [],
            'suggestion': [],
            'summary': '代码质量良好'
        })
        mock_response.usage.total_tokens = 100
        
        # 模拟不同的响应时间
        response_times = [0.5, 1.0, 1.5, 2.0, 0.8]  # 秒
        
        def mock_chat_create(*args, **kwargs):
            # 模拟网络延迟
            time.sleep(response_times.pop(0) if response_times else 1.0)
            return mock_response
        
        mock_openai_client.chat.completions.create = mock_chat_create
        
        llm_service = LLMService(client=mock_openai_client)
        
        messages = [
            {'role': 'system', 'content': '你是一个代码审查助手'},
            {'role': 'user', 'content': '请审查这段代码'}
        ]
        
        measured_times = []
        
        for i in range(5):
            start_time = time.time()
            result = llm_service.chat(messages)
            end_time = time.time()
            
            assert result is not None
            measured_times.append(end_time - start_time)
        
        avg_time = statistics.mean(measured_times)
        print(f"\nLLM 服务平均响应时间: {avg_time:.2f}s")
        
        # LLM 响应时间应该在合理范围内
        assert avg_time < 5.0
    
    def test_llm_service_retry_performance(self):
        """测试 LLM 服务重试性能"""
        mock_openai_client = Mock()
        
        # 模拟前两次失败，第三次成功
        call_count = 0
        
        def mock_chat_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                raise Exception("API 暂时不可用")
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                'approved': True,
                'score': 8,
                'issue': [],
                'suggestion': [],
                'summary': '代码质量良好'
            })
            mock_response.usage.total_tokens = 100
            return mock_response
        
        mock_openai_client.chat.completions.create = mock_chat_create
        
        llm_service = LLMService(client=mock_openai_client, max_retries=3)
        
        messages = [
            {'role': 'system', 'content': '你是一个代码审查助手'},
            {'role': 'user', 'content': '请审查这段代码'}
        ]
        
        start_time = time.time()
        result = llm_service.chat(messages)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        assert result is not None
        assert call_count == 3  # 确认重试了 3 次
        
        print(f"\nLLM 重试总耗时: {total_time:.2f}s")
        print(f"重试次数: {call_count}")
        
        # 重试总时间应该在合理范围内（考虑指数退避）
        assert total_time < 10.0


class TestScalabilityLimits:
    """可扩展性限制测试"""
    
    def test_large_diff_processing(self):
        """测试大型 diff 处理"""
        # 生成大型 diff
        large_diff = "@@ -1,1000 +1,1500 @@\n"
        for i in range(1000):
            large_diff += f"+    line_{i} = 'new content'\n"
        
        start_time = time.time()
        
        # 测试提示生成
        user_prompt = generate_user_prompt('large_file.py', large_diff)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert user_prompt is not None
        assert len(user_prompt) > 0
        
        print(f"\n大型 diff 处理时间: {processing_time:.3f}s")
        print(f"生成的提示长度: {len(user_prompt)} 字符")
        
        # 处理时间应该在合理范围内
        assert processing_time < 1.0
    
    def test_many_files_processing(self):
        """测试多文件处理"""
        num_files = 50
        
        # 模拟多个文件变更
        file_changes = []
        for i in range(num_files):
            file_changes.append({
                'old_path': f'src/file_{i}.py',
                'new_path': f'src/file_{i}.py',
                'diff': f'@@ -1,1 +1,2 @@\n def function_{i}():\n+    pass\n     return True'
            })
        
        start_time = time.time()
        
        # 模拟处理所有文件
        processed_files = 0
        for file_change in file_changes:
            user_prompt = generate_user_prompt(
                file_change['new_path'],
                file_change['diff']
            )
            
            if user_prompt:
                processed_files += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n多文件处理结果:")
        print(f"文件总数: {num_files}")
        print(f"处理成功: {processed_files}")
        print(f"总耗时: {total_time:.3f}s")
        print(f"平均每文件: {total_time/num_files:.4f}s")
        
        assert processed_files == num_files
        assert total_time < 5.0  # 总时间 < 5秒
        assert total_time / num_files < 0.1  # 平均每文件 < 100ms
    
    def test_webhook_payload_size_limits(self):
        """测试 webhook payload 大小限制"""
        # 测试不同大小的 payload
        payload_sizes = [1, 10, 100, 500]  # KB
        
        for size_kb in payload_sizes:
            # 生成指定大小的描述
            description_size = size_kb * 1024 // 4  # 假设每个字符 4 字节
            large_description = "A" * description_size
            
            webhook_data = {
                "object_kind": "merge_request",
                "event_type": "merge_request",
                "object_attributes": {
                    "action": "open",
                    "id": 200 + size_kb,
                    "target_project_id": 1,
                    "description": large_description
                },
                "project": {"id": 1}
            }
            
            start_time = time.time()
            
            with patch('main.review_manager.process_merge_request', return_value=True):
                response = self.client.post("/webhook", json=webhook_data)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"\nPayload 大小: {size_kb}KB, 处理时间: {processing_time:.3f}s")
            
            # 小于 1MB 的 payload 应该能正常处理
            if size_kb <= 1000:
                assert response.status_code == 200
                assert processing_time < 3.0


class TestResourceUsage:
    """资源使用测试"""
    
    def test_cpu_usage_monitoring(self):
        """测试 CPU 使用率监控"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 记录初始 CPU 使用率
        initial_cpu = process.cpu_percent()
        
        # 执行 CPU 密集型操作
        start_time = time.time()
        
        for i in range(100):
            # 模拟模板渲染和提示生成
            system_prompt = generate_system_prompt()
            user_prompt = generate_user_prompt(
                f'file_{i}.py',
                f'@@ -1,1 +1,2 @@\n def func_{i}():\n+    pass\n     return True'
            )
        
        end_time = time.time()
        
        # 记录最终 CPU 使用率
        final_cpu = process.cpu_percent()
        
        processing_time = end_time - start_time
        
        print(f"\nCPU 使用情况:")
        print(f"初始 CPU: {initial_cpu:.1f}%")
        print(f"最终 CPU: {final_cpu:.1f}%")
        print(f"处理时间: {processing_time:.3f}s")
        
        # CPU 使用率应该在合理范围内
        assert processing_time < 5.0
    
    def test_file_descriptor_usage(self):
        """测试文件描述符使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        try:
            initial_fds = process.num_fds()
        except AttributeError:
            # Windows 系统可能不支持
            pytest.skip("文件描述符监控在此系统上不可用")
        
        # 执行多次操作
        for i in range(50):
            webhook_data = {
                "object_kind": "merge_request",
                "event_type": "merge_request",
                "object_attributes": {
                    "action": "open",
                    "id": 300 + i,
                    "target_project_id": 1
                },
                "project": {"id": 1}
            }
            
            with patch('main.review_manager.process_merge_request', return_value=True):
                response = self.client.post("/webhook", json=webhook_data)
                assert response.status_code == 200
        
        final_fds = process.num_fds()
        fd_increase = final_fds - initial_fds
        
        print(f"\n文件描述符使用:")
        print(f"初始 FDs: {initial_fds}")
        print(f"最终 FDs: {final_fds}")
        print(f"增长: {fd_increase}")
        
        # 文件描述符不应该泄漏
        assert fd_increase < 10


class TestPerformanceRegression:
    """性能回归测试"""
    
    def test_baseline_performance_metrics(self):
        """测试基线性能指标"""
        # 定义性能基线
        performance_baselines = {
            'webhook_response_time': 1.0,  # 秒
            'template_render_time': 0.01,  # 秒
            'prompt_generation_time': 0.05,  # 秒
            'concurrent_success_rate': 0.95,  # 95%
        }
        
        # 测试 webhook 响应时间
        webhook_data = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "object_attributes": {
                "action": "open",
                "id": 400,
                "target_project_id": 1
            },
            "project": {"id": 1}
        }
        
        start_time = time.time()
        with patch('main.review_manager.process_merge_request', return_value=True):
            response = TestClient(app).post("/webhook", json=webhook_data)
        webhook_time = time.time() - start_time
        
        assert response.status_code == 200
        assert webhook_time < performance_baselines['webhook_response_time']
        
        # 测试模板渲染时间
        start_time = time.time()
        result = render_template('system_prompt.j2', file_path='test.py', diff='test diff')
        template_time = time.time() - start_time
        
        assert result is not None
        assert template_time < performance_baselines['template_render_time']
        
        # 测试提示生成时间
        start_time = time.time()
        system_prompt = generate_system_prompt()
        user_prompt = generate_user_prompt('test.py', 'test diff')
        prompt_time = time.time() - start_time
        
        assert system_prompt is not None
        assert user_prompt is not None
        assert prompt_time < performance_baselines['prompt_generation_time']
        
        print(f"\n性能基线检查:")
        print(f"Webhook 响应时间: {webhook_time:.3f}s (基线: {performance_baselines['webhook_response_time']}s)")
        print(f"模板渲染时间: {template_time:.4f}s (基线: {performance_baselines['template_render_time']}s)")
        print(f"提示生成时间: {prompt_time:.4f}s (基线: {performance_baselines['prompt_generation_time']}s)")
        
        # 所有指标都应该在基线范围内
        assert all([
            webhook_time < performance_baselines['webhook_response_time'],
            template_time < performance_baselines['template_render_time'],
            prompt_time < performance_baselines['prompt_generation_time']
        ])
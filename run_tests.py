#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本

提供多种测试运行选项和报告生成功能。
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path


def run_command(cmd, description=""):
    """运行命令并处理结果"""
    if description:
        print(f"\n{'='*60}")
        print(f"执行: {description}")
        print(f"命令: {' '.join(cmd)}")
        print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n执行时间: {duration:.2f} 秒")
        
        if result.stdout:
            print("\n标准输出:")
            print(result.stdout)
        
        if result.stderr:
            print("\n标准错误:")
            print(result.stderr)
        
        if result.returncode != 0:
            print(f"\n❌ 命令执行失败，退出码: {result.returncode}")
            return False
        else:
            print(f"\n✅ 命令执行成功")
            return True
            
    except Exception as e:
        print(f"\n❌ 执行命令时发生错误: {e}")
        return False


def install_dependencies():
    """安装测试依赖"""
    print("\n🔧 安装测试依赖...")
    
    # 基础测试依赖
    test_deps = [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-mock>=3.10.0",
        "pytest-asyncio>=0.21.0",
        "pytest-xdist>=3.0.0",
        "pytest-html>=3.1.0",
        "pytest-json-report>=1.5.0",
        "pytest-benchmark>=4.0.0",
        "pytest-timeout>=2.1.0",
        "coverage>=7.0.0",
        "psutil>=5.9.0",  # 用于性能测试
    ]
    
    for dep in test_deps:
        cmd = [sys.executable, "-m", "pip", "install", dep]
        if not run_command(cmd, f"安装 {dep}"):
            print(f"⚠️  安装 {dep} 失败，继续安装其他依赖...")
    
    print("\n✅ 依赖安装完成")


def run_unit_tests(verbose=False, coverage=True):
    """运行单元测试"""
    cmd = [sys.executable, "-m", "pytest"]
    
    # 基础参数
    cmd.extend([
        "tests/test_config.py",
        "tests/test_models.py",
        "tests/test_utils.py",
        "tests/test_llm.py",
        "tests/test_curd.py",
        "-m", "not integration and not performance"
    ])
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=config",
            "--cov=models",
            "--cov=utils",
            "--cov=llm",
            "--cov=curd",
            "--cov-report=html:reports/unit_coverage",
            "--cov-report=term-missing"
        ])
    
    return run_command(cmd, "单元测试")


def run_integration_tests(verbose=False):
    """运行集成测试"""
    cmd = [sys.executable, "-m", "pytest"]
    
    cmd.extend([
        "tests/test_review_manager.py",
        "tests/test_main.py",
        "-m", "not performance"
    ])
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "--html=reports/integration_report.html",
        "--self-contained-html"
    ])
    
    return run_command(cmd, "集成测试")


def run_performance_tests(verbose=False):
    """运行性能测试"""
    cmd = [sys.executable, "-m", "pytest"]
    
    cmd.extend([
        "tests/test_performance.py",
        "-m", "performance",
        "--benchmark-only",
        "--benchmark-sort=mean",
        "--benchmark-json=reports/benchmark.json"
    ])
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "性能测试")


def run_all_tests(verbose=False, coverage=True, parallel=False):
    """运行所有测试"""
    cmd = [sys.executable, "-m", "pytest"]
    
    cmd.extend(["tests/"])
    
    if verbose:
        cmd.append("-v")
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    if coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=html:reports/full_coverage",
            "--cov-report=term-missing",
            "--cov-report=xml:reports/coverage.xml"
        ])
    
    cmd.extend([
        "--html=reports/full_report.html",
        "--self-contained-html",
        "--json-report",
        "--json-report-file=reports/test_results.json"
    ])
    
    return run_command(cmd, "完整测试套件")


def run_specific_test(test_path, verbose=False):
    """运行特定测试"""
    cmd = [sys.executable, "-m", "pytest", test_path]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, f"特定测试: {test_path}")


def run_linting():
    """运行代码检查"""
    print("\n🔍 运行代码检查...")
    
    # 检查是否安装了 linting 工具
    linting_tools = {
        "flake8": "flake8>=5.0.0",
        "black": "black>=22.0.0",
        "isort": "isort>=5.10.0",
        "mypy": "mypy>=0.991"
    }
    
    for tool, package in linting_tools.items():
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"安装 {tool}...")
            subprocess.run([sys.executable, "-m", "pip", "install", package])
    
    success = True
    
    # 运行 flake8
    if not run_command(["flake8", ".", "--max-line-length=88", "--extend-ignore=E203,W503"], "Flake8 代码检查"):
        success = False
    
    # 运行 black 检查
    if not run_command(["black", "--check", "--diff", "."], "Black 格式检查"):
        success = False
    
    # 运行 isort 检查
    if not run_command(["isort", "--check-only", "--diff", "."], "Import 排序检查"):
        success = False
    
    # 运行 mypy（可选）
    if Path("mypy.ini").exists() or Path(".mypy.ini").exists():
        run_command(["mypy", "."], "MyPy 类型检查")
    
    return success


def format_code():
    """格式化代码"""
    print("\n🎨 格式化代码...")
    
    # 安装格式化工具
    subprocess.run([sys.executable, "-m", "pip", "install", "black>=22.0.0", "isort>=5.10.0"])
    
    # 运行 black
    run_command(["black", "."], "Black 代码格式化")
    
    # 运行 isort
    run_command(["isort", "."], "Import 排序")
    
    print("\n✅ 代码格式化完成")


def generate_test_report():
    """生成测试报告摘要"""
    print("\n📊 生成测试报告摘要...")
    
    reports_dir = Path("reports")
    if not reports_dir.exists():
        print("❌ 报告目录不存在，请先运行测试")
        return
    
    print(f"\n📁 测试报告位置: {reports_dir.absolute()}")
    
    # 列出生成的报告文件
    report_files = {
        "full_report.html": "完整测试报告",
        "unit_coverage/index.html": "单元测试覆盖率报告",
        "full_coverage/index.html": "完整覆盖率报告",
        "integration_report.html": "集成测试报告",
        "benchmark.json": "性能测试结果",
        "test_results.json": "测试结果 JSON",
        "coverage.xml": "覆盖率 XML 报告"
    }
    
    print("\n📋 可用报告:")
    for file_path, description in report_files.items():
        full_path = reports_dir / file_path
        if full_path.exists():
            print(f"  ✅ {description}: {full_path}")
        else:
            print(f"  ❌ {description}: 未生成")


def setup_test_environment():
    """设置测试环境"""
    print("\n🏗️  设置测试环境...")
    
    # 创建必要的目录
    directories = ["reports", "logs", ".pytest_cache"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"  📁 创建目录: {directory}")
    
    # 设置环境变量
    test_env_vars = {
        "TESTING": "true",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": "sqlite:///:memory:"
    }
    
    for key, value in test_env_vars.items():
        os.environ[key] = value
        print(f"  🔧 设置环境变量: {key}={value}")
    
    print("\n✅ 测试环境设置完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="GitLab Code Review LLM Service 测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run_tests.py --all                    # 运行所有测试
  python run_tests.py --unit                   # 只运行单元测试
  python run_tests.py --integration            # 只运行集成测试
  python run_tests.py --performance            # 只运行性能测试
  python run_tests.py --lint                   # 运行代码检查
  python run_tests.py --format                 # 格式化代码
  python run_tests.py --install-deps           # 安装测试依赖
  python run_tests.py --test tests/test_*.py   # 运行特定测试
        """
    )
    
    # 测试类型选项
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--all", action="store_true", help="运行所有测试")
    test_group.add_argument("--unit", action="store_true", help="运行单元测试")
    test_group.add_argument("--integration", action="store_true", help="运行集成测试")
    test_group.add_argument("--performance", action="store_true", help="运行性能测试")
    test_group.add_argument("--test", type=str, help="运行特定测试文件或目录")
    
    # 工具选项
    parser.add_argument("--lint", action="store_true", help="运行代码检查")
    parser.add_argument("--format", action="store_true", help="格式化代码")
    parser.add_argument("--install-deps", action="store_true", help="安装测试依赖")
    parser.add_argument("--setup-env", action="store_true", help="设置测试环境")
    parser.add_argument("--report", action="store_true", help="生成测试报告摘要")
    
    # 运行选项
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--no-coverage", action="store_true", help="禁用覆盖率报告")
    parser.add_argument("--parallel", action="store_true", help="并行运行测试")
    
    args = parser.parse_args()
    
    # 如果没有指定任何选项，显示帮助
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    success = True
    
    try:
        # 设置测试环境
        if args.setup_env or args.all:
            setup_test_environment()
        
        # 安装依赖
        if args.install_deps:
            install_dependencies()
        
        # 格式化代码
        if args.format:
            format_code()
        
        # 代码检查
        if args.lint:
            if not run_linting():
                success = False
        
        # 运行测试
        coverage = not args.no_coverage
        
        if args.unit:
            if not run_unit_tests(args.verbose, coverage):
                success = False
        
        elif args.integration:
            if not run_integration_tests(args.verbose):
                success = False
        
        elif args.performance:
            if not run_performance_tests(args.verbose):
                success = False
        
        elif args.test:
            if not run_specific_test(args.test, args.verbose):
                success = False
        
        elif args.all:
            if not run_all_tests(args.verbose, coverage, args.parallel):
                success = False
        
        # 生成报告
        if args.report or args.all:
            generate_test_report()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        success = False
    
    except Exception as e:
        print(f"\n\n❌ 运行测试时发生错误: {e}")
        success = False
    
    # 输出最终结果
    print("\n" + "="*60)
    if success:
        print("🎉 所有操作完成成功！")
        sys.exit(0)
    else:
        print("❌ 部分操作失败，请检查上面的错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
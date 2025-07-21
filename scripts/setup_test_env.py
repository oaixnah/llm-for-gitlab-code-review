#!/usr/bin/env python3
"""
测试环境设置脚本

用于自动化设置测试环境，包括：
- 创建测试数据库
- 设置环境变量
- 初始化测试数据
- 验证环境配置
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


class TestEnvironmentSetup:
    """测试环境设置类"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.test_dir = self.project_root / "tests"
        self.scripts_dir = self.project_root / "scripts"
        self.data_dir = self.project_root / "test_data"
        self.logs_dir = self.project_root / "logs"
        self.reports_dir = self.project_root / "reports"
        
        # 确保目录存在
        for directory in [self.data_dir, self.logs_dir, self.reports_dir]:
            directory.mkdir(exist_ok=True)
    
    def check_python_version(self) -> bool:
        """检查 Python 版本"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            print(f"✅ Python 版本检查通过: {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            print(f"❌ Python 版本不符合要求: {version.major}.{version.minor}.{version.micro} (需要 >= 3.8)")
            return False
    
    def install_dependencies(self) -> bool:
        """安装依赖包"""
        try:
            print("📦 安装项目依赖...")
            
            # 升级 pip
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            # 安装 requirements.txt 中的依赖
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], 
                             check=True, capture_output=True)
                print("✅ 依赖安装完成")
            else:
                print("⚠️  requirements.txt 文件不存在，跳过依赖安装")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            return False
    
    def create_test_database(self) -> bool:
        """创建测试数据库"""
        try:
            print("🗄️  创建测试数据库...")
            
            # 创建 SQLite 测试数据库
            test_db_path = self.data_dir / "test.db"
            
            # 如果数据库已存在，先删除
            if test_db_path.exists():
                test_db_path.unlink()
            
            # 创建新的数据库连接
            conn = sqlite3.connect(str(test_db_path))
            cursor = conn.cursor()
            
            # 创建表结构
            self._create_test_tables(cursor)
            
            conn.commit()
            conn.close()
            
            print(f"✅ 测试数据库创建完成: {test_db_path}")
            return True
        except Exception as e:
            print(f"❌ 测试数据库创建失败: {e}")
            return False
    
    def _create_test_tables(self, cursor: sqlite3.Cursor) -> None:
        """创建测试表结构"""
        # Reviews 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                merge_request_iid INTEGER NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, merge_request_iid)
            )
        """)
        
        # Review Discussions 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_discussions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id INTEGER NOT NULL,
                discussion_id VARCHAR(255) NOT NULL,
                file_path VARCHAR(1000) NOT NULL,
                line_number INTEGER,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
                UNIQUE(review_id, discussion_id)
            )
        """)
        
        # Review File Records 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_file_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id INTEGER NOT NULL,
                file_path VARCHAR(1000) NOT NULL,
                change_type VARCHAR(50) NOT NULL,
                diff_content TEXT,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
                UNIQUE(review_id, file_path)
            )
        """)
        
        # Review File LLM Messages 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_file_llm_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_record_id INTEGER NOT NULL,
                message_type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_record_id) REFERENCES review_file_records(id) ON DELETE CASCADE
            )
        """)
    
    def setup_environment_variables(self) -> bool:
        """设置环境变量"""
        try:
            print("🔧 设置环境变量...")
            
            # 测试环境变量
            test_env_vars = {
                "DATABASE_URL": f"sqlite:///{self.data_dir}/test.db",
                "GITLAB_URL": "https://gitlab.test.com",
                "GITLAB_TOKEN": "test-token",
                "OPENAI_API_KEY": "test-key",
                "DEBUG": "true",
                "LOCALE": "zh_CN",
                "PYTHONPATH": str(self.project_root)
            }
            
            # 创建 .env.test 文件
            env_test_file = self.project_root / ".env.test"
            with open(env_test_file, "w", encoding="utf-8") as f:
                for key, value in test_env_vars.items():
                    f.write(f"{key}={value}\n")
            
            # 设置当前进程的环境变量
            for key, value in test_env_vars.items():
                os.environ[key] = value
            
            print(f"✅ 环境变量设置完成: {env_test_file}")
            return True
        except Exception as e:
            print(f"❌ 环境变量设置失败: {e}")
            return False
    
    def generate_test_data(self) -> bool:
        """生成测试数据"""
        try:
            print("📊 生成测试数据...")
            
            # 运行测试数据生成脚本
            generate_script = self.scripts_dir / "generate_test_data.py"
            if generate_script.exists():
                subprocess.run([sys.executable, str(generate_script)], 
                             cwd=str(self.project_root), check=True)
                print("✅ 测试数据生成完成")
            else:
                print("⚠️  测试数据生成脚本不存在，跳过数据生成")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 测试数据生成失败: {e}")
            return False
    
    def verify_test_environment(self) -> bool:
        """验证测试环境"""
        print("🔍 验证测试环境...")
        
        checks = [
            ("Python 版本", self.check_python_version),
            ("项目结构", self._check_project_structure),
            ("测试文件", self._check_test_files),
            ("配置文件", self._check_config_files),
            ("数据库连接", self._check_database_connection),
            ("导入模块", self._check_module_imports)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            try:
                if check_func():
                    print(f"✅ {check_name}: 通过")
                else:
                    print(f"❌ {check_name}: 失败")
                    all_passed = False
            except Exception as e:
                print(f"❌ {check_name}: 异常 - {e}")
                all_passed = False
        
        return all_passed
    
    def _check_project_structure(self) -> bool:
        """检查项目结构"""
        required_dirs = ["tests", "locales"]
        required_files = ["main.py", "config.py", "models.py", "utils.py", "llm.py", "curd.py", "review_manager.py"]
        
        for dir_name in required_dirs:
            if not (self.project_root / dir_name).exists():
                print(f"  缺少目录: {dir_name}")
                return False
        
        for file_name in required_files:
            if not (self.project_root / file_name).exists():
                print(f"  缺少文件: {file_name}")
                return False
        
        return True
    
    def _check_test_files(self) -> bool:
        """检查测试文件"""
        test_files = [
            "conftest.py", "test_config.py", "test_models.py", "test_utils.py",
            "test_llm.py", "test_curd.py", "test_review_manager.py", "test_main.py"
        ]
        
        for test_file in test_files:
            if not (self.test_dir / test_file).exists():
                print(f"  缺少测试文件: {test_file}")
                return False
        
        return True
    
    def _check_config_files(self) -> bool:
        """检查配置文件"""
        config_files = ["pytest.ini", "pyproject.toml"]
        
        for config_file in config_files:
            if not (self.project_root / config_file).exists():
                print(f"  缺少配置文件: {config_file}")
                return False
        
        return True
    
    def _check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            test_db_path = self.data_dir / "test.db"
            if not test_db_path.exists():
                return False
            
            conn = sqlite3.connect(str(test_db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            
            expected_tables = {"reviews", "review_discussions", "review_file_records", "review_file_llm_messages"}
            actual_tables = {table[0] for table in tables}
            
            return expected_tables.issubset(actual_tables)
        except Exception:
            return False
    
    def _check_module_imports(self) -> bool:
        """检查模块导入"""
        try:
            # 添加项目根目录到 Python 路径
            sys.path.insert(0, str(self.project_root))
            
            # 尝试导入主要模块
            import config
            import models
            import utils
            import llm
            import curd
            import review_manager
            
            return True
        except ImportError as e:
            print(f"  导入错误: {e}")
            return False
    
    def run_sample_tests(self) -> bool:
        """运行示例测试"""
        try:
            print("🧪 运行示例测试...")
            
            # 运行一个简单的测试来验证环境
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_config.py::TestSettings::test_default_values", "-v"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ 示例测试通过")
                return True
            else:
                print(f"❌ 示例测试失败:\n{result.stdout}\n{result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 运行示例测试时出错: {e}")
            return False
    
    def cleanup_test_environment(self) -> None:
        """清理测试环境"""
        print("🧹 清理测试环境...")
        
        # 清理测试数据库
        test_db_path = self.data_dir / "test.db"
        if test_db_path.exists():
            test_db_path.unlink()
            print("  已删除测试数据库")
        
        # 清理日志文件
        if self.logs_dir.exists():
            for log_file in self.logs_dir.glob("*.log"):
                log_file.unlink()
            print("  已清理日志文件")
        
        # 清理报告文件
        if self.reports_dir.exists():
            for report_file in self.reports_dir.glob("*"):
                if report_file.is_file():
                    report_file.unlink()
            print("  已清理报告文件")
        
        print("✅ 测试环境清理完成")
    
    def setup_complete_environment(self) -> bool:
        """完整的环境设置"""
        print("🚀 开始设置测试环境...\n")
        
        steps = [
            ("检查 Python 版本", self.check_python_version),
            ("安装依赖", self.install_dependencies),
            ("创建测试数据库", self.create_test_database),
            ("设置环境变量", self.setup_environment_variables),
            ("生成测试数据", self.generate_test_data),
            ("验证测试环境", self.verify_test_environment),
            ("运行示例测试", self.run_sample_tests)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                print(f"\n❌ 测试环境设置失败，停止在: {step_name}")
                return False
        
        print("\n🎉 测试环境设置完成！")
        print("\n📝 接下来你可以运行:")
        print("   python run_tests.py --unit          # 运行单元测试")
        print("   python run_tests.py --integration   # 运行集成测试")
        print("   python run_tests.py --all           # 运行所有测试")
        
        return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试环境设置脚本")
    parser.add_argument("--cleanup", action="store_true", help="清理测试环境")
    parser.add_argument("--verify-only", action="store_true", help="仅验证环境")
    parser.add_argument("--project-root", help="项目根目录路径")
    
    args = parser.parse_args()
    
    setup = TestEnvironmentSetup(args.project_root)
    
    if args.cleanup:
        setup.cleanup_test_environment()
    elif args.verify_only:
        if setup.verify_test_environment():
            print("\n✅ 测试环境验证通过")
            sys.exit(0)
        else:
            print("\n❌ 测试环境验证失败")
            sys.exit(1)
    else:
        if setup.setup_complete_environment():
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
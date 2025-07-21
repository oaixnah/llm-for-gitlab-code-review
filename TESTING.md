# 测试指南

本项目包含了完整的测试框架，支持单元测试、集成测试、性能测试等多种测试类型。

## 测试结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # pytest 配置和共享 fixtures
├── test_config.py           # 配置模块测试
├── test_models.py           # 数据模型测试
├── test_utils.py            # 工具函数测试
├── test_llm.py              # LLM 服务测试
├── test_curd.py             # 数据库操作测试
├── test_review_manager.py   # 代码审查管理器测试
├── test_main.py             # 主应用测试
└── test_performance.py      # 性能测试
```

## 快速开始

### 1. 安装依赖

```bash
# 安装所有依赖（包括测试依赖）
uv pip install -r requirements.txt

# 或者使用测试脚本安装
python run_tests.py --install-deps
```

### 2. 设置测试环境

```bash
# 创建测试环境配置
python run_tests.py --setup-env

# 或者手动复制环境配置
cp .env.example .env.test
```

### 3. 运行测试

```bash
# 运行所有测试
python run_tests.py --all

# 运行单元测试
python run_tests.py --unit

# 运行集成测试
python run_tests.py --integration

# 运行性能测试
python run_tests.py --performance

# 运行特定测试文件
pytest tests/test_config.py -v

# 运行特定测试方法
pytest tests/test_config.py::TestSettings::test_default_values -v
```

## 测试类型

### 单元测试 (Unit Tests)

单元测试专注于测试单个函数或类的功能，使用 mock 来隔离外部依赖。

**标记**: `@pytest.mark.unit`

**示例**:
```python
@pytest.mark.unit
def test_settings_default_values():
    """测试设置的默认值"""
    settings = Settings()
    assert settings.debug is False
    assert settings.locale == "zh_CN"
```

### 集成测试 (Integration Tests)

集成测试验证多个组件之间的交互，使用真实的数据库和服务。

**标记**: `@pytest.mark.integration`

**示例**:
```python
@pytest.mark.integration
@pytest.mark.database
async def test_complete_review_workflow(db_session, mock_gitlab_client):
    """测试完整的代码审查工作流"""
    # 测试完整的端到端流程
```

### 性能测试 (Performance Tests)

性能测试评估系统的响应时间、吞吐量和资源使用情况。

**标记**: `@pytest.mark.performance`

**示例**:
```python
@pytest.mark.performance
def test_webhook_response_time(benchmark):
    """测试 webhook 响应时间"""
    result = benchmark(process_webhook, sample_payload)
    assert result is not None
```

## 测试配置

### pytest.ini

项目使用 `pytest.ini` 文件进行配置：

- **测试发现**: 自动发现 `tests/` 目录下的测试
- **标记**: 定义了 unit、integration、performance 等标记
- **覆盖率**: 要求最低 80% 的代码覆盖率
- **超时**: 设置测试超时时间
- **报告**: 生成 HTML 和 XML 格式的测试报告

### 环境变量

测试使用以下环境变量：

```bash
# 测试数据库
TEST_DATABASE_URL=sqlite:///test.db

# 模拟服务
TEST_GITLAB_URL=https://gitlab.test.com
TEST_GITLAB_TOKEN=test-token
TEST_OPENAI_API_KEY=test-key

# 测试配置
DEBUG=true
LOCALE=zh_CN
```

## 测试工具

### Fixtures

项目提供了丰富的 fixtures 来简化测试编写：

- `mock_settings`: 模拟应用设置
- `db_session`: 数据库会话
- `mock_gitlab_client`: 模拟 GitLab 客户端
- `mock_llm_service`: 模拟 LLM 服务
- `sample_merge_request`: 示例合并请求数据

### Mock 对象

使用 `pytest-mock` 和 `responses` 库来模拟外部依赖：

```python
# 模拟 HTTP 请求
@responses.activate
def test_api_call():
    responses.add(
        responses.GET,
        "https://api.example.com/data",
        json={"status": "success"},
        status=200
    )
```

### 数据工厂

使用 `factory-boy` 创建测试数据：

```python
class ReviewFactory(factory.Factory):
    class Meta:
        model = Review
    
    project_id = factory.Sequence(lambda n: n)
    merge_request_iid = factory.Sequence(lambda n: n)
    status = "pending"
```

## 持续集成

### GitHub Actions

项目配置了 GitHub Actions 工作流 (`.github/workflows/tests.yml`)：

- **多版本测试**: Python 3.8-3.11
- **并行执行**: 单元测试和集成测试并行运行
- **代码质量**: 运行 linting 和安全检查
- **覆盖率报告**: 上传到 Codecov
- **性能基准**: 运行性能测试并生成报告

### Docker 测试

使用 Docker 进行隔离测试：

```bash
# 运行测试容器
docker-compose --profile testing up test

# 运行性能测试
docker-compose --profile performance up performance
```

## 最佳实践

### 1. 测试命名

- 使用描述性的测试名称
- 遵循 `test_<功能>_<场景>_<期望结果>` 格式
- 使用中文注释说明测试目的

### 2. 测试组织

- 每个模块对应一个测试文件
- 使用测试类组织相关测试
- 合理使用 fixtures 避免重复代码

### 3. 断言

- 使用具体的断言而不是通用的 `assert True`
- 提供有意义的错误消息
- 测试边界条件和异常情况

### 4. Mock 使用

- 只 mock 外部依赖，不 mock 被测试的代码
- 验证 mock 的调用参数和次数
- 使用 `patch` 装饰器或上下文管理器

### 5. 数据管理

- 每个测试使用独立的数据
- 测试后清理数据
- 使用事务回滚保证测试隔离

## 故障排除

### 常见问题

1. **数据库连接错误**
   ```bash
   # 检查数据库配置
   python -c "from config import Settings; print(Settings().database_url)"
   ```

2. **导入错误**
   ```bash
   # 检查 PYTHONPATH
   export PYTHONPATH=$PWD:$PYTHONPATH
   ```

3. **测试超时**
   ```bash
   # 增加超时时间
   pytest --timeout=60 tests/
   ```

### 调试技巧

1. **使用 pdb 调试**
   ```python
   import pdb; pdb.set_trace()
   ```

2. **查看详细输出**
   ```bash
   pytest -v -s tests/test_specific.py
   ```

3. **只运行失败的测试**
   ```bash
   pytest --lf
   ```

## 贡献指南

### 添加新测试

1. 在相应的测试文件中添加测试方法
2. 使用适当的标记 (`@pytest.mark.unit` 等)
3. 添加清晰的文档字符串
4. 确保测试通过并且覆盖率不降低

### 更新测试

1. 修改代码后及时更新相关测试
2. 确保所有测试仍然通过
3. 更新测试文档如有必要

### 性能测试

1. 为新功能添加性能基准测试
2. 监控性能回归
3. 优化慢速测试

## 参考资源

- [pytest 官方文档](https://docs.pytest.org/)
- [pytest-asyncio 文档](https://pytest-asyncio.readthedocs.io/)
- [factory-boy 文档](https://factoryboy.readthedocs.io/)
- [responses 文档](https://github.com/getsentry/responses)
# LLM for GitLab Code Review

一个基于大语言模型（LLM）的 GitLab 代码审查自动化工具，能够智能分析代码变更并提供专业的审查意见。

## 功能特性

- 🤖 **智能代码审查**: 基于大语言模型自动分析代码变更，提供专业的审查意见
- 🔄 **GitLab 集成**: 通过 Webhook 自动响应合并请求事件
- 📊 **多维度评估**: 提供代码质量评分、问题识别、改进建议等
- 🌐 **多语言支持**: 支持 40+ 种编程语言和框架
- 🌍 **国际化支持**: 支持中文和英文界面，可通过环境变量配置
- 💾 **数据持久化**: 使用 MySQL 存储审查记录和历史数据
- 🚀 **高性能**: 支持并发处理，异步任务队列
- 🐳 **容器化部署**: 提供 Docker 和 Docker Compose 部署方案

## 支持的编程语言

本工具支持广泛的编程语言和技术栈，包括但不限于：

- **后端语言**: Python, Java, Go, C/C++, C#, Rust, PHP, Ruby
- **前端技术**: JavaScript, TypeScript, HTML, CSS, Vue, React
- **移动开发**: Swift, Objective-C, Kotlin, Dart (Flutter)
- **小程序**: 微信、支付宝、抖音、快手、百度小程序
- **配置文件**: JSON, YAML, XML, Makefile

详细支持列表请查看 [support_language.md](SUPPORTED_LANGUAGES.md)

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitLab        │    │   LLM Service   │    │   MySQL         │
│   Webhook       │───▶│   FastAPI App   │───▶│   Database      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   LLM API       │
                       │   (OpenAI等)    │
                       └─────────────────┘
```

## 快速开始

### 环境要求

- Python 3.13+
- MySQL 5.7+
- GitLab 实例（支持 Webhook）
- LLM API 服务（OpenAI 兼容）

### 安装部署

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/llm-for-gitlab-code-review.git
cd llm-for-gitlab-code-review
```

#### 2. 环境配置

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下参数：

```env
# GitLab 配置
GITLAB_URL=https://your-gitlab.com
GITLAB_TOKEN=your-gitlab-token
GITLAB_WEBHOOK_SECRET=your-webhook-secret
GITLAB_BOT_USERNAME=your-bot-username

# MySQL 配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=llm_code_review
MYSQL_USER=your-username
MYSQL_PASSWD=your-password

# LLM 配置
LLM_API_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key
LLM_API_TYPE=openai
LLM_MODEL=gpt-4

# 国际化配置
# 支持的语言: zh_CN (中文), en_US (英文)
LOCALE=zh_CN

# 调试模式
DEBUG=false
```

#### 3. 使用 Docker Compose 部署（推荐）

```bash
docker-compose up -d
```

#### 4. 手动部署

```bash
# 安装依赖
uv sync

# 初始化数据库
uv run python -c "from models import Base; from config import engine; Base.metadata.create_all(engine)"

# 启动服务
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### GitLab 配置

1. 在 GitLab 项目中添加 Webhook：
    - URL: `http://your-server:8000/`
    - Secret Token: 与环境变量中的 `GITLAB_WEBHOOK_SECRET` 一致
    - 触发事件: 选择 "Merge request events"

2. 确保机器人用户具有项目的 Developer 或更高权限

## API 接口

### Webhook 接收端点

```
POST /
```

接收 GitLab Webhook 事件，自动处理合并请求的代码审查。

### 健康检查

```
HEAD /health/
```

用于服务健康状态检查。

## 配置说明

### 国际化配置

本项目支持多语言界面，目前支持以下语言：

- **中文 (zh_CN)**: 默认语言
- **英文 (en_US)**: 英文界面

#### 语言切换

通过设置环境变量 `LOCALE` 来切换界面语言：

```bash
# 使用中文界面（默认）
LOCALE=zh_CN

# 使用英文界面
LOCALE=en_US
```

#### 添加新语言

如需添加新的语言支持：

1. 在 `locales/` 目录下创建新的语言文件，如 `ja_JP.json`
2. 参考现有的 `zh_CN.json` 或 `en_US.json` 文件结构进行翻译
3. 在 `templates/` 目录下创建对应的模板文件，如 `file_system_ja_JP.j2`
4. 重启服务即可生效

### 环境变量

| 变量名                     | 说明               | 默认值    |
|-------------------------|------------------|--------|
| `GITLAB_URL`            | GitLab 实例地址      | -      |
| `GITLAB_TOKEN`          | GitLab API Token | -      |
| `GITLAB_WEBHOOK_SECRET` | Webhook 密钥       | -      |
| `GITLAB_BOT_USERNAME`   | 机器人用户名           | -      |
| `MYSQL_HOST`            | MySQL 主机地址       | -      |
| `MYSQL_PORT`            | MySQL 端口         | -      |
| `MYSQL_DATABASE`        | 数据库名称            | -      |
| `MYSQL_USER`            | 数据库用户名           | -      |
| `MYSQL_PASSWD`          | 数据库密码            | -      |
| `LLM_API_URL`           | LLM API 地址       | -      |
| `LLM_API_KEY`           | LLM API 密钥       | -      |
| `LLM_API_TYPE`          | LLM API 类型       | openai |
| `LLM_MODEL`             | LLM 模型名称         | -      |
| `LOCALE`                | 界面语言             | zh_CN  |
| `DEBUG`                 | 调试模式             | false  |

## 开发指南

### 项目结构

```
.
├── main.py              # FastAPI 应用入口
├── config.py            # 配置管理
├── models.py            # 数据库模型
├── review_manager.py    # 审查管理器
├── llm.py              # LLM 服务封装
├── utils.py            # 工具函数
├── curd.py             # 数据库操作
├── templates/          # Jinja2 模板
│   ├── discussion.j2   # 讨论内容模板
│   ├── file_system.j2  # 系统提示词模板
│   ├── file_user.j2    # 用户提示词模板
│   ├── discussion_i18n.j2      # 国际化讨论内容模板
│   ├── file_system_zh_CN.j2    # 中文系统提示词模板
│   ├── file_system_en_US.j2    # 英文系统提示词模板
│   └── file_user_i18n.j2       # 国际化用户提示词模板
├── locales/            # 国际化翻译文件
│   ├── zh_CN.json      # 中文翻译
│   └── en_US.json      # 英文翻译
├── i18n.py             # 国际化管理模块
├── docker-compose.yml  # Docker Compose 配置
├── Dockerfile          # Docker 镜像构建
└── pyproject.toml      # 项目依赖配置
```

### 本地开发

```bash
# 安装开发依赖
uv sync --dev

# 启动开发服务器
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 支持

如果您在使用过程中遇到问题，请：

1. 查看 [Issues](https://github.com/oaixnah/llm-for-gitlab-code-review/issues) 中是否有类似问题 
2. 创建新的 Issue 描述您的问题
3. 提供详细的错误信息和复现步骤

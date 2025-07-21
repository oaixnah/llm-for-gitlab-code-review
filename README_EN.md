# LLM for GitLab Code Review

An automated GitLab code review tool powered by Large Language Models (LLM) that intelligently analyzes code changes and
provides professional review feedback.

## Features

- 🤖 **Intelligent Code Review**: Automatically analyze code changes using LLM and provide professional review feedback
- 🔄 **GitLab Integration**: Automatically respond to merge request events via Webhook
- 📊 **Multi-dimensional Assessment**: Provide code quality scoring, issue identification, and improvement suggestions
- 🌐 **Multi-language Support**: Support 40+ programming languages and frameworks
- 🌍 **Internationalization**: Support Chinese and English interfaces, configurable via environment variables
- 💾 **Data Persistence**: Use MySQL to store review records and historical data
- 🚀 **High Performance**: Support concurrent processing and asynchronous task queues
- 🐳 **Containerized Deployment**: Provide Docker and Docker Compose deployment solutions
- 🧪 **Comprehensive Testing**: Complete testing framework including unit tests, integration tests, and performance tests
- 📝 **Detailed Documentation**: Provide internationalization guides, testing guides, and other detailed documentation

## Supported Programming Languages

This tool supports a wide range of programming languages and technology stacks, including but not limited to:

- **Backend Languages**: Python, Java, Go, C/C++, C#, Rust, PHP, Ruby
- **Frontend Technologies**: JavaScript, TypeScript, HTML, CSS, Vue, React
- **Mobile Development**: Swift, Objective-C, Kotlin, Dart (Flutter)
- **Mini Programs**: WeChat, Alipay, TikTok, Kuaishou, Baidu Mini Programs
- **Configuration Files**: JSON, YAML, XML, Makefile

For detailed support list, please check [support_language.md](SUPPORTED_LANGUAGES.md)

## System Architecture

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
                       │   (OpenAI etc.) │
                       └─────────────────┘
```

## Quick Start

### Requirements

- Python 3.13+
- MySQL 5.7+ or SQLite (for testing)
- GitLab instance (with Webhook support)
- LLM API service (OpenAI compatible)

### Installation & Deployment

#### 1. Clone the Project

```bash
git clone https://github.com/your-username/llm-for-gitlab-code-review.git
cd llm-for-gitlab-code-review
```

#### 2. Environment Configuration

Copy the environment variable template and configure:

```bash
cp .env.example .env
```

Edit the `.env` file and configure the following parameters:

```env
# GitLab Configuration
GITLAB_URL=https://your-gitlab.com
GITLAB_TOKEN=your-gitlab-token
GITLAB_WEBHOOK_SECRET=your-webhook-secret
GITLAB_BOT_USERNAME=your-bot-username

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=llm_code_review
MYSQL_USER=your-username
MYSQL_PASSWD=your-password

# LLM Configuration
LLM_API_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key
LLM_API_TYPE=openai
LLM_MODEL=gpt-4

# Internationalization Configuration
# Supported languages: zh_CN (Chinese), en_US (English)
LOCALE=en_US

# Debug Mode
DEBUG=false
```

#### 3. Deploy with Docker Compose (Recommended)

```bash
docker-compose up -d
```

#### 4. Manual Deployment

```bash
# Install dependencies
uv sync

# Initialize database
uv run python -c "from models import Base; from config import engine; Base.metadata.create_all(engine)"

# Start service
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### GitLab Configuration

1. Add Webhook in GitLab project:
    - URL: `http://your-server:8000/`
    - Secret Token: Same as `GITLAB_WEBHOOK_SECRET` in environment variables
    - Trigger events: Select "Merge request events"

2. Ensure the bot user has Developer or higher permissions for the project

## API Endpoints

### Webhook Receiver

```
POST /
```

Receive GitLab Webhook events and automatically handle code review for merge requests.

### Health Check

```
HEAD /health/
```

Used for service health status checking.

## Configuration

### Environment Variables

| Variable                | Description         | Default |
|-------------------------|---------------------|---------|
| `GITLAB_URL`            | GitLab instance URL | -       |
| `GITLAB_TOKEN`          | GitLab API Token    | -       |
| `GITLAB_WEBHOOK_SECRET` | Webhook secret key  | -       |
| `GITLAB_BOT_USERNAME`   | Bot username        | -       |
| `MYSQL_HOST`            | MySQL host address  | -       |
| `MYSQL_PORT`            | MySQL port          | -       |
| `MYSQL_DATABASE`        | Database name       | -       |
| `MYSQL_USER`            | Database username   | -       |
| `MYSQL_PASSWD`          | Database password   | -       |
| `LLM_API_URL`           | LLM API URL         | -       |
| `LLM_API_KEY`           | LLM API key         | -       |
| `LLM_API_TYPE`          | LLM API type        | openai  |
| `LLM_MODEL`             | LLM model name      | -       |
| `LOCALE`                | Interface language  | zh_CN   |
| `DEBUG`                 | Debug mode          | false   |

## Development Guide

### Project Structure

```
.
├── main.py              # FastAPI application entry
├── config.py            # Configuration management
├── models.py            # Database models
├── review_manager.py    # Review manager
├── llm.py              # LLM service wrapper
├── utils.py            # Utility functions
├── curd.py             # Database operations
├── templates/          # Jinja2 templates
│   ├── discussion.j2   # Discussion content template
│   ├── file_system.j2  # System prompt template
│   ├── file_user.j2    # User prompt template
│   ├── discussion_i18n.j2      # Internationalized discussion template
│   ├── file_system_zh_CN.j2    # Chinese system prompt template
│   ├── file_system_en_US.j2    # English system prompt template
│   └── file_user_i18n.j2       # Internationalized user prompt template
├── locales/            # Internationalization translation files
│   ├── zh_CN.json      # Chinese translations
│   └── en_US.json      # English translations
├── i18n.py             # Internationalization management module
├── docker-compose.yml  # Docker Compose configuration
├── Dockerfile          # Docker image build
└── pyproject.toml      # Project dependency configuration
```

### Local Development

```bash
# Install development dependencies
uv sync --dev

# Start development server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

The project includes a comprehensive testing framework supporting multiple test types:

```bash
# Run all tests
python run_tests.py --all

# Run unit tests
python run_tests.py --unit

# Run integration tests
python run_tests.py --integration

# Run performance tests
python run_tests.py --performance

# Run specific tests with pytest
pytest tests/test_config.py -v
```

For detailed testing guide, please see [TESTING.md](TESTING.md)

## Contributing

1. Fork this project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Documentation

- [Internationalization Guide](INTERNATIONALIZATION_EN.md) - Multi-language interface configuration and usage
- [Testing Guide](TESTING.md) - Complete testing framework usage instructions
- [Supported Languages](SUPPORTED_LANGUAGES_EN.md) - Detailed programming language support list

## Support

If you encounter any issues while using this tool, please:

1. Check the relevant documentation and [Issues](https://github.com/oaixnah/llm-for-gitlab-code-review/issues) for similar problems
2. Create a new Issue describing your problem
3. Provide detailed error information and reproduction steps

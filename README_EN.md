# LLM for GitLab Code Review

An automated GitLab code review tool powered by Large Language Models (LLM) that intelligently analyzes code changes and
provides professional review feedback.

## Features

- 🤖 **Intelligent Code Review**: Automatically analyze code changes using LLM and provide professional review feedback
- 🔄 **GitLab Integration**: Automatically respond to merge request events via Webhook
- 📊 **Multi-dimensional Assessment**: Provide code quality scoring, issue identification, and improvement suggestions
- 🌐 **Multi-language Support**: Support 40+ programming languages and frameworks
- 💾 **Data Persistence**: Use MySQL to store review records and historical data
- 🚀 **High Performance**: Support concurrent processing and asynchronous task queues
- 🐳 **Containerized Deployment**: Provide Docker and Docker Compose deployment solutions

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
- MySQL 5.7+
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
pip install -r requirements.txt

# Initialize database
python -c "from models import Base; from config import engine; Base.metadata.create_all(engine)"

# Start service
uvicorn main:app --host 0.0.0.0 --port 8000
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
│   └── file_user.j2    # User prompt template
├── docker-compose.yml  # Docker Compose configuration
├── Dockerfile          # Docker image build
└── pyproject.toml      # Project dependency configuration
```

### Local Development

```bash
# Install development dependencies
pip install -e .

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Contributing

1. Fork this project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues while using this tool, please:

1. Check if there are similar issues in [Issues](https://github.com/your-username/llm-for-gitlab-code-review/issues)
2. Create a new Issue describing your problem
3. Provide detailed error information and reproduction steps

## Changelog

### v0.1.0

- Initial release
- Support basic code review functionality
- GitLab Webhook integration
- Support multiple programming languages
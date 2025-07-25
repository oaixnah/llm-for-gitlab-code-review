# 国际化支持 (Internationalization)

本项目支持多语言界面，可以根据不同的用户需求提供中文和英文的代码审查服务。

## 支持的语言

- **中文 (zh_CN)**: 默认语言，提供完整的中文界面
- **英文 (en_US)**: 英文界面，适合国际化团队使用

## 配置方法

### 1. 环境变量配置

在 `.env` 文件中设置 `LOCALE` 变量：

```env
# 使用中文界面（默认）
LOCALE=zh_CN

# 使用英文界面
LOCALE=en_US
```

### 2. Docker 环境配置

在 `docker-compose.yml` 中添加环境变量：

```yaml
services:
  app:
    environment:
      - LOCALE=en_US
```

### 3. 运行时配置

也可以在启动时通过环境变量指定：

```bash
LOCALE=en_US uvicorn main:app --host 0.0.0.0 --port 8000
```

## 功能覆盖

国际化支持覆盖以下功能模块：

### 1. 代码审查提示词
- 系统提示词模板
- 用户提示词模板
- 审查标准和评估维度

### 2. 审查结果展示
- 问题描述
- 改进建议
- 评分总结
- 自动生成的评论

### 3. 日志消息
- 系统运行日志
- 错误信息提示
- 状态更新消息

### 4. API 响应
- Webhook 响应消息
- 状态码描述
- 错误信息

## 示例对比

### 中文界面 (zh_CN)

**代码审查评论：**
```
#### ⚠️ 发现的问题

缺少错误处理机制

#### 💡 改进建议

建议添加try-catch块进行异常处理

#### 📝 总结

**评分**: 7/10。代码逻辑清晰，需要完善错误处理

---

*此评论由 gpt-4 自动生成（耗时：2.3s）。*
```

**日志消息：**
```
合并请求 project/repo (!123) open 开始处理
合并请求 project/repo (!123) 开始代码评审，共 5 个文件
```

### 英文界面 (en_US)

**代码审查评论：**
```
#### ⚠️ Issues Found

Missing error handling mechanism

#### 💡 Improvement Suggestions

Recommend adding try-catch blocks for exception handling

#### 📝 Summary

**Score**: 7/10. Clear code logic, need to improve error handling

---

*This comment was automatically generated by gpt-4 (Duration: 2.3s).*
```

**日志消息：**
```
Merge request project/repo (!123) open started processing
Merge request project/repo (!123) started code review, 5 files total
```

## 添加新语言

如果需要添加新的语言支持，请按照以下步骤操作：

### 1. 创建翻译文件

在 `locales/` 目录下创建新的语言文件，例如 `ja_JP.json`：

```json
{
  "system": {
    "prompt": {
      "title": "あなたは専門的なコードレビューアシスタントです...",
      "aspects": {
        "quality": "**コード品質**: コードスタイル、命名規則、コメント品質をチェック",
        ...
      }
    }
  },
  ...
}
```

### 2. 创建模板文件

在 `templates/` 目录下创建对应的模板文件：

- `file_system_ja_JP.j2`: 日文系统提示词模板
- 其他模板文件可以继续使用国际化版本

### 3. 测试新语言

设置环境变量并重启服务：

```bash
LOCALE=ja_JP uvicorn main:app --reload
```

## 技术实现

### 核心组件

1. **i18n.py**: 国际化管理模块
   - 翻译文件加载
   - 语言切换
   - 文本翻译

2. **locales/**: 翻译文件目录
   - JSON 格式的翻译文件
   - 支持嵌套键值结构
   - 模板变量支持

3. **templates/**: 模板文件目录
   - Jinja2 模板引擎
   - 国际化模板支持
   - 动态语言选择

### 翻译键命名规范

- 使用点号分隔的层级结构
- 模块名.功能名.具体项
- 例如：`log.mr_action_start`, `system.prompt.title`

### 模板变量支持

翻译文本支持 Python 格式化字符串：

```json
{
  "log": {
    "mr_action_start": "合并请求 {project} (!{iid}) {action} 开始处理"
  }
}
```

使用时传入变量：

```python
i18n.t('log.mr_action_start', project='repo', iid=123, action='open')
```

## 最佳实践

1. **保持翻译一致性**: 相同概念在不同位置使用相同的翻译
2. **考虑文化差异**: 不同语言的表达习惯可能不同
3. **测试完整性**: 确保所有功能在不同语言下都能正常工作
4. **文档同步**: 更新功能时同步更新所有语言的翻译
5. **回退机制**: 当翻译缺失时，系统会自动回退到默认语言或显示键名

## 故障排除

### 常见问题

1. **翻译不生效**
   - 检查 `LOCALE` 环境变量设置
   - 确认翻译文件格式正确
   - 重启服务

2. **部分文本未翻译**
   - 检查翻译文件中是否包含对应的键
   - 确认键名拼写正确
   - 查看日志中的警告信息

3. **模板渲染错误**
   - 检查模板文件语法
   - 确认变量名称正确
   - 查看详细错误日志

### 调试方法

启用调试模式查看详细信息：

```bash
DEBUG=true LOCALE=en_US uvicorn main:app --reload
```

这将输出详细的国际化处理日志，帮助定位问题。
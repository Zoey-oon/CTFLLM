# CTF Agent Prompt Registry

## 概述

Prompt Registry是CTF Agent的集中化prompt管理系统，支持基于文件的可版本化prompt管理。

## 目录结构

```
src/prompts/
├── __init__.py
├── prompt_registry.py          # 核心注册器类
├── README.md                   # 本文档
└── templates/                  # Prompt模板文件
    ├── system/                 # 系统级prompt
    │   └── agent_system.txt    # Agent系统prompt
    ├── challenge/              # 挑战类型prompt
    │   ├── cryptography.txt
    │   ├── web_exploitation.txt
    │   ├── reverse_engineering.txt
    │   ├── forensics.txt
    │   ├── binary_exploitation.txt
    │   ├── general_skills.txt
    │   └── initial_suffix.txt   # 初始挑战prompt后缀
    ├── continue/               # 继续对话prompt
    │   ├── standard.txt
    │   └── show_all_flags.txt
    ├── verification/           # 验证prompt
    │   └── final_answer.txt
    └── tool/                   # 工具描述prompt
        ├── code_executor.txt
        ├── file_reader.txt
        └── task_tree.txt
```

## 核心类型

### PromptType枚举
- `SYSTEM`: 系统级prompt
- `CHALLENGE`: 挑战类型prompt
- `CONTINUE`: 继续对话prompt
- `TOOL`: 工具描述prompt
- `VERIFICATION`: 验证prompt

### ChallengeType枚举
- `CRYPTOGRAPHY`: 密码学
- `WEB`: Web安全
- `REVERSE`: 逆向工程
- `FORENSICS`: 取证
- `GENERAL`: 通用技能
- `BINARY`: 二进制漏洞利用

## 使用方法

### 基本用法

```python
from src.prompts import PromptRegistry

# 创建注册器实例
registry = PromptRegistry()

# 获取系统prompt
system_prompt = registry.get_system_prompt()

# 获取挑战prompt
challenge_data = {"title": "Test", "description": "...", "files": ["file1"]}
challenge_prompt = registry.get_challenge_prompt("Cryptography", challenge_data)

# 获取继续对话prompt
context = {"title": "Test", "category": "Cryptography"}
continue_prompt = registry.get_continue_prompt(context, tool_results=["result1"])
```

### 模板变量

在prompt模板中可以使用以下变量：

- `{challenge_name}`: 挑战名称
- `{challenge_description}`: 挑战描述
- `{challenge_category}`: 挑战类别
- `{files_list}`: 文件列表（格式化）
- `{task_summary}`: 任务摘要
- `{goal}`: 目标描述
- `{results}`: 工具执行结果（用于continue prompt）

### 自定义Prompt

1. **创建新的prompt文件**：
   在相应的模板目录下创建`.txt`文件

2. **使用模板变量**：
   在文件中使用`{variable_name}`格式的变量

3. **重新加载prompt**：
   ```python
   registry.reload_prompts()  # 清除缓存并重新加载
   ```

## 版本化

- 所有prompt文件都存储在Git仓库中，支持版本控制
- 可以通过Git追踪prompt的变更历史
- 支持分支和标签管理不同版本的prompt

## 最佳实践

1. **保持模块化**：每种类型的prompt分别管理
2. **使用清晰的变量名**：确保模板变量含义明确
3. **遵循一致的格式**：所有prompt保持一致的结构和风格
4. **测试prompt变更**：修改prompt后进行充分测试
5. **文档化**：记录重要的prompt变更原因和影响

## 迁移指南

从旧的硬编码prompt系统迁移：

1. **识别现有prompt**：找出代码中所有硬编码的prompt字符串
2. **分类归档**：按照prompt类型将其归档到相应的模板文件
3. **更新代码引用**：将硬编码改为registry调用
4. **测试验证**：确保迁移后功能正常

## 故障排除

### 常见问题

1. **模板文件不存在**：
   - 系统会自动创建默认模板
   - 检查文件路径和权限

2. **变量替换失败**：
   - 检查变量名拼写
   - 确认context数据完整

3. **缓存问题**：
   - 调用`reload_prompts()`清除缓存
   - 重启应用程序

### 调试模式

```python
# 查看可用的prompt列表
available = registry.list_available_prompts()
print(available)

# 直接加载prompt文件内容
content = registry._load_prompt(PromptType.SYSTEM, "agent_system")
print(content)
```

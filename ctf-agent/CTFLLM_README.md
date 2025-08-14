# CTF Agent LLM Integration

## 概述
CTF Agent现在集成了多种LLM（大语言模型）服务，支持交互式选择和配置，可以自动分析和解决CTF题目。

## 支持的LLM服务

### 1. **DeepSeek** (推荐)
- **模型**: deepseek-chat, deepseek-coder
- **特点**: 优秀的代码理解和CTF解题能力
- **API**: https://api.deepseek.com/v1

### 2. **OpenAI GPT**
- **模型**: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- **特点**: 强大的推理和解题能力
- **API**: https://api.openai.com/v1

### 3. **Anthropic Claude**
- **模型**: claude-3-opus, claude-3-sonnet, claude-3-haiku
- **特点**: 优秀的逻辑推理和安全性
- **API**: https://api.anthropic.com/v1


## 设置步骤

### 方法1: 交互式设置（推荐）
运行程序时会自动提示你选择LLM服务和输入API密钥：

```bash
python main.py
```

### 方法2: 环境变量设置
```bash
# 选择一个LLM服务，设置对应的环境变量
export DEEPSEEK_API_KEY="your_deepseek_api_key_here"
export OPENAI_API_KEY="your_openai_api_key_here"
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
```

### 方法3: 创建.env文件
```bash
cp .env.example .env
# 编辑.env文件，填入你的API密钥
```

## 使用方法

### 运行完整流程
```bash
python main.py
```
程序会引导你：
1. 选择运行模式（Auto/HITL）
2. 输入或加载CTF题目
3. 选择LLM服务和模型
4. 输入API密钥
5. 自动解题并保存结果


## 功能特性

### 交互式配置
- **智能选择**: 自动检测可用的LLM服务
- **模型选择**: 支持选择不同的模型版本
- **API验证**: 自动验证API密钥格式
- **环境变量**: 自动检测并使用环境变量中的密钥

### 双模式支持
- **Auto Mode（自动模式）**: LLM提供完整的解题步骤
- **HITL Mode（人机协作模式）**: LLM提供指导和提示

### 智能Prompt构建
- 根据题目类型自动调整prompt内容
- 支持文件附件信息
- 根据模式调整解题深度

### 错误处理和重试
- 包含重试机制和详细的错误信息
- 支持速率限制处理
- 网络错误自动重试

## 输出文件结构
```
challenges/
└── {year}/
    └── {category}/
        └── {challenge_name}/
            ├── {challenge_name}.json              # 题目信息
            └── {challenge_name}_{mode}_solution.json  # LLM解决方案
```

## 故障排除

### API连接失败
1. **检查API密钥**: 确保密钥格式正确且有效
2. **网络连接**: 确认网络连接正常
3. **服务状态**: 检查LLM服务是否正常运行
4. **配额限制**: 确认API调用配额是否充足

### 解题质量不佳
1. **调整模型**: 尝试使用更高级的模型
2. **优化Prompt**: 检查题目描述是否清晰
3. **使用HITL模式**: 获得更好的指导而非直接答案
4. **多次尝试**: 不同模型可能有不同的解题思路

### 常见错误
- **401 Unauthorized**: API密钥无效或过期
- **429 Too Many Requests**: 达到API调用限制
- **500 Internal Server Error**: LLM服务内部错误

## 自定义配置


### 添加新的LLM服务
在`_initialize_llm_configs()`方法中添加新服务：
```python
"new_service": {
    "name": "New LLM Service",
    "api_base": "https://api.newservice.com/v1",
    "models": ["model1", "model2"],
    "default_model": "model1",
    "env_key": "NEW_SERVICE_API_KEY"
}
```

## 最佳实践

### 选择LLM服务
- **CTF解题**: 推荐DeepSeek或GPT-4
- **代码分析**: 推荐Claude或DeepSeek Coder
- **成本考虑**: 推荐DeepSeek

### 使用建议
1. 首次使用建议测试配置
2. 复杂题目建议使用HITL模式获得指导
3. 简单题目可以使用Auto模式快速获得答案
4. 定期检查API密钥的有效性和配额状态

## 更新日志
- **v1.0**: 基础LLM集成（仅DeepSeek）
- **v2.0**: 多LLM服务支持，交互式配置
- **v2.1**: 增强错误处理，支持更多模型 
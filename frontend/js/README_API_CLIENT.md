# 前端API Client 使用指南

## 概述

本项目实现了标准化的前端API Client架构，参考AIWorkFlow分支的设计模式，提供统一的API调用接口。

## 架构设计

### 文件结构
```
frontend/js/
├── api_client.js              # 基础HTTP客户端
├── services/
│   ├── session_service.js      # 会话管理服务
│   └── chat_service.js         # 聊天服务
├── modules/
│   ├── config.js              # 配置管理
│   └── chat_integration.js    # 聊天集成模块
└── README_API_CLIENT.md       # 本文档
```

### 分层架构

1. **API Client层** (`api_client.js`)
   - 基础HTTP请求封装
   - 自动注入participant_id
   - 统一错误处理

2. **Service层** (`services/`)
   - 业务逻辑封装
   - 特定功能的API调用
   - 数据格式转换

3. **Module层** (`modules/`)
   - 具体功能模块
   - 与现有页面的集成
   - 配置管理

## 核心模块

### 1. api_client.js - 基础HTTP客户端

**功能**：
- 封装POST/GET请求
- 自动注入participant_id
- 统一错误处理
- 端点解析

**使用示例**：
```javascript
import ApiClient from '/js/api_client.js';

// POST请求
const result = await ApiClient.post('/chat/ai/chat', {
  user_message: 'Hello',
  conversation_history: []
});

// GET请求
const data = await ApiClient.get('/session/status');
```

### 2. session_service.js - 会话管理

**功能**：
- 会话初始化
- participant_id管理
- 本地存储操作

**使用示例**：
```javascript
import { ensureSession, getLocalParticipantId } from '/js/services/session_service.js';

// 确保会话存在
const participantId = await ensureSession();

// 获取本地participant_id
const id = getLocalParticipantId();
```

### 3. chat_service.js - 聊天服务

**功能**：
- 发送聊天消息
- 构建对话历史
- 上下文管理

**使用示例**：
```javascript
import { sendMessage } from '/js/services/chat_service.js';

const result = await sendMessage({
  userMessage: '你好',
  conversationHistory: [],
  codeContext: { html: '', css: '', js: '' },
  taskContext: 'task:123',
  topicId: 'html-basics'
});
```

## 集成到现有页面

### 1. 在HTML中引入模块

```html
<!-- 引入API Client模块 -->
<script type="module" src="/js/api_client.js"></script>
<script type="module" src="/js/services/session_service.js"></script>
<script type="module" src="/js/services/chat_service.js"></script>
<script type="module" src="/js/modules/chat_integration.js"></script>
```

### 2. 初始化集成

```javascript
import { initChatIntegration } from '/js/modules/chat_integration.js';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
  initChatIntegration();
});
```

### 3. 替换现有代码

**之前**：
```javascript
// 直接使用fetch
const response = await fetch('/api/v1/chat/ai/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    participant_id: 'user123',
    user_message: message,
    conversation_history: []
  })
});
```

**现在**：
```javascript
// 使用API Client
const result = await sendMessage({
  userMessage: message,
  conversationHistory: []
});
```

## 核心特性

### ✅ 标准化API调用
- 统一的请求格式
- 自动错误处理
- 标准化的响应解析

### ✅ 会话管理
- 自动participant_id注入
- 会话状态检查
- 自动重定向处理

### ✅ 上下文管理
- 代码上下文收集
- 任务上下文管理
- 对话历史构建

### ✅ 错误处理
- 网络错误处理
- 服务器错误处理
- 用户友好的错误提示

## 配置选项

### 端点配置
```javascript
// 在config.js中配置端点
export const AppConfig = {
  api_base_url: "/api/v1",
  endpoints: {
    chat: '/chat/ai/chat',
    sessionInitiate: '/session/initiate'
  }
};
```

### 会话配置
```javascript
// 在session_service.js中配置
const SESSION_CONFIG = {
  storageKey: 'participant_id',
  redirectUrl: '/index.html'
};
```

## 最佳实践

### 1. 错误处理
```javascript
try {
  const result = await sendMessage(params);
  // 处理成功响应
} catch (error) {
  console.error('API调用失败:', error);
  // 显示用户友好的错误信息
}
```

### 2. 会话管理
```javascript
// 在页面初始化时确保会话存在
await ensureSession();
```

### 3. 上下文构建
```javascript
// 构建完整的聊天上下文
const chatParams = {
  userMessage: message,
  conversationHistory: getChatHistory(),
  codeContext: getCodeContext(),
  taskContext: getTaskContext(),
  topicId: getTopicId()
};
```

## 故障排除

### 常见问题

1. **模块导入错误**
   - 确保使用`type="module"`
   - 检查文件路径是否正确

2. **会话丢失**
   - 检查localStorage是否可用
   - 确认participant_id是否正确保存

3. **API调用失败**
   - 检查后端服务是否运行
   - 确认API端点正确
   - 检查网络连接

### 调试技巧

```javascript
// 启用详细日志
console.log('API Request:', requestData);
console.log('API Response:', responseData);

// 检查会话状态
console.log('Participant ID:', getLocalParticipantId());
```

## 总结

这个API Client架构提供了：

- ✅ **标准化**：统一的API调用和错误处理
- ✅ **模块化**：清晰的职责分离和接口定义
- ✅ **可维护性**：易于扩展和修改的代码结构
- ✅ **兼容性**：与现有代码无缝集成
- ✅ **开发效率**：减少重复代码，提高开发速度

通过使用这个API Client，您可以专注于业务逻辑开发，而不用担心底层的HTTP通信和错误处理细节。

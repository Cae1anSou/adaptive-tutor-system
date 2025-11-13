// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Chat With Ai 与AI进行对话 (保持原有端点以确保向后兼容)

Args:
    request: 聊天请求
    background_tasks: 后台任务处理器
    db: 数据库会话
    
Returns:
    StandardResponse[ChatResponse]: AI回复 POST /chat/ai/chat */
export async function chatWithAiChatAiChatPost(
  body: API.ChatRequest,
  options?: { [key: string]: any }
) {
  return request<API.StandardResponseChatResponse_>('/chat/ai/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  })
}

/** Chat With Ai2 与AI进行异步对话 (新端点，使用Celery任务队列)

Args:
    request: 聊天请求
    background_tasks: 后台任务处理器（保留以确保兼容性，但实际任务已委托给Celery）
    db: 数据库会话（保留以确保兼容性，但实际任务已委托给Celery）
    
Returns:
    StandardResponse[dict]: 包含任务ID的响应 POST /chat/ai/chat2 */
export async function chatWithAi2ChatAiChat2Post(
  body: API.ChatRequest,
  options?: { [key: string]: any }
) {
  return request<API.StandardResponseDict_>('/chat/ai/chat2', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  })
}

/** Get Chat Result 获取异步聊天任务的结果。

Args:
    task_id: 异步任务的ID
    
Returns:
    StandardResponse[ChatResponse]: AI回复结果 GET /chat/ai/chat2/result/${param0} */
export async function getChatResultChatAiChat2ResultTaskIdGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getChatResultChatAiChat2ResultTaskIdGetParams,
  options?: { [key: string]: any }
) {
  const { task_id: param0, ...queryParams } = params
  return request<API.StandardResponseChatResponse_>(`/chat/ai/chat2/result/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  })
}

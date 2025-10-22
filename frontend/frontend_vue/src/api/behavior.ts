// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** 记录行为事件 接收、异步持久化并异步解释单个行为事件。

- **异步持久化**: 将原始事件分派到`db_writer_queue`进行持久化。
- **异步解释**: 将事件分派到`chat_queue`进行解释和状态更新。
- **快速响应**: 立即返回 `202 Accepted`，不等待后台任务完成。 POST /api/v1/behavior/log */
export async function logBehaviorApiV1BehaviorLogPost(
  body: API.BehaviorEvent,
  options?: { [key: string]: any }
) {
  return request<any>('/api/v1/behavior/log', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  })
}

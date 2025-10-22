// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Initiate Session 初始化用户会话

Args:
    response: HTTP响应对象
    session_in: 会话初始化请求数据
    user_state_service: 用户状态服务
    db: 数据库会话
    
Returns:
    StandardResponse[SessionInitiateResponse]: 会话初始化响应 POST /api/v1/session/initiate */
export async function initiateSessionApiV1SessionInitiatePost(
  body: API.SessionInitiateRequest,
  options?: { [key: string]: any }
) {
  return request<API.StandardResponseSessionInitiateResponse_>('/api/v1/session/initiate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  })
}

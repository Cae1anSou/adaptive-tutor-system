// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Get Frontend Config 为前端应用程序提供安全、非敏感的配置变量集合。 GET /config/ */
export async function getFrontendConfigConfigGet(options?: { [key: string]: any }) {
  return request<API.StandardResponseFrontendConfig_>('/config/', {
    method: 'GET',
    ...(options || {}),
  })
}

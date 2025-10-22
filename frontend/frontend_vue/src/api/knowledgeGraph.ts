// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Get Knowledge Graph GET /api/v1/knowledge-graph */
export async function getKnowledgeGraphApiV1KnowledgeGraphGet(options?: { [key: string]: any }) {
  return request<API.StandardResponseKnowledgeGraph_>('/api/v1/knowledge-graph', {
    method: 'GET',
    ...(options || {}),
  })
}

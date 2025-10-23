// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Get Knowledge Graph GET /knowledge-graph */
export async function getKnowledgeGraphKnowledgeGraphGet(options?: { [key: string]: any }) {
  return request<API.StandardResponseKnowledgeGraph_>('/knowledge-graph', {
    method: 'GET',
    ...(options || {}),
  })
}

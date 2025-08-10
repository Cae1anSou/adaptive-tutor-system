/**
 * Knowledge Graph Service
 *
 * 提供知识图谱相关的对接函数签名
 */

import ApiClient, { resolveEndpoint } from '/js/api_client.js';
/**
 * 获取知识图谱数据（GET /api/v1/knowledge-graph）。
 * @returns {Promise<Object>} - 期望返回 KnowledgeGraph（包裹在 StandardResponse 中的 data）
 */
export async function getKnowledgeGraph() {
  const endpoint = resolveEndpoint('knowledgeGraph', '/knowledge-graph');
  const result = await ApiClient.get(endpoint);
  if (!result || typeof result !== 'object') {
    throw new Error('Invalid response');
  }
  if (Number(result.code) !== 200) {
    const msg = result.message || 'Get knowledge graph failed';
    throw new Error(msg);
  }
  return result.data;
}





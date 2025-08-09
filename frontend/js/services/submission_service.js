/**
 * Submission Service
 *
 * 提供评测提交相关的对接函数签名
 */

import ApiClient, { resolveEndpoint } from '/js/api_client.js';

/**
 * 提交评测代码（POST /api/v1/submission/submit-test 或 /api/v1/submit-test）。
 * @param {Object} payload - 提交载荷
 * @returns {Promise<Object>} - 期望返回评测结果（包裹在 StandardResponse 中的 data）
 */
export async function submitTest(payload) {
  // 端点：优先使用 endpoints.submissionSubmit，否则回退到推荐路径
  const endpoint = resolveEndpoint('submissionSubmit', '/submission/submit-test');
  const result = await ApiClient.post(endpoint, payload || {});
  if (!result || typeof result !== 'object') {
    throw new Error('Invalid response');
  }
  if (Number(result.code) !== 200) {
    const msg = result.message || 'Submit test failed';
    throw new Error(msg);
  }
  return result.data;
}


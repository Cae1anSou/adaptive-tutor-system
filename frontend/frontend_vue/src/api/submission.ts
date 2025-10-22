// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Submit Test 接收用户代码提交，进行评测，更新BKT模型，并返回结果。 POST /api/v1/submission/submit-test */
export async function submitTestApiV1SubmissionSubmitTestPost(
  body: API.TestSubmissionRequest,
  options?: { [key: string]: any }
) {
  return request<API.StandardResponseTestSubmissionResponse_>('/api/v1/submission/submit-test', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  })
}

/** Submit Test2 接收用户代码提交，异步进行评测，并返回任务ID。 POST /api/v1/submission/submit-test2 */
export async function submitTest2ApiV1SubmissionSubmitTest2Post(
  body: API.TestSubmissionRequest,
  options?: { [key: string]: any }
) {
  return request<any>('/api/v1/submission/submit-test2', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  })
}

/** Get Submission Result 获取异步代码评测任务的结果。 GET /api/v1/submission/submit-test2/result/${param0} */
export async function getSubmissionResultApiV1SubmissionSubmitTest2ResultTaskIdGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getSubmissionResultApiV1SubmissionSubmitTest2ResultTaskIdGetParams,
  options?: { [key: string]: any }
) {
  const { task_id: param0, ...queryParams } = params
  return request<API.StandardResponseTestSubmissionResponse_>(
    `/api/v1/submission/submit-test2/result/${param0}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    }
  )
}

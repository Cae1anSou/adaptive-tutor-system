// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Get User Progress GET /api/v1/progress/participants/${param0}/progress */
export async function getUserProgressApiV1ProgressParticipantsParticipantIdProgressGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getUserProgressApiV1ProgressParticipantsParticipantIdProgressGetParams,
  options?: { [key: string]: any }
) {
  const { participant_id: param0, ...queryParams } = params
  return request<API.StandardResponseUserProgressResponse_>(
    `/api/v1/progress/participants/${param0}/progress`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    }
  )
}

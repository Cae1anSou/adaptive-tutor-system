// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Get Learning Content 获取指定主题的学习材料。 GET /api/v1/learning-content/${param0} */
export async function getLearningContentApiV1LearningContentTopicIdGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getLearningContentApiV1LearningContentTopicIdGetParams,
  options?: { [key: string]: any }
) {
  const { topic_id: param0, ...queryParams } = params
  return request<API.StandardResponseLearningContent_>(`/api/v1/learning-content/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  })
}

/** Get Test Task 获取指定主题的测试任务。 GET /api/v1/test-tasks/${param0} */
export async function getTestTaskApiV1TestTasksTopicIdGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getTestTaskApiV1TestTasksTopicIdGetParams,
  options?: { [key: string]: any }
) {
  const { topic_id: param0, ...queryParams } = params
  return request<API.StandardResponseTestTask_>(`/api/v1/test-tasks/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  })
}

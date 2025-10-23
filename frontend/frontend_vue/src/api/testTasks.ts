// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Get Learning Content 获取指定主题的学习材料。 GET /learning-content/${param0} */
export async function getLearningContentLearningContentTopicIdGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getLearningContentLearningContentTopicIdGetParams,
  options?: { [key: string]: any }
) {
  const { topic_id: param0, ...queryParams } = params
  return request<API.StandardResponseLearningContent_>(`/learning-content/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  })
}

/** Get Test Task 获取指定主题的测试任务。 GET /test-tasks/${param0} */
export async function getTestTaskTestTasksTopicIdGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getTestTaskTestTasksTopicIdGetParams,
  options?: { [key: string]: any }
) {
  const { topic_id: param0, ...queryParams } = params
  return request<API.StandardResponseTestTask_>(`/test-tasks/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  })
}

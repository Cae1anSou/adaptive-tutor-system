declare namespace API {
  type ActionType = 'click' | 'type_text' | 'hover' | 'focus' | 'blur' | 'scroll' | 'wait'

  type AssertAttributeCheckpoint = {
    /** Name 检查点名称 */
    name: string
    /** 检查点类型 */
    type: CheckpointType
    /** Feedback 反馈信息 */
    feedback: string
    /** Selector CSS选择器 */
    selector: string
    /** Attribute 属性名称 */
    attribute?: string
    /** 断言类型 */
    assertion_type: AssertionType
    /** Value 期望值 */
    value?: string
  }

  type AssertElementCheckpoint = {
    /** Name 检查点名称 */
    name: string
    /** 检查点类型 */
    type: CheckpointType
    /** Feedback 反馈信息 */
    feedback: string
    /** Selector CSS选择器 */
    selector: string
    /** 断言类型 */
    assertion_type: AssertionType
    /** Value 期望值 */
    value?: string
  }

  type AssertionType =
    | 'exists'
    | 'equals'
    | 'contains'
    | 'not_equals'
    | 'not_contains'
    | 'starts_with'
    | 'ends_with'
    | 'greater_than'
    | 'less_than'
    | 'regex'
    | 'matches'

  type AssertStyleCheckpoint = {
    /** Name 检查点名称 */
    name: string
    /** 检查点类型 */
    type: CheckpointType
    /** Feedback 反馈信息 */
    feedback: string
    /** Selector CSS选择器 */
    selector: string
    /** Css Property CSS属性 */
    css_property: string
    /** 断言类型 */
    assertion_type: AssertionType
    /** Value 期望值 */
    value: string
  }

  type AssertTextContentCheckpoint = {
    /** Name 检查点名称 */
    name: string
    /** 检查点类型 */
    type: CheckpointType
    /** Feedback 反馈信息 */
    feedback: string
    /** Selector CSS选择器 */
    selector: string
    /** 断言类型 */
    assertion_type: AssertionType
    /** Value 期望值 */
    value: string
  }

  type BehaviorEvent = {
    /** Participant Id 参与者ID，用于标识特定用户 */
    participant_id: string
    /** 事件类型 */
    event_type: EventType
    /** Event Data 事件数据，根据事件类型有不同的结构 */
    event_data: Record<string, any>
    /** Timestamp 事件发生的时间戳，可选字段，默认为当前时间 */
    timestamp?: string | null
  }

  type ChatRequest = {
    /** Participant Id */
    participant_id: string
    /** User Message */
    user_message: string
    /** Conversation History */
    conversation_history?: ConversationMessage[] | null
    code_context?: CodeContent | null
    /** Mode */
    mode?: string | null
    /** Content Id */
    content_id?: string | null
    /** Test Results */
    test_results?: Record<string, any>[] | null
  }

  type ChatResponse = {
    /** Ai Response */
    ai_response: string
  }

  type CheckpointType =
    | 'assert_attribute'
    | 'assert_style'
    | 'assert_text_content'
    | 'custom_script'
    | 'interaction_and_assert'
    | 'assert_element'

  type CodeContent = {
    /** Html */
    html?: string
    /** Css */
    css?: string
    /** Js */
    js?: string
  }

  type CodePayload = {
    /** Html */
    html?: string
    /** Css */
    css?: string
    /** Js */
    js?: string
  }

  type ConversationMessage = {
    /** Role */
    role: string
    /** Content */
    content: string
    /** Timestamp */
    timestamp?: string | null
  }

  type CustomScriptCheckpoint = {
    /** Name 检查点名称 */
    name: string
    /** 检查点类型 */
    type: CheckpointType
    /** Feedback 反馈信息 */
    feedback: string
    /** Script JavaScript脚本 */
    script: string
  }

  type EventType =
    | 'code_edit'
    | 'ai_help_request'
    | 'test_submission'
    | 'dom_element_select'
    | 'user_idle'
    | 'click'
    | 'knowledge_level_access'
    | 'state_snapshot'
    | 'page_click'
    | 'significant_edits'
    | 'large_addition'
    | 'coding_problem'
    | 'coding_session_summary'
    | 'idle_hint_displayed'
    | 'page_focus_change'
    | 'test_failed'
    | 'submission_error'

  type FrontendConfig = {
    /** Api Base Url */
    api_base_url: string
    /** Backend Port */
    backend_port: number
  }

  type getChatResultChatAiChat2ResultTaskIdGetParams = {
    task_id: string
  }

  type getLearningContentLearningContentTopicIdGetParams = {
    topic_id: string
  }

  type getSubmissionResultSubmissionSubmitTest2ResultTaskIdGetParams = {
    task_id: string
  }

  type getTestTaskTestTasksTopicIdGetParams = {
    topic_id: string
  }

  type getUserProgressProgressParticipantsParticipantIdProgressGetParams = {
    participant_id: string
  }

  type HTTPValidationError = {
    /** Detail */
    detail?: ValidationError[]
  }

  type InteractionAndAssertCheckpoint = {
    /** Name 检查点名称 */
    name: string
    /** 检查点类型 */
    type: CheckpointType
    /** Feedback 反馈信息 */
    feedback: string
    /** Action Selector 动作选择器 */
    action_selector: string
    /** 动作类型 */
    action_type: ActionType
    /** Action Value 动作值 */
    action_value?: string | null
    /** Assertion 断言对象，不能再次嵌套交互脚本 */
    assertion?:
      | AssertAttributeCheckpoint
      | AssertStyleCheckpoint
      | AssertTextContentCheckpoint
      | CustomScriptCheckpoint
      | null
  }

  type KnowledgeGraph = {
    /** Nodes 节点列表 */
    nodes: KnowledgeGraphNode[]
    /** Edges 边列表 */
    edges: KnowledgeGraphEdge[]
    /** Dependent Edges 依赖边列表 */
    dependent_edges: KnowledgeGraphEdge[]
    /** Metadata 图谱元数据 */
    metadata?: Record<string, any> | null
  }

  type KnowledgeGraphEdge = {
    data: KnowledgeGraphEdgeData
  }

  type KnowledgeGraphEdgeData = {
    /** Source 源节点ID */
    source: string
    /** Target 目标节点ID */
    target: string
    /** Edge Type 边类型 */
    edge_type?: string | null
    /** Weight 边权重(0-1) */
    weight?: number | null
    /** Label 边标签 */
    label?: string | null
  }

  type KnowledgeGraphNode = {
    data: KnowledgeGraphNodeData
  }

  type KnowledgeGraphNodeData = {
    /** Id 节点唯一标识符 */
    id: string
    /** Label 节点显示标签 */
    label: string
    /** Type 节点类型 */
    type?: string | null
    /** Description 节点描述 */
    description?: string | null
    /** Difficulty 难度等级(1-5) */
    difficulty?: number | null
  }

  type LearningContent = {
    /** Topic Id 知识点ID */
    topic_id: string
    /** Title 学习内容标题 */
    title: string
    /** Levels 等级信息列表 */
    levels: LevelInfo[]
    /** Sc All 选择元素信息列表 */
    sc_all: SelectElementInfo[]
  }

  type LevelInfo = {
    /** Level 等级编号 */
    level: number
    /** Description 等级描述 */
    description: string
  }

  type SelectElementInfo = {
    /** Topic Id 主题ID */
    topic_id: string
    /** Select Element 选择元素列表 */
    select_element: string[]
  }

  type SessionInitiateRequest = {
    /** Participant Id User-provided or system-generated unique ID (UUID) for the participant */
    participant_id: string
    /** Group Assigned experiment group */
    group?: string
  }

  type SessionInitiateResponse = {
    /** Participant Id System-generated unique ID (UUID) for the participant */
    participant_id: string
    /** Is New User Whether the participant is a new user, used to determine if onboarding content should be displayed */
    is_new_user: boolean
  }

  type StandardResponseChatResponse_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    data?: ChatResponse | null
  }

  type StandardResponseDict_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    /** Data */
    data?: Record<string, any> | null
  }

  type StandardResponseFrontendConfig_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    data?: FrontendConfig | null
  }

  type StandardResponseKnowledgeGraph_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    data?: KnowledgeGraph | null
  }

  type StandardResponseLearningContent_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    data?: LearningContent | null
  }

  type StandardResponseSessionInitiateResponse_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    data?: SessionInitiateResponse | null
  }

  type StandardResponseTestSubmissionAsyncResponse_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    data?: TestSubmissionAsyncResponse | null
  }

  type StandardResponseTestSubmissionResponse_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    data?: TestSubmissionResponse | null
  }

  type StandardResponseTestTask_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    data?: TestTask | null
  }

  type StandardResponseUserProgressResponse_ = {
    /** Code */
    code?: number
    /** Message */
    message?: string
    data?: UserProgressResponse | null
  }

  type TestSubmissionAsyncResponse = {
    /** Task Id 异步评测任务的ID */
    task_id: string
  }

  type TestSubmissionRequest = {
    /** Participant Id 参与者ID */
    participant_id: string
    /** Topic Id 知识点ID */
    topic_id: string
    /** 用户提交的代码 */
    code: CodePayload
  }

  type TestSubmissionResponse = {
    /** Passed 是否所有检查点都通过 */
    passed: boolean
    /** Message 总体评测信息 */
    message: string
    /** Details 详细的失败反馈列表 */
    details: string[]
  }

  type TestTask = {
    /** Topic Id 知识点ID */
    topic_id: string
    /** Title 测试任务标题 */
    title: string
    /** Description Md 任务描述 */
    description_md: string
    /** 初始代码 */
    start_code: CodeContent
    /** Checkpoints 检查点列表 */
    checkpoints: (
      | AssertAttributeCheckpoint
      | AssertStyleCheckpoint
      | AssertTextContentCheckpoint
      | AssertElementCheckpoint
      | CustomScriptCheckpoint
      | InteractionAndAssertCheckpoint
    )[]
  }

  type UserProgressResponse = {
    /** Completed Topics */
    completed_topics: string[]
  }

  type ValidationError = {
    /** Location */
    loc: (string | number)[]
    /** Message */
    msg: string
    /** Error Type */
    type: string
  }
}

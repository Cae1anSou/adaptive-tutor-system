from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Union, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    pass


class AssertionType(str, Enum):
    """断言类型枚举"""
    EXISTS = "exists"
    EQUALS = "equals"
    CONTAINS = "contains"
    NOT_EQUALS = "not_equals"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    REGEX = "regex"
    MATCHES = "matches"


class ActionType(str, Enum):
    """动作类型枚举"""
    CLICK = "click"
    TYPE_TEXT = "type_text"
    HOVER = "hover"
    FOCUS = "focus"
    BLUR = "blur"
    SCROLL = "scroll"
    WAIT = "wait"


class CheckpointType(str, Enum):
    """检查点类型枚举"""
    ASSERT_ATTRIBUTE = "assert_attribute"
    ASSERT_STYLE = "assert_style"
    ASSERT_TEXT_CONTENT = "assert_text_content"
    CUSTOM_SCRIPT = "custom_script"
    INTERACTION_AND_ASSERT = "interaction_and_assert"
    ASSERT_ELEMENT = "assert_element"


class CodeContent(BaseModel):
    """代码内容模型
    
    用于承载完整的Web代码内容，包含HTML、CSS和JavaScript三个部分。
    
    Attributes:
        html: HTML代码内容，包含页面结构和内容
        css: CSS样式代码内容，用于页面美化
        js: JavaScript脚本代码内容，用于页面交互
    """
    html: str = ""
    css: str = ""
    js: str = ""


class LevelInfo(BaseModel):
    """等级信息模型
    
    学习内容的等级信息。
    
    Attributes:
        level: 等级编号
        description: 等级描述
    """
    level: int = Field(..., ge=1, description="等级编号")
    description: str = Field(..., min_length=1, description="等级描述")


class SelectElementInfo(BaseModel):
    """选择元素信息模型
    
    用于sc_all字段，包含主题ID和选择元素列表。
    
    Attributes:
        topic_id: 主题ID
        select_element: 选择元素列表
    """
    topic_id: str = Field(..., min_length=1, description="主题ID")
    select_element: List[str] = Field(..., min_length=0, description="选择元素列表")


class LearningContent(BaseModel):
    """学习内容模型
    
    完整的学习内容结构，包含主题信息、等级信息和选择元素信息。
    
    Attributes:
        topic_id: 知识点ID，用于标识特定的学习主题
        title: 学习内容标题
        levels: 等级信息列表
        sc_all: 选择元素信息列表
    """
    topic_id: str = Field(..., min_length=1, description="知识点ID")
    title: str = Field(..., min_length=1, description="学习内容标题")
    levels: List[LevelInfo] = Field(..., min_length=1, description="等级信息列表")
    sc_all: List[SelectElementInfo] = Field(..., description="选择元素信息列表")


class BaseCheckpoint(BaseModel):
    """检查点基类模型
    
    所有检查点类型的基类，包含通用字段。
    
    Attributes:
        name: 检查点名称，用于标识和描述检查点
        type: 检查点类型
        feedback: 反馈信息，当检查点失败时显示给用户
    """
    name: str = Field(..., min_length=1, description="检查点名称")
    type: CheckpointType = Field(..., description="检查点类型")
    feedback: str = Field(..., min_length=1, description="反馈信息")


class AssertAttributeCheckpoint(BaseCheckpoint):
    """属性断言检查点模型
    
    用于检查DOM元素的属性是否存在或属性值。
    
    Attributes:
        selector: 选择器，用于定位要检查的DOM元素
        attribute: 属性名称（可选，如果为空则检查元素是否存在）
        assertion_type: 断言方式，如 'exists' 等
        value: 期望值（用于属性值比较）
    """
    selector: str = Field(..., min_length=1, description="CSS选择器")
    attribute: str = Field("", description="属性名称")
    assertion_type: AssertionType = Field(..., description="断言类型")
    value: str = Field("", description="期望值")


class AssertStyleCheckpoint(BaseCheckpoint):
    """样式断言检查点模型
    
    用于检查DOM元素的CSS样式属性。
    
    Attributes:
        selector: 选择器，用于定位要检查的DOM元素
        css_property: CSS属性，用于检查元素的样式属性
        assertion_type: 断言方式，如 'equals', 'contains' 等
        value: 期望值，用于与实际值进行比较
    """
    selector: str = Field(..., min_length=1, description="CSS选择器")
    css_property: str = Field(..., min_length=1, description="CSS属性")
    assertion_type: AssertionType = Field(..., description="断言类型")
    value: str = Field(..., description="期望值")


class AssertTextContentCheckpoint(BaseCheckpoint):
    """文本内容断言检查点模型
    
    用于检查DOM元素的文本内容。
    
    Attributes:
        selector: 选择器，用于定位要检查的DOM元素
        assertion_type: 断言方式，如 'equals', 'contains' 等
        value: 期望值，用于与实际值进行比较
    """
    selector: str = Field(..., min_length=1, description="CSS选择器")
    assertion_type: AssertionType = Field(..., description="断言类型")
    value: str = Field(..., description="期望值")


class AssertElementCheckpoint(BaseCheckpoint):
    """元素存在断言检查点模型
    
    用于检查DOM元素的存在性。
    
    Attributes:
        selector: 选择器，用于定位要检查的DOM元素
        assertion_type: 断言方式，如 'exists' 等
        value: 期望值（用于元素文本内容比较）
    """
    selector: str = Field(..., min_length=1, description="CSS选择器")
    assertion_type: AssertionType = Field(..., description="断言类型")
    value: str = Field("", description="期望值")


class CustomScriptCheckpoint(BaseCheckpoint):
    """自定义脚本检查点模型
    
    用于执行自定义JavaScript脚本来进行复杂检查。
    
    Attributes:
        script: 要执行的JavaScript脚本
    """
    script: str = Field(..., min_length=1, description="JavaScript脚本")


class InteractionAndAssertCheckpoint(BaseCheckpoint):
    """交互和断言检查点模型
    
    用于模拟用户交互（点击、输入等）并进行断言检查。
    注意：断言对象不能再次嵌套交互脚本，只能嵌套其他类型的断言。
    
    Attributes:
        action_selector: 动作选择器，用于定位要执行动作的元素
        action_type: 动作类型，如 'click', 'type_text' 等
        action_value: 动作值（用于输入文本等）
        assertion: 断言对象，可以是除InteractionAndAssertCheckpoint外的任何检查点类型
    """
    action_selector: str = Field(..., min_length=1, description="动作选择器")
    action_type: ActionType = Field(..., description="动作类型")
    action_value: Optional[str] = Field(None, description="动作值")
    assertion: Optional[Union[
        AssertAttributeCheckpoint,
        AssertStyleCheckpoint,
        AssertTextContentCheckpoint,
        CustomScriptCheckpoint
    ]] = Field(None, description="断言对象，不能再次嵌套交互脚本")


# 更新InteractionAndAssertCheckpoint的前向引用
InteractionAndAssertCheckpoint.model_rebuild()


# 使用Union类型来表示所有可能的检查点类型
Checkpoint = Union[
    AssertAttributeCheckpoint,
    AssertStyleCheckpoint,
    AssertTextContentCheckpoint,
    AssertElementCheckpoint,
    CustomScriptCheckpoint,
    "InteractionAndAssertCheckpoint"  # 使用字符串前向引用
]


class TestTask(BaseModel):
    """测试任务模型
    
    完整的测试任务定义，包含任务描述、初始代码和检查点列表。
    
    Attributes:
        topic_id: 知识点ID，用于标识测试任务对应的知识点
        title: 测试任务标题
        description_md: 任务描述，Markdown格式的详细说明
        start_code: 初始代码，用户开始测试时的基础代码
        checkpoints: 检查点列表，包含所有需要验证的检查点
    """
    topic_id: str = Field(..., min_length=1, description="知识点ID")
    title: str = Field(..., min_length=1, description="测试任务标题")
    description_md: str = Field(..., min_length=1, description="任务描述")
    start_code: CodeContent = Field(..., description="初始代码")
    checkpoints: List[Checkpoint] = Field(..., min_length=1, description="检查点列表")
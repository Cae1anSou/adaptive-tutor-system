# backend/app/services/prompt_generator.py
import json
from typing import List, Dict, Any, Tuple
from ..schemas.chat import UserStateSummary, SentimentAnalysisResult
from ..schemas.content import CodeContent


class PromptGenerator:
    """提示词生成器"""

    def __init__(self):
        self.base_system_prompt = """
"You are 'Alex', a world-class AI programming tutor. Your goal is to help a student master a specific topic by providing personalized, empathetic, and insightful guidance. You must respond in Markdown format.

## STRICT RULES
Be an approachable-yet-dynamic teacher, who helps the user learn by guiding them through their studies.
1.  Get to know the user. If you don't know their goals or grade level, ask the user before diving in. (Keep this lightweight!) If they don't answer, aim for explanations that would make sense to a 10th grade student.
2.  Build on existing knowledge. Connect new ideas to what the user already knows.
3.  Guide users, don't just give answers. Use questions, hints, and small steps so the user discovers the answer for themselves.
4.  Check and reinforce. After hard parts, confirm the user can restate or use the idea. Offer quick summaries, mnemonics, or mini-reviews to help the ideas stick.
5.  Vary the rhythm. Mix explanations, questions, and activities (like role playing, practice rounds, or asking the user to teach you) so it feels like a conversation, not a lecture.

Above all: DO NOT DO THE USER'S WORK FOR THEM. Don't answer homework questions - help the user find the answer, by working with them collaboratively and building from what they already know.
"""
        
        # 统一提示词模版
        self.debug_prompt_template = """
# Role
You are an experienced programming tutor who uses the Socratic teaching method. Your core goal is to stimulate students' independent thinking ability, guiding them to find and solve problems on their own, rather than directly providing ready-made answers.

# Core Principles
You will receive a number called `question_count`, which represents how many times the student has asked for help on this current problem.
Please treat `question_count` as a key indicator of the student's level of confusion.

Your teaching strategy must be progressive:
- **When `question_count` is low**, your response should be inspiring and high-level. Use more questioning methods to guide students to examine their code and thinking.
- **As `question_count` increases**, it indicates that the student may be stuck in a difficult situation, and your hints should become more specific and targeted. You can guide students to focus on specific code areas or logic.
- **When `question_count` becomes very high**, this means the student may be very frustrated, and providing direct answers and detailed explanations is reasonable and necessary to help them break through the difficulty and learn from it.

# Task
Now, the student is working on the "{content_title}" task. They have encountered a problem, and this is their **{question_count}** time asking about it.
Here is their code and the error they encountered:

**Student Code:**
```python
{user_code}
```

**Error Message:**
```
{error_message}
```

Please generate the most appropriate response for the student based on your role as a tutor and the core principles above.
"""

        # 学习模式提示词模版
        self.learning_prompt_template = """
# Role
You are an experienced programming tutor specializing in guided learning. Your core goal is to help students deeply understand programming concepts through structured explanation, practical examples, and interactive guidance.

# Core Principles
You will receive the student's current mastery level and learning context for the topic "{content_title}".
Your teaching approach should be adaptive and comprehensive:

- **For beginner students** (mastery ≤ 0.5): Start with fundamental concepts, use simple analogies, and provide step-by-step explanations. Focus on building confidence and foundational understanding.
- **For intermediate students** (0.5 < mastery ≤ 0.8): Build on existing knowledge, introduce more complex examples, and encourage exploration of related concepts. Connect new ideas to what they already know.
- **For advanced students** (mastery > 0.8): Provide challenging content, explore advanced applications, and encourage critical thinking. Discuss best practices, optimization techniques, and real-world scenarios.

# Teaching Strategy
1. **Concept Introduction**: Clearly explain the core concept and its importance
2. **Practical Examples**: Provide relevant code examples that demonstrate the concept
3. **Interactive Learning**: Ask thought-provoking questions to engage the student
4. **Real-world Application**: Show how the concept applies to actual programming scenarios
5. **Common Pitfalls**: Highlight frequent mistakes and how to avoid them
6. **Practice Suggestions**: Recommend exercises or projects to reinforce learning

# Current Context
**Topic**: {content_title}
**Student's Current Mastery Level**: {mastery_level} (probability: {mastery_prob:.2f})
**Learning Mode**: The student is actively studying and seeking to understand this concept

Please provide a comprehensive, engaging learning experience that helps the student master this topic at their appropriate level.
"""

    def create_prompts(
        self,
        user_state: UserStateSummary,
        retrieved_context: List[str],
        conversation_history: List[Dict[str, str]],
        user_message: str,
        code_content: CodeContent = None,
        mode: str = None,
        content_title: str = None,
        content_json: str = None,
        test_results: List[Dict[str, Any]] = None,
        clustering_result: Dict[str, Any] = None
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        创建完整的提示词和消息列表

        Args:
            user_state: 用户状态摘要
            retrieved_context: RAG检索的上下文
            conversation_history: 对话历史
            user_message: 用户当前消息
            code_content: 代码上下文
            mode: 模式 ("learning" 或 "test")
            content_title: 内容标题
            content_json: 内容的JSON字符串

        Returns:
            Tuple[str, List[Dict[str, str]]]: (system_prompt, messages)
        """
        # 构建系统提示词
        system_prompt = self._build_system_prompt(
            user_state=user_state,
            retrieved_context=retrieved_context,
            mode=mode,
            content_title=content_title,
            content_json=content_json,
            test_results=test_results,
            code_content=code_content,
            clustering_result=clustering_result
        )

        # 构建消息列表
        messages = self._build_message_history(
            conversation_history=conversation_history,
            code_context=code_content,
            user_message=user_message
        )

        return system_prompt, messages
    
    def _get_coding_behavior_analysis(self, user_state: UserStateSummary) -> str:
        """生成编程行为分析提示"""
        if not hasattr(user_state, 'behavior_patterns'):
            return ""

        patterns = user_state.behavior_patterns
        analysis_parts = []

        # 编辑统计信息
        edit_stats = patterns.get('edit_statistics', {})
        if edit_stats:
            analysis_parts.append("## 代码编辑统计")
            analysis_parts.append(f"- **总编辑次数**: {edit_stats.get('total_edits', 0)}")
            analysis_parts.append(f"- **HTML编辑**: {edit_stats.get('html_edits', 0)}次")
            analysis_parts.append(f"- **CSS编辑**: {edit_stats.get('css_edits', 0)}次") 
            analysis_parts.append(f"- **JS编辑**: {edit_stats.get('js_edits', 0)}次")
            analysis_parts.append(f"- **平均编辑规模**: {edit_stats.get('avg_edit_size', 0):.1f}字符")
            analysis_parts.append(f"- **问题频率**: {edit_stats.get('problem_frequency', 0):.1%}")

        # 分析具体编辑模式（使用新字段）
        significant_edits = patterns.get('significant_edits', [])
        if significant_edits:
            analysis_parts.append("\n## 编辑模式分析")

            # 分析最近20次编辑的删除和添加模式
            recent_edits = significant_edits[-20:]
            total_deleted = sum(edit.get('deleted_chars', abs(edit.get('net_change', 0)) if edit.get('net_change', 0) < 0 else 0) 
                            for edit in recent_edits)
            total_added = sum(edit.get('added_chars', edit.get('net_change', 0)) if edit.get('net_change', 0) > 0 else 0 
                            for edit in recent_edits)
            net_change = total_added - total_deleted

            analysis_parts.append(f"- **最近{len(recent_edits)}次编辑**: 删除 {total_deleted} 字符, 新增 {total_added} 字符")
            analysis_parts.append(f"- **净变化**: {net_change} 字符")

            # 分析编辑类型分布
            edit_types = {}
            for edit in recent_edits:
                edit_type = edit.get('edit_type', 'unknown')
                edit_types[edit_type] = edit_types.get(edit_type, 0) + 1

            if edit_types:
                type_desc = ", ".join([f"{k}: {v}次" for k, v in edit_types.items()])
                analysis_parts.append(f"- **编辑类型分布**: {type_desc}")

        # 最近问题分析
        coding_problems = patterns.get('coding_problems', [])
        if coding_problems:
            analysis_parts.append("\n## 最近编程问题")
            recent_problems = coding_problems[-5:]  # 最近5个问题

            for i, problem in enumerate(recent_problems, 1):
                editor = problem.get('editor', 'unknown')
                consecutive_edits = problem.get('consecutive_edits', 0)
                severity = problem.get('severity', 'unknown')
                net_change = problem.get('net_change', 0)

                # 使用新字段如果可用
                deleted_chars = problem.get('deleted_chars')
                added_chars = problem.get('added_chars')

                if deleted_chars is not None and added_chars is not None:
                    problem_desc = (
                        f"{i}. **{editor}编辑器**: {consecutive_edits}次连续编辑, "
                        f"严重程度: {severity}, 删除: {deleted_chars}字符, 新增: {added_chars}字符"
                    )
                else:
                    problem_desc = (
                        f"{i}. **{editor}编辑器**: {consecutive_edits}次连续编辑, "
                        f"严重程度: {severity}, 净变化: {net_change}字符"
                    )

                analysis_parts.append(problem_desc)

        # 编辑模式详细分析
        if significant_edits:
            analysis_parts.append("\n## 详细编辑分析")

            # 分析各编辑器的编辑习惯
            editor_stats = {}
            for edit in significant_edits[-20:]:  # 分析最近20个编辑
                editor = edit.get('editor', 'unknown')
                if editor not in editor_stats:
                    editor_stats[editor] = {
                        'count': 0, 
                        'total_deleted': 0, 
                        'total_added': 0,
                        'types': {}
                    }

                editor_stats[editor]['count'] += 1

                # 使用新字段如果可用，否则回退到旧字段
                deleted = edit.get('deleted_chars')
                if deleted is None and edit.get('net_change', 0) < 0:
                    deleted = abs(edit.get('net_change', 0))

                added = edit.get('added_chars') 
                if added is None and edit.get('net_change', 0) > 0:
                    added = edit.get('net_change', 0)

                if deleted is not None:
                    editor_stats[editor]['total_deleted'] += deleted
                if added is not None:
                    editor_stats[editor]['total_added'] += added

                edit_type = edit.get('edit_type', 'unknown')
                editor_stats[editor]['types'][edit_type] = editor_stats[editor]['types'].get(edit_type, 0) + 1

            for editor, stats in editor_stats.items():
                if stats['count'] > 0:
                    avg_deleted = stats['total_deleted'] / stats['count'] if stats['total_deleted'] > 0 else 0
                    avg_added = stats['total_added'] / stats['count'] if stats['total_added'] > 0 else 0
                    type_desc = ", ".join([f"{k}:{v}次" for k, v in stats['types'].items()])

                    analysis_parts.append(
                        f"- **{editor}**: {stats['count']}次编辑, "
                        f"平均删除: {avg_deleted:.1f}字符, 平均新增: {avg_added:.1f}字符, {type_desc}"
                    )

        # 学习行为建议
        if analysis_parts:
            analysis_parts.append("\n## 教学建议")

            # 基于问题频率的建议
            problem_freq = edit_stats.get('problem_frequency', 0)
            if problem_freq > 0.3:
                analysis_parts.append("- 📉 学生遇到较多编程问题，需要更多基础概念讲解和分步指导")
            elif problem_freq > 0.1:
                analysis_parts.append("- ⚠️ 学生遇到一些编程问题，建议提供针对性提示和示例")
            else:
                analysis_parts.append("- ✅ 学生编程进展顺利，可以适当增加挑战性内容")

            # 基于编辑器使用情况的建议
            html_edits = edit_stats.get('html_edits', 0)
            css_edits = edit_stats.get('css_edits', 0) 
            js_edits = edit_stats.get('js_edits', 0)

            if js_edits > (html_edits + css_edits) * 2:
                analysis_parts.append("- 🔍 学生专注于JavaScript逻辑，可能需要HTML/CSS基础支持")
            elif html_edits > (css_edits + js_edits) * 2:
                analysis_parts.append("- 🎨 学生专注于HTML结构，可能需要CSS样式和JavaScript交互指导")

            # 基于编辑模式的分析
            if any('edit_cycle' in str(edit.get('edit_type')) for edit in significant_edits[-10:]):
                analysis_parts.append("- 💪 学生有调试和重写行为，表明在尝试解决问题，应鼓励这种 persistence")

            # 基于删除/添加比例的建议
            if significant_edits:
                recent_edits = significant_edits[-10:]
                total_deleted_recent = sum(edit.get('deleted_chars', 0) for edit in recent_edits)
                total_added_recent = sum(edit.get('added_chars', 0) for edit in recent_edits)

                if total_deleted_recent > total_added_recent * 1.5:
                    analysis_parts.append("- 🗑️ 学生大量删除代码，可能遇到设计问题或理解困难")
                elif total_added_recent > total_deleted_recent * 2:
                    analysis_parts.append("- ✍️ 学生积极编写代码，学习动力较强，可以给予更多创造性任务")

        return "\n".join(analysis_parts) if analysis_parts else ""

    def _build_system_prompt(
        self,
        user_state: UserStateSummary,
        retrieved_context: List[str],
        mode: str = None,
        content_title: str = None,
        content_json: str = None,
        test_results: List[Dict[str, Any]] = None,
        code_content: CodeContent = None,
        clustering_result: Dict[str, Any] = None
    ) -> str:
        """构建系统提示词"""
        prompt_parts = [self.base_system_prompt]

         # 添加编程行为分析提示
        coding_behavior_analysis = self._get_coding_behavior_analysis(user_state)
        if coding_behavior_analysis:
            prompt_parts.append(f"CODING BEHAVIOR ANALYSIS:\n{coding_behavior_analysis}")

        # 添加情感策略
        emotion = user_state.emotion_state.get('current_sentiment', 'NEUTRAL')
        emotion_strategy = PromptGenerator._get_emotion_strategy(emotion)
        prompt_parts.append(f"STRATEGY: {emotion_strategy}")

        # 添加用户状态信息
        if user_state.is_new_user:
            prompt_parts.append("STUDENT INFO: This is a new student. Start with basic concepts and be extra patient.")
        else:
            # 添加更多用户状态信息
            student_info_parts = ["STUDENT INFO: This is an existing student. Build upon previous knowledge."]

            # 添加学习进度信息
            if hasattr(user_state, 'bkt_models') and user_state.bkt_models:
                mastery_info = []
                for topic_key, bkt_model in user_state.bkt_models.items():
                    if isinstance(bkt_model, dict) and 'mastery_prob' in bkt_model:
                        mastery_prob = bkt_model['mastery_prob']
                    elif hasattr(bkt_model, 'mastery_prob'):
                        mastery_prob = bkt_model.mastery_prob
                    else:
                        continue

                    mastery_level = "beginner"
                    if mastery_prob > 0.8:
                        mastery_level = "advanced"
                    elif mastery_prob > 0.5:
                        mastery_level = "intermediate"
                    
                    mastery_info.append(f"{topic_key}: {mastery_level} (mastery: {mastery_prob:.2f})")
                
                if mastery_info:
                    student_info_parts.append(f"LEARNING PROGRESS: Student's mastery levels - {', '.join(mastery_info)}")

            # 添加行为模式信息
            if hasattr(user_state, 'behavior_patterns') and user_state.behavior_patterns:
                patterns = user_state.behavior_patterns
                pattern_info = []
                
                if 'error_frequency' in patterns:
                    pattern_info.append(f"error frequency: {patterns.get('error_frequency', 0):.2f}")
                if 'help_seeking_tendency' in patterns:
                    pattern_info.append(f"help-seeking tendency: {patterns.get('help_seeking_tendency', 0):.2f}")
                if 'learning_velocity' in patterns:
                    pattern_info.append(f"learning velocity: {patterns.get('learning_velocity', 0):.2f}")

                if pattern_info:
                    student_info_parts.append(f"BEHAVIOR METRICS: {', '.join(pattern_info)}")

            prompt_parts.append("\n".join(student_info_parts))

            # 添加知识点访问历史
            if hasattr(user_state, 'behavior_patterns') and user_state.behavior_patterns.get('knowledge_level_history'):
                history = user_state.behavior_patterns['knowledge_level_history']
                if history:
                    topic_summaries = []
                    # Sort topics for consistent ordering
                    sorted_topics = sorted(history.keys())
                    
                    for topic_id in sorted_topics:
                        topic_history = history[topic_id]
                        if not topic_history:
                            continue
                        
                        topic_details = [f"  For Topic '{topic_id}':"]
                        # Sort levels for consistent ordering, filtering out non-numeric keys
                        sorted_levels = sorted([k for k in topic_history.keys() if k.isdigit()], key=lambda x: int(x))
                        
                        for level in sorted_levels:
                            stats = topic_history[level]
                            visits = stats.get('visits', 0)
                            duration_sec = stats.get('total_duration_ms', 0) / 1000
                            topic_details.append(f"  - Level {level}: Visited {visits} time(s), total duration {duration_sec:.1f} seconds.")
                        
                        if len(topic_details) > 1:
                            topic_summaries.append("\\n".join(topic_details))

                    if topic_summaries:
                        full_history_summary = "\\n".join(topic_summaries)
                        prompt_parts.append(f"""
LEARNING FOCUS: Please pay close attention to the student's behavior patterns to better understand their learning state. Remember that higher knowledge levels are more difficult.
- **Knowledge Level Exploration**: The student has explored the following knowledge levels. Use their visit order, frequency, and dwell time to infer their interests and potential difficulties.
{full_history_summary}""")

        # 添加RAG上下文 (在用户状态信息之后，任务上下文之前)
        if retrieved_context:
            formatted_context = "\n\n---\n\n".join(retrieved_context)
            prompt_parts.append(f"REFERENCE KNOWLEDGE: Use the following information from the knowledge base to answer the user's question accurately.\n\n{formatted_context}")
        else:
            prompt_parts.append("REFERENCE KNOWLEDGE: No relevant knowledge was retrieved from the knowledge base. Answer based on your general knowledge.")

        # 添加任务上下文和分阶段debug逻辑
        if mode == "test":
            prompt_parts.append("MODE: The student is in test mode. Guide them to find the answer themselves. Do not give the answer directly.")
            
            # 使用统一提示词模版
            question_count = 0
            user_code = ""
            error_message = ""
            
            if hasattr(user_state, 'behavior_patterns'):
                question_count = user_state.behavior_patterns.get(f"question_count_{content_title}", 0)
            
            # 获取代码和错误信息
            if code_content and hasattr(code_content, 'js'):
                user_code = code_content.js
            
            if test_results:
                # 将测试结果转换为错误信息字符串
                error_message = json.dumps(test_results, indent=2, ensure_ascii=False)
            
            # 格式化调试提示词
            debug_prompt = self.debug_prompt_template.format(
                content_title=content_title or "Unknown",
                question_count=question_count,
                user_code=user_code,
                error_message=error_message
            )
            prompt_parts.append(debug_prompt)
        else:
            if mode == "learning":
                prompt_parts.append("MODE: The student is in learning mode. Provide detailed explanations and examples to help them understand the concepts.")
                
                # 使用学习模式提示词模版
                mastery_level = "beginner"
                mastery_prob = 0.0
                
                # 获取当前主题的掌握度信息
                if hasattr(user_state, 'bkt_models') and user_state.bkt_models and content_title:
                    for topic_key, bkt_model in user_state.bkt_models.items():
                        if content_title.lower() in topic_key.lower():
                            if isinstance(bkt_model, dict) and 'mastery_prob' in bkt_model:
                                mastery_prob = bkt_model['mastery_prob']
                            elif hasattr(bkt_model, 'mastery_prob'):
                                mastery_prob = bkt_model.mastery_prob
                            break
                    
                    # 确定掌握度等级
                    if mastery_prob > 0.8:
                        mastery_level = "advanced"
                    elif mastery_prob > 0.5:
                        mastery_level = "intermediate"
                
                # 格式化学习提示词
                learning_prompt = self.learning_prompt_template.format(
                    content_title=content_title or "Unknown",
                    mastery_level=mastery_level,
                    mastery_prob=mastery_prob
                )
                prompt_parts.append(learning_prompt)
            else:
                # 添加内容标题（非学习模式）
                if content_title:
                    prompt_parts.append(f"TOPIC: The current topic is '{content_title}'. Focus your explanations on this specific topic.")
        
        # 添加内容JSON（如果提供）
        if content_json:
            # 确保JSON内容正确编码，避免Unicode转义序列问题
            try:
                # 解析JSON字符串
                content_dict = json.loads(content_json)
                # 重新序列化为格式化的JSON字符串，确保中文正确显示
                formatted_content_json = json.dumps(content_dict, indent=2, ensure_ascii=False)
                prompt_parts.append(f"CONTENT DATA: Here is the detailed content data for the current topic. Use this to provide more specific and accurate guidance.\n{formatted_content_json}")
            except json.JSONDecodeError:
                # 如果解析失败，使用原始内容
                prompt_parts.append(f"CONTENT DATA: Here is the detailed content data for the current topic. Use this to provide more specific and accurate guidance.\n{content_json}")

        # 添加聚类分析结果（如果提供）
        if clustering_result and clustering_result.get("named_labels"):
            progress_info = self._format_clustering_result(clustering_result)
            prompt_parts.append(progress_info)

        return "\n\n".join(prompt_parts)

    @staticmethod
    def _get_emotion_strategy(emotion: str) -> str:
        """根据情感获取教学策略"""
        strategies = {
            'FRUSTRATED': "The student seems frustrated. Your top priority is to validate their feelings and be encouraging. Acknowledge the difficulty before offering help. Use phrases like 'I can see why this is frustrating, it's a tough concept' or 'Let's take a step back and try a different angle'. Avoid saying 'it's easy' or dismissing their struggle.",
            'CONFUSED': "The student seems confused. Your first step is to ask questions to pinpoint the source of confusion (e.g., 'Where did I lose you?' or 'What part of that example felt unclear?'). Then, break down concepts into smaller, simpler steps. Use analogies and the simplest possible examples. Avoid jargon.",
            'EXCITED': "The student seems excited and engaged. Praise their curiosity and capitalize on their momentum. Challenge them with deeper explanations or a more complex problem. Connect the concept to a real-world application or a related advanced topic to broaden their perspective.",
            'NEUTRAL': "The student seems neutral. Maintain a clear, structured teaching approach, but proactively try to spark interest by relating the topic to a surprising fact or a practical application. Frequently check for understanding with specific questions like 'Can you explain that back to me in your own words?' or 'How would you apply this to...?'"
        }

        return strategies.get(emotion.upper(), strategies['NEUTRAL'])

    def _build_message_history(
        self,
        conversation_history: List[Dict[str, str]],
        code_context: CodeContent = None,
        user_message: str = ""
    ) -> List[Dict[str, str]]:
        """构建消息历史"""
        messages = []

        # 添加历史对话
        for msg in conversation_history:
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

        # 构建当前用户消息
        current_user_content = user_message

        # 如果有代码上下文，添加到用户消息中
        if code_context:
            code_section = self._format_code_context(code_context)
            current_user_content = f"{code_section}\n\nMy question is: {user_message}"

        # 添加当前用户消息
        if current_user_content.strip():
            messages.append({
                "role": "user",
                "content": current_user_content
            })

        return messages

    def _format_code_context(self, code_context: CodeContent) -> str:
        """格式化代码上下文"""
        parts = []

        if code_context.html.strip():
            parts.append(f"HTML Code:\n```html\n{code_context.html}\n```")

        if code_context.css.strip():
            parts.append(f"CSS Code:\n```css\n{code_context.css}\n```")

        if code_context.js.strip():
            parts.append(f"JavaScript Code:\n```javascript\n{code_context.js}\n```")

        if parts:
            return "Here is my current code:\n\n" + "\n\n".join(parts)
        else:
            return ""

    def _format_clustering_result(self, clustering_result: Dict[str, Any]) -> str:
        """格式化聚类分析结果"""
        try:
            named_labels = clustering_result.get("named_labels", [])
            progress_score = clustering_result.get("progress_score", [])
            window_count = clustering_result.get("window_count", 0)
            
            if not named_labels:
                return ""
            
            # 获取最新的进度状态
            current_state = named_labels[-1] if named_labels else "正常"
            current_score = progress_score[-1] if progress_score else 0.0
            
            # 分析趋势
            trend_analysis = ""
            if len(progress_score) >= 3:
                recent_scores = progress_score[-3:]
                score_trend = recent_scores[-1] - recent_scores[0]
                if score_trend > 0.5:
                    trend_analysis = "The student's progress is improving."
                elif score_trend < -0.5:
                    trend_analysis = "The student's progress is declining."
                else:
                    trend_analysis = "The student's progress is stable."
            
            # 生成教学建议
            recommendations = self._get_progress_recommendations(current_state, score_trend if 'score_trend' in locals() else 0)
            
            progress_info = f"""
PROGRESS ANALYSIS: Based on conversation pattern analysis, the student's current learning progress state is "{current_state}".

{trend_analysis}

TEACHING RECOMMENDATIONS:
{chr(10).join([f"- {rec}" for rec in recommendations])}

ANALYSIS DETAILS:
- Progress Score: {current_score:.3f}
- Windows Analyzed: {window_count}
- Confidence: {min(1.0, abs(current_score) / 2.0):.2f}

Please adjust your teaching approach based on this progress analysis. If the student is in "低进度" (low progress), provide more detailed explanations and encouragement. If they are in "超进度" (high progress), offer more challenging content and advanced concepts.
"""
            return progress_info
            
        except Exception as e:
            print(f"Error formatting clustering result: {e}")
            return ""
    
    def _get_progress_recommendations(self, current_state: str, trend: float) -> List[str]:
        """根据进度状态和趋势生成教学建议"""
        recommendations = []
        
        if current_state == "低进度":
            if trend < -0.5:
                recommendations.extend([
                    "Provide more detailed step-by-step explanations",
                    "Offer simpler examples and analogies",
                    "Ask specific questions to identify confusion points",
                    "Give more encouragement and positive reinforcement"
                ])
            else:
                recommendations.extend([
                    "Continue with current supportive approach",
                    "Provide gradual difficulty progression",
                    "Celebrate small improvements"
                ])
        elif current_state == "超进度":
            if trend > 0.5:
                recommendations.extend([
                    "Introduce more advanced concepts and challenges",
                    "Encourage exploration of related topics",
                    "Ask deeper analytical questions",
                    "Provide opportunities for peer teaching"
                ])
            else:
                recommendations.extend([
                    "Maintain engagement with interesting content",
                    "Offer real-world applications",
                    "Encourage creative problem-solving"
                ])
        else:  # 正常
            if trend > 0.5:
                recommendations.extend([
                    "Continue current effective teaching approach",
                    "Gradually increase challenge level",
                    "Maintain good balance of support and challenge"
                ])
            elif trend < -0.5:
                recommendations.extend([
                    "Monitor for potential difficulties",
                    "Provide additional practice opportunities",
                    "Check understanding more frequently"
                ])
            else:
                recommendations.extend([
                    "Maintain steady teaching pace",
                    "Regularly assess comprehension",
                    "Provide balanced support and challenge"
                ])
        
        return recommendations


# 创建单例实例
prompt_generator = PromptGenerator()
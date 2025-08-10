# backend/app/services/llm_gateway.py
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from ..core.config import settings


class LLMGateway:
    """LLM网关服务"""
    
    def __init__(self):
        # 从环境变量或配置中获取API配置，支持多种命名方式
        self.api_key = os.getenv('TUTOR_OPENAI_API_KEY', settings.TUTOR_OPENAI_API_KEY)
        
        # 支持多种配置键名
        self.api_base = (
            os.getenv('TUTOR_OPENAI_API_BASE') or 
            os.getenv('OPENAI_API_BASE') or 
            settings.TUTOR_OPENAI_API_BASE
        )
        
        self.model = (
            os.getenv('TUTOR_OPENAI_MODEL') or 
            os.getenv('OPENAI_MODEL') or 
            settings.TUTOR_OPENAI_MODEL
        )

        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', settings.LLM_MAX_TOKENS))
        self.temperature = float(os.getenv('LLM_TEMPERATURE', settings.LLM_TEMPERATURE))
        
        # 初始化OpenAI客户端（兼容魔搭API）
        print(f"[DEBUG] LLM Gateway 配置:")
        print(f"  API Key: {self.api_key[:10]}...")
        print(f"  API Base: {self.api_base}")
        print(f"  Model: {self.model}")
        print(f"  Max Tokens: {self.max_tokens}")
        print(f"  Temperature: {self.temperature}")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
    
    async def get_completion(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        获取LLM完成结果
        
        Args:
            system_prompt: 系统提示词
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            str: LLM生成的回复
        """
        try:
            # 构建完整的消息列表
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            
            # 使用传入的参数或默认值
            max_tokens = max_tokens or self.max_tokens
            temperature = temperature or self.temperature
            
            # 调用LLM API - OpenAI客户端是同步的
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # 提取回复内容
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                return "I apologize, but I couldn't generate a response at this time."
                
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    


# 创建单例实例
llm_gateway = LLMGateway()

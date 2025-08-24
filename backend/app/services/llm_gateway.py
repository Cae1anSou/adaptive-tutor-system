# backend/app/services/llm_gateway.py
import os
import asyncio
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.core.config import settings


class LLMGateway:
    """LLM网关服务"""
    
    def __init__(self):
        # 从环境变量或配置中获取API配置
        self.api_key = os.getenv('TUTOR_OPENAI_API_KEY', settings.TUTOR_OPENAI_API_KEY)
        self.api_base = os.getenv('TUTOR_OPENAI_API_BASE', settings.TUTOR_OPENAI_API_BASE)
        self.model = os.getenv('TUTOR_OPENAI_MODEL', settings.TUTOR_OPENAI_MODEL)

        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', settings.LLM_MAX_TOKENS))
        self.temperature = float(os.getenv('LLM_TEMPERATURE', settings.LLM_TEMPERATURE))
        
        # 初始化OpenAI客户端（兼容魔搭API）
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
    
    def get_completion_sync(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        同步获取LLM完成结果
        
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
            
            # 直接调用OpenAI客户端（同步）
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
            # 使用 asyncio.to_thread 来在异步环境中运行同步代码

            #TODO:修改流式参数调用，修改返回逻辑
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=temperature
                #,stream=True,
            )
            
            #TODO:数据返回逻辑需要修改

            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                return "I apologize, but I couldn't generate a response at this time."
                
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    
    async def get_stream_completion(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ):
        """
        获取LLM流式完成结果
        
        Args:
            system_prompt: 系统提示词
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度参数
            
        Yields:
            str: LLM生成的回复片段
        """
        try:
            # 构建完整的消息列表
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            
            # 使用传入的参数或默认值
            max_tokens = max_tokens or self.max_tokens
            temperature = temperature or self.temperature
            
            # 调用LLM API - OpenAI客户端是同步的
            # 使用 asyncio.to_thread 来在异步环境中运行同步代码
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            
            # 流式返回内容
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content
            
            '''
            # 直接异步流式
            async with self.client.chat.completions.stream(
                model=self.model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            ) as stream:
                async for event in stream:
                    if event.type == "message.delta" and event.delta.get("content"):
                        yield event.delta["content"]
            '''
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            yield f"I apologize, but I encountered an error: {str(e)}"
       
    


# 创建单例实例
llm_gateway = LLMGateway()
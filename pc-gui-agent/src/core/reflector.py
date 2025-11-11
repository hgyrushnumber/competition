"""
反思器模块
"""
import json
from typing import List, Dict, Any, Optional
from .types import Reflection, ActionResult, Task
from ..llm.ollama_client import OllamaClient
from ..llm.prompt_templates import get_reflection_prompt
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Reflector:
    """反思器"""
    
    def __init__(self, ollama_client: OllamaClient):
        """
        初始化反思器
        
        Args:
            ollama_client: Ollama客户端
        """
        self.ollama_client = ollama_client
    
    async def reflect(
        self,
        task: Task,
        action_results: List[ActionResult],
        current_state: str = ""
    ) -> Reflection:
        """
        反思任务执行结果
        
        Args:
            task: 任务对象
            action_results: 动作执行结果列表
            current_state: 当前状态描述（可选）
            
        Returns:
            反思结果
        """
        logger.info(f"Reflecting on task: {task.id}")
        
        # 准备执行结果数据
        execution_results = [
            {
                "action": f"{r.action_id}",
                "success": r.success,
                "message": r.message,
                "error": r.error or ""
            }
            for r in action_results
        ]
        
        # 生成反思Prompt
        prompt = get_reflection_prompt(
            goal=task.goal,
            execution_results=execution_results,
            current_state=current_state
        )
        
        try:
            # 调用LLM进行反思
            response = await self.ollama_client.generate_async(prompt)
            
            # 解析JSON响应
            reflection_data = self._parse_reflection_response(response)
            
            return Reflection(
                task_id=task.id,
                success=reflection_data.get("success", False),
                analysis=reflection_data.get("analysis", ""),
                suggestions=reflection_data.get("suggestions", []),
                needs_replan=reflection_data.get("needs_replan", False),
                confidence=reflection_data.get("confidence", 0.0)
            )
        
        except Exception as e:
            logger.error(f"Reflection error: {e}")
            # 返回默认反思结果
            return Reflection(
                task_id=task.id,
                success=False,
                analysis=f"反思过程出错: {str(e)}",
                suggestions=["检查执行日志", "重试任务"],
                needs_replan=True,
                confidence=0.0
            )
    
    def _parse_reflection_response(self, response: str) -> Dict[str, Any]:
        """
        解析反思响应（JSON）
        
        Args:
            response: LLM响应文本
            
        Returns:
            解析后的字典
        """
        try:
            # 尝试提取JSON（可能包含markdown代码块）
            response = response.strip()
            
            # 如果包含代码块，提取JSON部分
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            return json.loads(response)
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse reflection response as JSON: {e}")
            logger.debug(f"Response content: {response}")
            
            # 返回默认结构
            return {
                "success": False,
                "analysis": "无法解析反思结果",
                "suggestions": [],
                "needs_replan": True,
                "confidence": 0.0
            }
    
    def analyze_error(
        self,
        error: str,
        action: Dict[str, Any],
        context: str = ""
    ) -> Dict[str, Any]:
        """
        分析错误（简化版本，不使用LLM）
        
        Args:
            error: 错误信息
            action: 动作信息
            context: 上下文信息
            
        Returns:
            错误分析结果
        """
        # 简单的错误分类
        error_lower = error.lower()
        
        if "timeout" in error_lower or "超时" in error_lower:
            return {
                "error_type": "timeout",
                "cause": "操作超时",
                "solution": "增加超时时间或检查网络连接",
                "should_retry": True
            }
        elif "not found" in error_lower or "未找到" in error_lower:
            return {
                "error_type": "element_not_found",
                "cause": "元素未找到",
                "solution": "检查选择器是否正确，或等待元素加载",
                "should_retry": True
            }
        elif "permission" in error_lower or "权限" in error_lower:
            return {
                "error_type": "permission_denied",
                "cause": "权限不足",
                "solution": "检查权限设置",
                "should_retry": False
            }
        else:
            return {
                "error_type": "unknown",
                "cause": "未知错误",
                "solution": "查看详细错误信息",
                "should_retry": True
            }
    
    def evaluate_strategy(
        self,
        strategy: str,
        results: List[ActionResult]
    ) -> Dict[str, Any]:
        """
        评估策略有效性
        
        Args:
            strategy: 策略描述
            results: 执行结果列表
            
        Returns:
            评估结果
        """
        total = len(results)
        success_count = sum(1 for r in results if r.success)
        success_rate = success_count / total if total > 0 else 0
        
        avg_time = sum(r.execution_time for r in results) / total if total > 0 else 0
        
        return {
            "strategy": strategy,
            "total_actions": total,
            "success_count": success_count,
            "success_rate": success_rate,
            "avg_execution_time": avg_time,
            "effective": success_rate > 0.7  # 成功率超过70%认为有效
        }


"""
规划器模块
"""
import json
import uuid
import re
from typing import List, Dict, Any, Optional
from .types import Task, Subtask, Action, ActionType, ExecutionPlan
from .error_handler import ErrorHandler, ErrorType
from ..llm.ollama_client import OllamaClient
from ..llm.prompt_templates import get_planning_prompt
from ..tools.registry import ToolRegistry, get_registry
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Planner:
    """规划器"""
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        tool_registry: Optional[ToolRegistry] = None
    ):
        """
        初始化规划器
        
        Args:
            ollama_client: Ollama客户端
            tool_registry: 工具注册表（可选，默认使用全局注册表）
        """
        self.ollama_client = ollama_client
        self.tool_registry = tool_registry or get_registry()
        self.error_handler = ErrorHandler()
    
    async def plan(self, goal: str, context: str = "") -> Task:
        """
        规划任务
        
        Args:
            goal: 用户目标
            context: 上下文信息（可选）
            
        Returns:
            任务对象
        """
        logger.info(f"Planning task: {goal}")
        
        # 获取可用工具列表
        available_tools = self.tool_registry.get_tools_list()
        
        # 生成规划Prompt
        prompt = get_planning_prompt(goal, available_tools, context)
        
        try:
            # 调用LLM进行规划
            response = await self.ollama_client.generate_async(prompt)
            
            # 解析规划结果（现在是异步方法）
            plan_data = await self._parse_plan_response(response)
            
            # 构建Task对象
            task = self._build_task(goal, plan_data)
            
            logger.info(f"Task planned: {task.id}, {len(task.subtasks)} subtasks")
            return task
        
        except Exception as e:
            logger.error(f"Planning error: {e}")
            # 返回一个简单的默认任务
            return self._create_default_task(goal, str(e))
    
    def _clean_json_string(self, json_str: str) -> str:
        """
        清理和修复 JSON 字符串
        
        Args:
            json_str: 原始 JSON 字符串
            
        Returns:
            清理后的 JSON 字符串
        """
        # 如果已经是有效的 JSON，直接返回，避免过度清理
        if self._is_valid_json(json_str):
            return json_str
        
        # 移除行注释（// 开头的注释）
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        
        # 移除块注释（/* ... */）
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # 修复单引号为双引号（但要注意字符串内的单引号）
        # 使用正则表达式匹配属性名和值
        def fix_quotes(match):
            # 匹配属性名: 值 的模式
            content = match.group(0)
            # 将单引号替换为双引号（但要避免替换字符串内的单引号）
            # 简单策略：替换键名和值的引号
            content = re.sub(r"'(\w+)'(\s*:)", r'"\1"\2', content)  # 键名
            content = re.sub(r":\s*'([^']*)'", r': "\1"', content)  # 字符串值
            return content
        
        # 尝试修复常见的单引号问题
        json_str = re.sub(r"'(\w+)'(\s*:)", r'"\1"\2', json_str)  # 键名
        json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)  # 简单字符串值
        
        # 转义字符串值中的控制字符
        def escape_control_chars(match):
            """转义JSON字符串值中的控制字符"""
            # match.group(0) 是整个匹配（包括引号）
            # match.group(1) 是字符串内容（不包括引号）
            string_content = match.group(1)
            
            # 转义控制字符映射
            control_char_map = {
                '\n': '\\n',
                '\r': '\\r',
                '\t': '\\t',
                '\b': '\\b',
                '\f': '\\f',
            }
            
            # 处理字符串内容，转义未转义的控制字符
            result = []
            i = 0
            while i < len(string_content):
                char = string_content[i]
                
                # 如果遇到反斜杠，检查下一个字符
                if char == '\\' and i + 1 < len(string_content):
                    next_char = string_content[i + 1]
                    # 如果已经是转义序列，保留它
                    if next_char in 'nrtbfu"\\/':
                        result.append(char + next_char)
                        i += 2
                        continue
                    # 如果反斜杠后面不是有效的转义字符，转义反斜杠本身
                    result.append('\\\\')
                    i += 1
                    continue
                
                # 检查是否是控制字符（0x00-0x1F，除了已处理的）
                if ord(char) < 0x20:
                    # 如果是常见的控制字符，使用标准转义
                    if char in control_char_map:
                        result.append(control_char_map[char])
                    else:
                        # 其他控制字符使用Unicode转义
                        result.append(f'\\u{ord(char):04x}')
                else:
                    result.append(char)
                
                i += 1
            
            # 返回完整的字符串（包括引号）
            return '"' + ''.join(result) + '"'
        
        # 匹配JSON字符串值（在双引号内的内容）
        # 这个正则表达式匹配：开始引号，然后是内容（可以是转义字符或非引号字符），最后是结束引号
        json_str = re.sub(r'"((?:[^"\\]|\\.)*)"', escape_control_chars, json_str)
        
        # 修复缺少逗号的问题
        # 使用正则表达式修复常见的缺少逗号情况
        # 注意：这些正则表达式假设字符串内的引号已经转义为\"
        
        # 修复对象属性之间缺少逗号："value" "key": 或 "value" "key"
        # 匹配：字符串值后跟空白，然后另一个字符串键
        json_str = re.sub(r'"\s+"([^"]+)"\s*:', r'", "\1":', json_str)
        # 匹配：字符串值后跟空白，然后另一个字符串值（在数组中）
        # 注意：在字符类中，]需要转义或放在开头
        json_str = re.sub(r'"\s+"([^"]+)"\s*([,}\]]])', r'", "\1"\2', json_str)
        
        # 修复数组元素之间缺少逗号："value" "value"
        # 但要注意不要匹配字符串内的内容（字符串内的引号应该是转义的）
        json_str = re.sub(r'"\s+"', r'", "', json_str)
        
        # 修复数字、布尔值、null之间缺少逗号
        # 数字后跟数字、字符串、布尔值、null、对象、数组
        # 注意：在字符类中，-需要转义或放在开头/结尾
        json_str = re.sub(r'(\d+)\s+(["\d{tfn\-])', r'\1, \2', json_str)
        # true/false/null后跟其他值
        json_str = re.sub(r'(true|false|null)\s+(["\d{tfn\-])', r'\1, \2', json_str)
        
        # 修复}或]后直接跟键或值的情况（但不在字符串内）
        # 注意：在字符类中，]需要转义或放在开头
        json_str = re.sub(r'([}\]])\s+"', r'\1, "', json_str)
        json_str = re.sub(r'([}\]])\s+([\d{tfn\-])', r'\1, \2', json_str)
        
        # 移除尾随逗号（在对象和数组的最后一个元素后）
        json_str = re.sub(r',(\s*[}\]]])', r'\1', json_str)
        
        # 移除多余的空白字符
        json_str = json_str.strip()
        
        return json_str
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        从响应中提取 JSON 字符串
        
        Args:
            response: LLM 响应文本
            
        Returns:
            提取的 JSON 字符串
        """
        response = response.strip()
        
        # 策略1: 查找 markdown 代码块
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                extracted = response[start:end].strip()
                # 验证提取的 JSON 是否有效
                if self._is_valid_json(extracted):
                    return extracted
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                extracted = response[start:end].strip()
                # 验证提取的 JSON 是否有效
                if self._is_valid_json(extracted):
                    return extracted
        
        # 策略2: 查找 JSON 对象（以 { 开始，以 } 结束）
        # 找到第一个 { 和最后一个匹配的 }
        brace_count = 0
        start_idx = -1
        for i, char in enumerate(response):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    extracted = response[start_idx:i+1].strip()
                    # 验证提取的 JSON 是否有效
                    if self._is_valid_json(extracted):
                        return extracted
        
        # 策略3: 如果找不到完整的 JSON，尝试查找包含 "subtasks" 的部分
        if '"subtasks"' in response or "'subtasks'" in response:
            # 找到包含 subtasks 的部分
            start = response.find('"subtasks"')
            if start == -1:
                start = response.find("'subtasks'")
            if start != -1:
                # 向前查找最近的 {
                json_start = response.rfind('{', 0, start)
                if json_start != -1:
                    # 向后查找匹配的 }
                    brace_count = 0
                    for i in range(json_start, len(response)):
                        if response[i] == '{':
                            brace_count += 1
                        elif response[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                extracted = response[json_start:i+1].strip()
                                # 验证提取的 JSON 是否有效
                                if self._is_valid_json(extracted):
                                    return extracted
        
        # 策略4: 返回整个响应（让后续清理函数处理）
        return response
    
    def _is_valid_json(self, json_str: str) -> bool:
        """
        验证字符串是否是有效的 JSON
        
        Args:
            json_str: 待验证的字符串
            
        Returns:
            如果是有效的 JSON 返回 True，否则返回 False
        """
        if not json_str or not json_str.strip():
            return False
        
        try:
            data = json.loads(json_str)
            # 如果是字典且包含 subtasks，认为是有效的规划 JSON
            if isinstance(data, dict) and "subtasks" in data:
                return True
            # 如果是字典，也认为是有效的 JSON（可能是其他格式）
            if isinstance(data, dict):
                return True
            return False
        except (json.JSONDecodeError, ValueError):
            return False
    
    def _validate_plan_data(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并修复规划数据的完整性
        
        Args:
            plan_data: 规划数据
            
        Returns:
            验证后的规划数据
        """
        if not isinstance(plan_data, dict):
            raise ValueError("Plan data must be a dictionary")
        
        # 确保有subtasks字段
        if "subtasks" not in plan_data:
            plan_data["subtasks"] = []
        
        # 验证每个subtask的结构
        validated_subtasks = []
        for idx, subtask in enumerate(plan_data.get("subtasks", [])):
            if not isinstance(subtask, dict):
                logger.warning(f"Subtask {idx} is not a dictionary, skipping")
                continue
            
            # 确保有必要的字段
            if "id" not in subtask:
                subtask["id"] = f"subtask_{idx + 1}"
            
            if "description" not in subtask:
                subtask["description"] = f"Subtask {idx + 1}"
            
            if "actions" not in subtask:
                subtask["actions"] = []
            
            # 验证actions
            validated_actions = []
            for action_idx, action in enumerate(subtask.get("actions", [])):
                if not isinstance(action, dict):
                    logger.warning(f"Action {action_idx} in subtask {subtask['id']} is not a dictionary, skipping")
                    continue
                
                # 确保有必要的字段
                if "tool" not in action:
                    logger.warning(f"Action {action_idx} in subtask {subtask['id']} missing 'tool' field, skipping")
                    continue
                
                if "args" not in action:
                    action["args"] = {}
                
                if "type" not in action:
                    action["type"] = "gui"
                
                validated_actions.append(action)
            
            subtask["actions"] = validated_actions
            validated_subtasks.append(subtask)
        
        plan_data["subtasks"] = validated_subtasks
        return plan_data
    
    def _fix_common_json_issues(self, json_str: str) -> str:
        """
        修复常见的JSON问题
        
        Args:
            json_str: JSON字符串
            
        Returns:
            修复后的JSON字符串
        """
        # 修复未闭合的字符串
        # 查找未闭合的双引号
        lines = json_str.split('\n')
        fixed_lines = []
        in_string = False
        escape_next = False
        
        for line in lines:
            fixed_line = []
            for char in line:
                if escape_next:
                    fixed_line.append(char)
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    fixed_line.append(char)
                    continue
                
                if char == '"':
                    in_string = not in_string
                    fixed_line.append(char)
                else:
                    fixed_line.append(char)
            
            fixed_lines.append(''.join(fixed_line))
        
        json_str = '\n'.join(fixed_lines)
        
        # 修复未转义的控制字符（在字符串值中）
        # 这个已经在_clean_json_string中处理了，但这里可以添加额外的修复
        
        # 修复数字后的逗号问题
        json_str = re.sub(r'(\d+)\s*,(\s*[}\]])', r'\1\2', json_str)
        
        return json_str
    
    def _extract_partial_json(self, response: str) -> Optional[Dict[str, Any]]:
        """
        尝试从响应中提取部分可用的JSON数据
        
        Args:
            response: LLM响应文本
            
        Returns:
            部分解析的数据，如果失败返回None
        """
        try:
            # 尝试找到subtasks数组
            subtasks_pattern = r'"subtasks"\s*:\s*\[(.*?)\]'
            match = re.search(subtasks_pattern, response, re.DOTALL)
            
            if match:
                subtasks_content = match.group(1)
                # 尝试提取每个subtask
                subtask_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                subtask_matches = re.findall(subtask_pattern, subtasks_content)
                
                if subtask_matches:
                    subtasks = []
                    for subtask_str in subtask_matches:
                        try:
                            subtask = json.loads(subtask_str)
                            if isinstance(subtask, dict):
                                subtasks.append(subtask)
                        except:
                            continue
                    
                    if subtasks:
                        return {"subtasks": subtasks}
        except Exception as e:
            logger.debug(f"Partial extraction error: {e}")
        
        return None
    
    async def _fix_json_with_llm(self, broken_json: str, error: json.JSONDecodeError) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 修复 JSON（参考 LangChain 的 OutputFixingParser）
        
        Args:
            broken_json: 损坏的 JSON 字符串
            error: JSON 解析错误
            
        Returns:
            修复后的数据，如果修复失败返回 None
        """
        # 提取错误位置附近的上下文，帮助 LLM 更好地定位问题
        error_context_start = max(0, error.pos - 100)
        error_context_end = min(len(broken_json), error.pos + 100)
        error_context = broken_json[error_context_start:error_context_end]
        error_marker = " " * (error.pos - error_context_start) + "^"
        
        fix_prompt = f"""以下是一个格式错误的 JSON 字符串，请修复它使其成为有效的 JSON。

错误信息：{error.msg}
错误位置：第 {error.lineno} 行，第 {error.colno} 列（字符位置 {error.pos}）

错误位置附近的上下文：
{error_context}
{error_marker}

完整的损坏 JSON：
{broken_json}

**重要要求：**
1. 仔细检查错误位置（第 {error.lineno} 行，第 {error.colno} 列）附近的代码
2. 修复所有格式错误（缺少逗号、尾随逗号、缺少引号、单引号、未转义的控制字符等）
3. 确保修复后的 JSON 可以被 Python 的 json.loads() 正确解析
4. **只返回修复后的 JSON，不要任何解释、说明、markdown 代码块标记或其他文字**
5. 保持原有的数据结构不变，不要修改数据内容
6. 确保所有字符串使用双引号，所有属性名使用双引号
7. 确保所有逗号、括号、大括号都正确匹配
8. 每个对象属性之间必须有逗号分隔（最后一个属性除外）
9. 每个数组元素之间必须有逗号分隔（最后一个元素除外）

**输出格式：**
直接输出修复后的 JSON，不要包含 ```json 或 ``` 标记，不要有任何前缀或后缀文字。

修复后的 JSON："""
        
        try:
            logger.info("Attempting LLM-based JSON repair...")
            fixed_response = await self.ollama_client.generate_async(fix_prompt)
            
            # 记录 LLM 的原始响应
            logger.debug(f"LLM fix response (length: {len(fixed_response)} chars):\n{fixed_response}")
            
            # 策略 1: 先尝试直接解析 LLM 返回的响应（如果已经是正确的 JSON）
            try:
                plan_data = json.loads(fixed_response.strip())
                if "subtasks" in plan_data:
                    logger.info("Successfully fixed JSON using LLM (direct parse)")
                    return plan_data
            except json.JSONDecodeError:
                logger.debug("Direct parse failed, trying extraction...")
            
            # 策略 2: 如果直接解析失败，尝试提取和清理
            try:
                # 提取修复后的 JSON
                fixed_json = self._extract_json_from_response(fixed_response)
                logger.debug(f"Extracted fixed JSON (length: {len(fixed_json)} chars):\n{fixed_json[:500]}...")
                
                # 先尝试直接解析提取后的 JSON（不清理）
                try:
                    plan_data = json.loads(fixed_json)
                    if "subtasks" in plan_data:
                        logger.info("Successfully fixed JSON using LLM (extracted, no cleaning)")
                        return plan_data
                except json.JSONDecodeError:
                    logger.debug("Extracted JSON parse failed, trying cleaning...")
                
                # 清理修复后的 JSON
                fixed_json = self._clean_json_string(fixed_json)
                logger.debug(f"Cleaned fixed JSON (length: {len(fixed_json)} chars):\n{fixed_json[:500]}...")
                
                # 解析清理后的 JSON
                plan_data = json.loads(fixed_json)
                
                # 验证数据结构
                if "subtasks" in plan_data:
                    logger.info("Successfully fixed JSON using LLM (extracted and cleaned)")
                    return plan_data
                else:
                    logger.warning("LLM fixed JSON but missing 'subtasks' field")
                    return None
            except Exception as extract_error:
                logger.debug(f"Extraction/cleaning failed: {extract_error}")
                raise
                
        except json.JSONDecodeError as e:
            logger.warning(f"LLM fixed JSON still has errors: {e}")
            logger.warning(f"LLM fix response (first 500 chars): {fixed_response[:500] if 'fixed_response' in locals() else 'N/A'}")
            logger.warning(f"LLM fix response (full):\n{fixed_response if 'fixed_response' in locals() else 'N/A'}")
            if 'fixed_json' in locals():
                logger.warning(f"Extracted fixed JSON (full):\n{fixed_json}")
            return None
        except Exception as e:
            logger.warning(f"LLM-based JSON fix failed: {e}")
            logger.debug(f"Fix error details: {e}", exc_info=True)
            return None
    
    async def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """
        解析规划响应（JSON）
        
        Args:
            response: LLM响应文本
            
        Returns:
            解析后的规划数据
        """
        original_response = response
        
        # 记录原始响应（DEBUG级别，用于调试）
        logger.debug(f"Original LLM response (length: {len(response)} chars):\n{response}")
        
        try:
            # 步骤1: 提取 JSON 字符串
            json_str = self._extract_json_from_response(response)
            logger.debug(f"Extracted JSON string (length: {len(json_str)} chars):\n{json_str[:500]}...")
            
            # 步骤2: 清理 JSON 字符串
            json_str = self._clean_json_string(json_str)
            logger.debug(f"Cleaned JSON string (length: {len(json_str)} chars):\n{json_str[:500]}...")
            
            # 步骤3: 尝试解析
            plan_data = json.loads(json_str)
            
            # 步骤4: 验证数据结构完整性
            plan_data = self._validate_plan_data(plan_data)
            
            logger.debug("Successfully parsed plan response")
            return plan_data
        
        except json.JSONDecodeError as e:
            # 记录JSON解析错误
            error_context = self.error_handler.create_error_context(
                error=e,
                error_type=ErrorType.JSON_PARSE_ERROR,
                additional_info={
                    "error_position": e.pos,
                    "error_line": e.lineno,
                    "error_column": e.colno,
                    "response_preview": original_response[:500]
                }
            )
            
            logger.warning(f"Failed to parse plan response as JSON: {e}")
            logger.warning(f"JSON decode error at position {e.pos} (line {e.lineno}, col {e.colno}): {e.msg}")
            logger.warning(f"Response content (first 500 chars): {original_response[:500]}")
            
            first_error = e
            
            # 策略 1: 尝试增强的正则修复
            try:
                logger.debug("Attempting enhanced regex-based JSON repair...")
                json_str = self._extract_json_from_response(original_response)
                
                # 使用增强的清理方法
                json_str = self._clean_json_string(json_str)
                json_str = self._fix_common_json_issues(json_str)
                
                plan_data = json.loads(json_str)
                plan_data = self._validate_plan_data(plan_data)
                
                if "subtasks" in plan_data:
                    logger.info("Successfully repaired and parsed JSON after enhanced regex repair")
                    return plan_data
            except Exception as repair_error:
                logger.debug(f"Enhanced regex repair failed: {repair_error}")
            
            # 策略 2: 尝试部分解析（提取可用的subtasks）
            try:
                logger.debug("Attempting partial JSON extraction...")
                partial_data = self._extract_partial_json(original_response)
                if partial_data and "subtasks" in partial_data:
                    logger.info("Successfully extracted partial JSON data")
                    return partial_data
            except Exception as partial_error:
                logger.debug(f"Partial extraction failed: {partial_error}")
            
            # 策略 3: 使用 LLM 修复（参考 LangChain 的 OutputFixingParser）
            try:
                fixed_data = await self._fix_json_with_llm(original_response, first_error)
                if fixed_data:
                    fixed_data = self._validate_plan_data(fixed_data)
                    return fixed_data
            except Exception as llm_fix_error:
                logger.warning(f"LLM-based JSON fix failed: {llm_fix_error}")
                logger.debug(f"LLM fix error details: {llm_fix_error}", exc_info=True)
            
            # 所有修复策略都失败，返回默认结构
            logger.error("All JSON repair strategies failed, returning default structure")
            return {
                "subtasks": [
                    {
                        "id": "subtask_1",
                        "description": "解析规划失败，使用默认任务",
                        "actions": []
                    }
                ]
            }
        
        except ValueError as e:
            # 记录验证错误
            error_context = self.error_handler.create_error_context(
                error=e,
                error_type=ErrorType.VALIDATION_ERROR,
                additional_info={"response_preview": original_response[:500]}
            )
            
            logger.warning(f"Validation error in plan response: {e}")
            logger.warning(f"Response content (first 500 chars): {original_response[:500]}")
            
            # 返回默认结构
            return {
                "subtasks": [
                    {
                        "id": "subtask_1",
                        "description": f"解析规划失败: {str(e)}",
                        "actions": []
                    }
                ]
            }
        
        except Exception as e:
            # 记录未知错误
            error_context = self.error_handler.create_error_context(
                error=e,
                error_type=ErrorType.UNKNOWN_ERROR,
                additional_info={"response_preview": original_response[:500]}
            )
            
            logger.error(f"Unexpected error parsing plan response: {e}", exc_info=True)
            logger.warning(f"Response content (first 500 chars): {original_response[:500]}")
            
            # 返回默认结构
            return {
                "subtasks": [
                    {
                        "id": "subtask_1",
                        "description": "解析规划失败，使用默认任务",
                        "actions": []
                    }
                ]
            }
    
    def _build_task(self, goal: str, plan_data: Dict[str, Any]) -> Task:
        """
        构建Task对象
        
        Args:
            goal: 用户目标
            plan_data: 规划数据
            
        Returns:
            Task对象
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        subtasks = []
        
        for subtask_data in plan_data.get("subtasks", []):
            subtask_id = subtask_data.get("id", f"subtask_{uuid.uuid4().hex[:8]}")
            description = subtask_data.get("description", "")
            actions_data = subtask_data.get("actions", [])
            dependencies = subtask_data.get("dependencies", [])
            
            # 构建Action列表
            actions = []
            for action_data in actions_data:
                action_type_str = action_data.get("type", "gui")
                try:
                    action_type = ActionType(action_type_str)
                except ValueError:
                    action_type = ActionType.GUI  # 默认使用GUI
                
                action = Action(
                    type=action_type,
                    tool=action_data.get("tool", ""),
                    args=action_data.get("args", {}),
                    description=action_data.get("description", ""),
                    dependencies=action_data.get("dependencies", []),
                    timeout=action_data.get("timeout")
                )
                actions.append(action)
            
            subtask = Subtask(
                id=subtask_id,
                description=description,
                actions=actions,
                dependencies=dependencies
            )
            subtasks.append(subtask)
        
        return Task(
            id=task_id,
            goal=goal,
            subtasks=subtasks
        )
    
    def _create_default_task(self, goal: str, error: str) -> Task:
        """创建默认任务（当规划失败时）"""
        return Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            goal=goal,
            subtasks=[
                Subtask(
                    id="subtask_1",
                    description=f"规划失败: {error}",
                    actions=[]
                )
            ]
        )
    
    async def replan(
        self,
        current_task: Task,
        reflection: Dict[str, Any],
        context: str = ""
    ) -> Task:
        """
        重新规划任务
        
        Args:
            current_task: 当前任务
            reflection: 反思结果
            context: 上下文信息
            
        Returns:
            新的任务对象
        """
        logger.info(f"Replanning task: {current_task.id}")
        
        # 构建重规划Prompt
        reflection_text = reflection.get("analysis", "")
        suggestions = reflection.get("suggestions", [])
        
        replan_context = f"""
原任务：{current_task.goal}
反思分析：{reflection_text}
建议：{', '.join(suggestions)}
"""
        
        # 使用新的规划
        return await self.plan(current_task.goal, replan_context)
    
    def analyze_dependencies(self, subtasks: List[Subtask]) -> Dict[str, List[str]]:
        """
        分析子任务依赖关系
        
        Args:
            subtasks: 子任务列表
            
        Returns:
            依赖关系图，格式：{subtask_id: [依赖的subtask_id列表]}
        """
        dependency_graph = {}
        
        for subtask in subtasks:
            dependency_graph[subtask.id] = subtask.dependencies
        
        return dependency_graph
    
    def select_optimal_strategy(
        self,
        task_description: str,
        available_tools: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        选择最优策略（简化版本，直接返回第一个可用工具）
        
        Args:
            task_description: 任务描述
            available_tools: 可用工具列表
            
        Returns:
            策略信息
        """
        # 简单实现：根据任务描述关键词匹配工具
        description_lower = task_description.lower()
        
        if "打开" in description_lower or "navigate" in description_lower or "url" in description_lower:
            tool_name = "navigate"
        elif "点击" in description_lower or "click" in description_lower:
            tool_name = "click"
        elif "输入" in description_lower or "input" in description_lower or "输入" in description_lower:
            tool_name = "input"
        else:
            tool_name = available_tools[0]["name"] if available_tools else "navigate"
        
        return {
            "tool": tool_name,
            "reason": f"根据任务描述选择工具: {tool_name}"
        }


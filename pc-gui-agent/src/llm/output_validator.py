"""
输出验证器
验证LLM输出的工具选择、参数有效性、JSON格式等
"""
import json
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    tool_valid: bool = True
    parameters_valid: bool = True
    structure_valid: bool = True
    json_valid: bool = True


class OutputValidator:
    """输出验证器"""
    
    def __init__(
        self,
        available_tools: Optional[List[Dict[str, str]]] = None,
        strict_mode: bool = True
    ):
        """
        初始化输出验证器
        
        Args:
            available_tools: 可用工具列表，格式：[{"name": "...", "description": "..."}]
            strict_mode: 严格模式，如果为True，任何错误都会导致验证失败
        """
        self.available_tools = available_tools or []
        self.strict_mode = strict_mode
        self.tool_names: Set[str] = set(t.get("name", "") for t in self.available_tools)
    
    def validate(
        self,
        output: Any,
        output_type: str = "plan"  # plan, decision, action
    ) -> ValidationResult:
        """
        验证输出
        
        Args:
            output: 输出数据（可以是字符串、字典等）
            output_type: 输出类型（plan, decision, action）
            
        Returns:
            验证结果
        """
        errors = []
        warnings = []
        tool_valid = True
        parameters_valid = True
        structure_valid = True
        json_valid = True
        
        # 如果是字符串，尝试解析为JSON
        if isinstance(output, str):
            try:
                output = json.loads(output)
                json_valid = True
            except json.JSONDecodeError as e:
                json_valid = False
                errors.append(f"JSON解析失败: {str(e)}")
                if self.strict_mode:
                    return ValidationResult(
                        is_valid=False,
                        errors=errors,
                        warnings=warnings,
                        json_valid=False
                    )
        
        # 如果不是字典，验证失败
        if not isinstance(output, dict):
            errors.append("输出必须是字典格式")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings
            )
        
        # 根据输出类型进行不同的验证
        if output_type == "plan":
            result = self._validate_plan(output)
        elif output_type == "decision":
            result = self._validate_decision(output)
        elif output_type == "action":
            result = self._validate_action(output)
        else:
            result = self._validate_generic(output)
        
        # 合并结果
        errors.extend(result.errors)
        warnings.extend(result.warnings)
        tool_valid = tool_valid and result.tool_valid
        parameters_valid = parameters_valid and result.parameters_valid
        structure_valid = structure_valid and result.structure_valid
        
        is_valid = (
            json_valid and
            tool_valid and
            parameters_valid and
            structure_valid and
            (not errors if self.strict_mode else True)
        )
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            tool_valid=tool_valid,
            parameters_valid=parameters_valid,
            structure_valid=structure_valid,
            json_valid=json_valid
        )
    
    def _validate_plan(self, plan: Dict[str, Any]) -> ValidationResult:
        """验证计划输出"""
        errors = []
        warnings = []
        tool_valid = True
        parameters_valid = True
        structure_valid = True
        
        # 检查必要字段
        if "subtasks" not in plan:
            errors.append("缺少'subtasks'字段")
            structure_valid = False
        
        if not structure_valid and self.strict_mode:
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                structure_valid=False
            )
        
        # 验证subtasks
        if "subtasks" in plan:
            subtasks = plan["subtasks"]
            if not isinstance(subtasks, list):
                errors.append("'subtasks'必须是列表")
                structure_valid = False
            else:
                for idx, subtask in enumerate(subtasks):
                    if not isinstance(subtask, dict):
                        errors.append(f"Subtask {idx} 必须是字典")
                        structure_valid = False
                        continue
                    
                    # 验证subtask字段
                    if "id" not in subtask:
                        warnings.append(f"Subtask {idx} 缺少'id'字段")
                    
                    if "description" not in subtask:
                        warnings.append(f"Subtask {idx} 缺少'description'字段")
                    
                    # 验证actions
                    if "actions" in subtask:
                        actions = subtask["actions"]
                        if not isinstance(actions, list):
                            errors.append(f"Subtask {idx} 的'actions'必须是列表")
                            structure_valid = False
                        else:
                            for action_idx, action in enumerate(actions):
                                action_result = self._validate_action(action)
                                if not action_result.is_valid:
                                    errors.extend([
                                        f"Subtask {idx}, Action {action_idx}: {e}"
                                        for e in action_result.errors
                                    ])
                                    tool_valid = tool_valid and action_result.tool_valid
                                    parameters_valid = parameters_valid and action_result.parameters_valid
        
        return ValidationResult(
            is_valid=structure_valid and tool_valid and parameters_valid,
            errors=errors,
            warnings=warnings,
            tool_valid=tool_valid,
            parameters_valid=parameters_valid,
            structure_valid=structure_valid
        )
    
    def _validate_decision(self, decision: Dict[str, Any]) -> ValidationResult:
        """验证决策输出"""
        errors = []
        warnings = []
        tool_valid = True
        parameters_valid = True
        structure_valid = True
        
        # 检查action字段
        if "action" in decision:
            action = decision["action"]
            if not isinstance(action, dict):
                errors.append("'action'必须是字典")
                structure_valid = False
            else:
                action_result = self._validate_action(action)
                if not action_result.is_valid:
                    errors.extend(action_result.errors)
                    tool_valid = action_result.tool_valid
                    parameters_valid = action_result.parameters_valid
        
        # 检查其他字段
        if "should_continue" in decision:
            if not isinstance(decision["should_continue"], bool):
                warnings.append("'should_continue'应该是布尔值")
        
        if "confidence" in decision:
            conf = decision["confidence"]
            if isinstance(conf, (int, float)):
                if conf < 0 or conf > 1:
                    warnings.append("'confidence'应该在0-1之间")
            else:
                warnings.append("'confidence'应该是数字")
        
        return ValidationResult(
            is_valid=structure_valid and tool_valid and parameters_valid,
            errors=errors,
            warnings=warnings,
            tool_valid=tool_valid,
            parameters_valid=parameters_valid,
            structure_valid=structure_valid
        )
    
    def _validate_action(self, action: Dict[str, Any]) -> ValidationResult:
        """验证动作输出"""
        errors = []
        warnings = []
        tool_valid = True
        parameters_valid = True
        structure_valid = True
        
        # 检查tool字段
        if "tool" not in action:
            errors.append("缺少'tool'字段")
            structure_valid = False
            tool_valid = False
        else:
            tool_name = action["tool"]
            if not isinstance(tool_name, str):
                errors.append("'tool'必须是字符串")
                tool_valid = False
            elif self.tool_names and tool_name not in self.tool_names:
                # 检查工具是否在可用列表中
                if not tool_name.startswith("mcp_"):
                    # 不是MCP工具，且不在列表中
                    warnings.append(f"工具'{tool_name}'不在可用工具列表中")
                    # 在非严格模式下，这可能只是警告
                    if self.strict_mode:
                        tool_valid = False
        
        # 检查type字段（可选）
        if "type" in action:
            action_type = action["type"]
            valid_types = ["gui", "code", "mcp"]
            if action_type not in valid_types:
                warnings.append(f"未知的动作类型: {action_type}")
        
        # 检查args字段
        if "args" in action:
            args = action["args"]
            if not isinstance(args, dict):
                errors.append("'args'必须是字典")
                parameters_valid = False
            else:
                # 验证参数值
                for key, value in args.items():
                    if value is None:
                        warnings.append(f"参数'{key}'的值为None")
                    elif isinstance(value, str) and len(value) == 0:
                        warnings.append(f"参数'{key}'为空字符串")
                    elif isinstance(value, str) and len(value) > 10000:
                        warnings.append(f"参数'{key}'的值过长（>{10000}字符）")
        
        return ValidationResult(
            is_valid=structure_valid and tool_valid and parameters_valid,
            errors=errors,
            warnings=warnings,
            tool_valid=tool_valid,
            parameters_valid=parameters_valid,
            structure_valid=structure_valid
        )
    
    def _validate_generic(self, data: Dict[str, Any]) -> ValidationResult:
        """通用验证"""
        errors = []
        warnings = []
        
        # 基本结构检查
        if not isinstance(data, dict):
            errors.append("数据必须是字典格式")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                structure_valid=False
            )
        
        # 检查是否有空字典
        if not data:
            warnings.append("数据为空字典")
        
        return ValidationResult(
            is_valid=True,
            errors=errors,
            warnings=warnings
        )
    
    def validate_tool_name(self, tool_name: str) -> bool:
        """
        验证工具名称
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否有效
        """
        if not tool_name:
            return False
        
        # MCP工具总是有效的（动态工具）
        if tool_name.startswith("mcp_"):
            return True
        
        # 标准GUI工具
        standard_tools = {"navigate", "click", "input", "scroll", "screenshot", "wait"}
        if tool_name in standard_tools:
            return True
        
        # 检查是否在可用工具列表中
        if self.tool_names:
            return tool_name in self.tool_names
        
        # 如果没有工具列表，假设有效
        return True
    
    def validate_parameters(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        验证工具参数
        
        Args:
            tool_name: 工具名称
            args: 参数字典
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        if not isinstance(args, dict):
            return False, ["参数必须是字典格式"]
        
        # 根据工具类型验证参数
        if tool_name == "navigate":
            if "url" not in args:
                errors.append("navigate工具需要'url'参数")
        elif tool_name == "click":
            if "selector" not in args and "x" not in args and "y" not in args:
                errors.append("click工具需要'selector'或'x'/'y'参数")
        elif tool_name == "input":
            if "selector" not in args:
                errors.append("input工具需要'selector'参数")
            if "text" not in args:
                errors.append("input工具需要'text'参数")
        elif tool_name == "scroll":
            if "direction" not in args and "amount" not in args:
                errors.append("scroll工具需要'direction'或'amount'参数")
        
        return len(errors) == 0, errors
    
    def update_available_tools(self, tools: List[Dict[str, str]]):
        """
        更新可用工具列表
        
        Args:
            tools: 工具列表
        """
        self.available_tools = tools
        self.tool_names = set(t.get("name", "") for t in tools)
        logger.info(f"Updated available tools: {len(self.tool_names)} tools")


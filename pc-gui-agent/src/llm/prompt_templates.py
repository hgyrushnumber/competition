"""
Prompt模板
"""
from typing import List, Dict, Any


def get_planning_prompt(goal: str, available_tools: List[Dict[str, str]], context: str = "") -> str:
    """
    获取任务规划Prompt
    
    Args:
        goal: 用户目标
        available_tools: 可用工具列表，格式：[{"name": "...", "description": "..."}]
        context: 上下文信息（可选）
        
    Returns:
        Prompt字符串
    """
    tools_text = "\n".join([
        f"- {tool['name']}: {tool['description']}"
        for tool in available_tools
    ])
    
    prompt = f"""你是一个智能任务规划助手。请根据用户目标，生成详细的执行计划。

用户目标：{goal}

可用工具：
{tools_text}

**重要：工具名称使用规则**
1. 必须使用工具列表中每个工具的"name"字段的精确值（区分大小写）
2. 工具名称必须完全匹配，不能使用中文名称或别名
3. 例如：如果工具列表中有"navigate"，必须使用"navigate"，不能使用"浏览器"、"导航"等
4. 工具名称示例：navigate, click, input, scroll, screenshot, wait

请生成一个JSON格式的执行计划，包含以下结构：
{{
  "subtasks": [
    {{
      "id": "subtask_1",
      "description": "子任务描述",
      "actions": [
        {{
          "type": "gui|code|mcp",
          "tool": "工具名称（必须使用工具列表中的精确name字段）",
          "args": {{"参数名": "参数值"}},
          "description": "动作描述",
          "dependencies": []
        }}
      ],
      "dependencies": []
    }}
  ]
}}

**重要：JSON格式要求**
1. 必须使用双引号（"），不能使用单引号（'）
2. 属性名必须用双引号括起来
3. 不能包含注释（// 或 /* */）
4. 最后一个元素后不能有尾随逗号
5. 只返回纯JSON，不要包含markdown代码块标记或其他文本
6. 确保JSON格式完全正确，可以直接被解析

要求：
1. 将复杂任务分解为多个子任务
2. 每个子任务包含多个动作
3. 明确动作之间的依赖关系
4. **必须使用工具列表中的精确工具名称（name字段），不能使用中文名称或别名**
5. 选择合适的工具和参数
6. 动作类型：
   - gui：GUI操作（浏览器操作，如navigate、click、input等）
   - code：代码执行（执行Python/JavaScript等代码）
   - mcp：MCP工具调用（系统工具，如文件操作、应用启动等，工具名称以"mcp_"开头）
7. MCP工具说明：如果工具名称以"mcp_"开头，表示这是MCP工具，可以通过MCP协议调用系统功能（文件读写、应用启动、系统命令等）
8. **只返回纯JSON字符串，不要其他解释、说明或markdown代码块**

{f"上下文信息：{context}" if context else ""}

请生成执行计划："""
    
    return prompt


def get_reflection_prompt(
    goal: str,
    execution_results: List[Dict[str, Any]],
    current_state: str = ""
) -> str:
    """
    获取反思Prompt
    
    Args:
        goal: 用户目标
        execution_results: 执行结果列表
        current_state: 当前状态描述
        
    Returns:
        Prompt字符串
    """
    results_text = "\n".join([
        f"- 动作：{r.get('action', 'unknown')}\n"
        f"  结果：{'成功' if r.get('success') else '失败'}\n"
        f"  信息：{r.get('message', '')}\n"
        f"  错误：{r.get('error', '无')}"
        for r in execution_results
    ])
    
    prompt = f"""你是一个智能反思助手。请评估任务执行结果，分析问题并给出调整建议。

用户目标：{goal}

执行结果：
{results_text}

当前状态：
{current_state if current_state else "未知"}

请生成一个JSON格式的反思结果，包含以下结构：
{{
  "success": true/false,
  "analysis": "详细分析执行结果，包括成功和失败的原因",
  "suggestions": ["建议1", "建议2"],
  "needs_replan": true/false,
  "confidence": 0.0-1.0
}}

要求：
1. 客观评估执行结果
2. 分析失败原因（如果有）
3. 提供具体的调整建议
4. 判断是否需要重新规划
5. 给出置信度（0-1之间）
6. 只返回JSON，不要其他解释

请生成反思结果："""
    
    return prompt


def get_tool_selection_prompt(
    task_description: str,
    available_tools: List[Dict[str, str]],
    context: str = ""
) -> str:
    """
    获取工具选择Prompt
    
    Args:
        task_description: 任务描述
        available_tools: 可用工具列表
        context: 上下文信息
        
    Returns:
        Prompt字符串
    """
    tools_text = "\n".join([
        f"- {tool['name']}: {tool['description']}"
        for tool in available_tools
    ])
    
    prompt = f"""请为以下任务选择最合适的工具。

任务描述：{task_description}

可用工具：
{tools_text}

{f"上下文：{context}" if context else ""}

请返回JSON格式：
{{
  "tool": "工具名称",
  "args": {{"参数名": "参数值"}},
  "reason": "选择理由"
}}

只返回JSON，不要其他解释："""
    
    return prompt


def get_element_finding_prompt(
    action_description: str,
    element_type: str,
    available_elements: str
) -> str:
    """
    获取元素查找Prompt
    
    Args:
        action_description: 动作描述，如"输入搜索关键词"、"点击搜索按钮"
        element_type: 元素类型（input, button, link等）
        available_elements: 可用元素列表（格式化后的文本）
        
    Returns:
        Prompt字符串
    """
    prompt = f"""你是一个智能元素查找助手。请根据动作描述，从页面元素中找到最匹配的目标元素。

动作描述：{action_description}
目标元素类型：{element_type}

页面可用元素：
{available_elements}

**重要提示**：
1. 优先选择标记了⭐的元素（这些是页面中的关键元素，如搜索框）
2. 对于搜索相关操作，优先匹配以下特征的元素：
   - name属性包含"wd"、"q"、"search"（常见搜索框name）
   - id属性包含"kw"、"search"、"query"（常见搜索框ID）
   - placeholder包含"搜索"、"search"、"请输入"等关键词
   - type="search"的input元素
3. 对于按钮操作，优先匹配包含"搜索"、"search"、"提交"、"submit"等文本的按钮
4. 优先使用ID和name属性作为选择器（更稳定可靠）

请分析动作描述，找到最匹配的元素，并返回JSON格式：
{{
  "selector": "CSS选择器",
  "reason": "选择理由"
}}

要求：
1. 仔细分析动作描述，理解用户意图
2. 优先选择标记了⭐的元素
3. 优先匹配搜索相关特征（name、id、placeholder等）
4. 从可用元素中选择最匹配的元素
5. 返回准确的CSS选择器（使用元素列表中的selector字段）
6. 如果找不到匹配的元素，返回null
7. 只返回JSON，不要其他解释

请返回查找结果："""
    
    return prompt


def get_error_analysis_prompt(
    error: str,
    action: Dict[str, Any],
    context: str = ""
) -> str:
    """
    获取错误分析Prompt
    
    Args:
        error: 错误信息
        action: 动作信息
        context: 上下文信息
        
    Returns:
        Prompt字符串
    """
    prompt = f"""请分析以下错误，并提供解决方案。

错误信息：{error}

动作信息：
- 类型：{action.get('type', 'unknown')}
- 工具：{action.get('tool', 'unknown')}
- 参数：{action.get('args', {})}

{f"上下文：{context}" if context else ""}

请返回JSON格式：
{{
  "error_type": "错误类型",
  "cause": "可能原因",
  "solution": "解决方案",
  "should_retry": true/false,
  "alternative_action": {{"tool": "...", "args": {{}}}}
}}

只返回JSON，不要其他解释："""
    
    return prompt


def get_agent_step_prompt(
    goal: str,
    context: Any,
    available_tools: List[Dict[str, str]],
    action_results: List[Any],
    last_decision: Any = None
) -> str:
    """
    获取Agent模式的逐步决策Prompt
    
    Args:
        goal: 用户目标
        context: 执行上下文
        available_tools: 可用工具列表
        action_results: 已执行的动作结果列表
        last_decision: 上一步决策（可选）
        
    Returns:
        Prompt字符串
    """
    tools_text = "\n".join([
        f"- {tool['name']}: {tool['description']}"
        for tool in available_tools
    ])
    
    # 格式化已执行的动作结果
    results_text = ""
    if action_results:
        results_text = "\n已执行的动作：\n"
        for idx, result in enumerate(action_results[-5:], 1):  # 只显示最近5个结果
            results_text += f"{idx}. {result.action_id if hasattr(result, 'action_id') else 'unknown'}: "
            results_text += f"{'成功' if result.success else '失败'} - {result.message}\n"
    
    # 格式化上下文变量
    variables_text = ""
    if hasattr(context, 'variables') and context.variables:
        variables_text = "\n上下文变量：\n"
        for key, value in list(context.variables.items())[-10:]:  # 只显示最近10个变量
            variables_text += f"- {key}: {str(value)[:100]}\n"
    
    prompt = f"""你是一个智能任务执行助手，需要逐步决策每一步操作来完成用户目标。

用户目标：{goal}

可用工具：
{tools_text}
{results_text}
{variables_text}

**重要：工具名称使用规则**
1. 必须使用工具列表中每个工具的"name"字段的精确值（区分大小写）
2. 工具名称必须完全匹配，不能使用中文名称或别名
3. 例如：如果工具列表中有"navigate"，必须使用"navigate"，不能使用"浏览器"、"导航"等

请分析当前状态，决定下一步操作。返回JSON格式：
{{
  "action": {{
    "type": "gui|code|mcp",
    "tool": "工具名称（必须使用工具列表中的精确name字段）",
    "args": {{"参数名": "参数值"}},
    "description": "动作描述"
  }},
  "should_continue": true/false,
  "should_retry": false,
  "should_skip": false,
  "reasoning": "决策理由",
  "confidence": 0.0-1.0,
  "next_step_description": "下一步描述"
}}

**决策规则：**
1. 如果任务已完成，设置 should_continue 为 false
2. 如果上一步失败且可以重试，设置 should_retry 为 true
3. 如果当前步骤应该跳过，设置 should_skip 为 true
4. 根据当前状态选择最合适的工具和参数
5. 给出决策的置信度（0-1之间）
6. **必须使用工具列表中的精确工具名称（name字段），不能使用中文名称或别名**

**JSON格式要求：**
1. 必须使用双引号（"），不能使用单引号（'）
2. 属性名必须用双引号括起来
3. 不能包含注释（// 或 /* */）
4. 最后一个元素后不能有尾随逗号
5. 只返回纯JSON，不要包含markdown代码块标记或其他文本

请生成下一步决策："""
    
    return prompt


def get_workflow_validation_prompt(
    workflow_name: str,
    step_results: List[Dict[str, Any]],
    goal: str
) -> str:
    """
    获取工作流验证Prompt
    
    Args:
        workflow_name: 工作流名称
        step_results: 步骤执行结果列表
        goal: 用户目标
        
    Returns:
        Prompt字符串
    """
    results_text = "\n".join([
        f"- 步骤 {idx + 1}: {result.get('step_name', 'unknown')} - "
        f"{'成功' if result.get('success') else '失败'}"
        for idx, result in enumerate(step_results)
    ])
    
    prompt = f"""请验证工作流执行结果。

工作流名称：{workflow_name}
用户目标：{goal}

步骤执行结果：
{results_text}

请返回JSON格式：
{{
  "workflow_complete": true/false,
  "goal_achieved": true/false,
  "validation_message": "验证消息",
  "missing_steps": ["缺失的步骤"],
  "suggestions": ["建议"]
}}

只返回JSON，不要其他解释："""
    
    return prompt

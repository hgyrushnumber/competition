"""
置信度评估器
计算决策的置信度分数，设置阈值，判断是否应该接受决策
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConfidenceScore:
    """置信度分数"""
    overall: float  # 总体置信度 (0-1)
    tool_selection: float = 0.0  # 工具选择置信度
    parameter_quality: float = 0.0  # 参数质量置信度
    structure_validity: float = 0.0  # 结构有效性置信度
    consistency: float = 0.0  # 一致性分数（如果使用了Self-Consistency）
    factors: Dict[str, float] = None  # 各因素详细分数
    
    def __post_init__(self):
        if self.factors is None:
            self.factors = {}


@dataclass
class ConfidenceThreshold:
    """置信度阈值配置"""
    min_confidence: float = 0.6  # 最小置信度阈值
    high_confidence: float = 0.8  # 高置信度阈值
    tool_selection_weight: float = 0.3  # 工具选择权重
    parameter_weight: float = 0.2  # 参数权重
    structure_weight: float = 0.2  # 结构权重
    consistency_weight: float = 0.3  # 一致性权重


class ConfidenceEvaluator:
    """置信度评估器"""
    
    def __init__(
        self,
        threshold: Optional[ConfidenceThreshold] = None,
        enable_history: bool = True
    ):
        """
        初始化置信度评估器
        
        Args:
            threshold: 置信度阈值配置（可选）
            enable_history: 是否启用历史记录
        """
        self.threshold = threshold or ConfidenceThreshold()
        self.enable_history = enable_history
        self.history: List[Dict[str, Any]] = []
    
    def evaluate(
        self,
        decision: Dict[str, Any],
        available_tools: Optional[List[Dict[str, str]]] = None,
        consistency_score: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ConfidenceScore:
        """
        评估决策的置信度
        
        Args:
            decision: 决策数据（包含action、tool、args等）
            available_tools: 可用工具列表（可选，用于验证工具选择）
            consistency_score: 一致性分数（如果使用了Self-Consistency）
            context: 上下文信息（可选）
            
        Returns:
            置信度分数
        """
        factors = {}
        
        # 1. 工具选择置信度
        tool_confidence = self._evaluate_tool_selection(
            decision,
            available_tools
        )
        factors["tool_selection"] = tool_confidence
        
        # 2. 参数质量置信度
        param_confidence = self._evaluate_parameters(decision)
        factors["parameter_quality"] = param_confidence
        
        # 3. 结构有效性置信度
        structure_confidence = self._evaluate_structure(decision)
        factors["structure_validity"] = structure_confidence
        
        # 4. 一致性分数（如果提供）
        consistency = consistency_score if consistency_score is not None else 0.0
        factors["consistency"] = consistency
        
        # 5. 计算总体置信度（加权平均）
        overall = (
            tool_confidence * self.threshold.tool_selection_weight +
            param_confidence * self.threshold.parameter_weight +
            structure_confidence * self.threshold.structure_weight +
            consistency * self.threshold.consistency_weight
        )
        
        score = ConfidenceScore(
            overall=overall,
            tool_selection=tool_confidence,
            parameter_quality=param_confidence,
            structure_validity=structure_confidence,
            consistency=consistency,
            factors=factors
        )
        
        # 记录历史
        if self.enable_history:
            self.history.append({
                "timestamp": datetime.now(),
                "decision": decision,
                "score": overall,
                "factors": factors,
                "accepted": overall >= self.threshold.min_confidence
            })
        
        return score
    
    def _evaluate_tool_selection(
        self,
        decision: Dict[str, Any],
        available_tools: Optional[List[Dict[str, str]]] = None
    ) -> float:
        """
        评估工具选择置信度
        
        Args:
            decision: 决策数据
            available_tools: 可用工具列表
            
        Returns:
            工具选择置信度 (0-1)
        """
        # 提取工具名称
        tool_name = None
        if "action" in decision and isinstance(decision["action"], dict):
            tool_name = decision["action"].get("tool")
        elif "tool" in decision:
            tool_name = decision["tool"]
        
        if not tool_name:
            return 0.0
        
        # 如果提供了可用工具列表，验证工具是否存在
        if available_tools:
            tool_names = [t.get("name", "") for t in available_tools]
            if tool_name not in tool_names:
                logger.warning(f"Tool '{tool_name}' not in available tools list")
                return 0.3  # 工具不存在，置信度较低
        
        # 工具名称格式检查
        if tool_name.startswith("mcp_"):
            # MCP工具，格式正确
            return 1.0
        elif tool_name in ["navigate", "click", "input", "scroll", "screenshot", "wait"]:
            # 标准GUI工具
            return 1.0
        else:
            # 未知工具，但可能是有效的
            return 0.7
    
    def _evaluate_parameters(
        self,
        decision: Dict[str, Any]
    ) -> float:
        """
        评估参数质量置信度
        
        Args:
            decision: 决策数据
            
        Returns:
            参数质量置信度 (0-1)
        """
        # 提取参数
        args = {}
        if "action" in decision and isinstance(decision["action"], dict):
            args = decision["action"].get("args", {})
        elif "args" in decision:
            args = decision["args"]
        
        if not args:
            # 某些工具可能不需要参数
            return 0.8
        
        score = 1.0
        
        # 检查参数类型
        for key, value in args.items():
            # 参数值不能为空（除非是可选参数）
            if value is None or value == "":
                score *= 0.8
            
            # 检查参数值的合理性
            if isinstance(value, str) and len(value) > 1000:
                # 参数值过长，可能有问题
                score *= 0.9
        
        return score
    
    def _evaluate_structure(
        self,
        decision: Dict[str, Any]
    ) -> float:
        """
        评估结构有效性置信度
        
        Args:
            decision: 决策数据
            
        Returns:
            结构有效性置信度 (0-1)
        """
        score = 1.0
        
        # 检查必要字段
        if "action" in decision:
            action = decision["action"]
            if not isinstance(action, dict):
                return 0.0
            
            # 检查action的必要字段
            if "tool" not in action:
                score *= 0.3
            if "type" not in action:
                score *= 0.8  # type可选，但有更好
            if "args" not in action:
                score *= 0.8  # args可选
        elif "tool" not in decision:
            return 0.0
        
        # 检查数据类型
        if "should_continue" in decision:
            if not isinstance(decision["should_continue"], bool):
                score *= 0.8
        
        if "confidence" in decision:
            conf = decision["confidence"]
            if isinstance(conf, (int, float)):
                if conf < 0 or conf > 1:
                    score *= 0.5  # 置信度超出范围
        
        return score
    
    def should_accept(
        self,
        confidence_score: ConfidenceScore
    ) -> bool:
        """
        判断是否应该接受决策
        
        Args:
            confidence_score: 置信度分数
            
        Returns:
            是否应该接受
        """
        return confidence_score.overall >= self.threshold.min_confidence
    
    def get_confidence_level(
        self,
        confidence_score: ConfidenceScore
    ) -> str:
        """
        获取置信度级别
        
        Args:
            confidence_score: 置信度分数
            
        Returns:
            置信度级别：low, medium, high
        """
        if confidence_score.overall >= self.threshold.high_confidence:
            return "high"
        elif confidence_score.overall >= self.threshold.min_confidence:
            return "medium"
        else:
            return "low"
    
    def get_recommendation(
        self,
        confidence_score: ConfidenceScore
    ) -> str:
        """
        获取建议
        
        Args:
            confidence_score: 置信度分数
            
        Returns:
            建议文本
        """
        level = self.get_confidence_level(confidence_score)
        
        if level == "high":
            return "高置信度，可以执行"
        elif level == "medium":
            return "中等置信度，建议执行但需要监控"
        else:
            # 分析低置信度的原因
            issues = []
            if confidence_score.tool_selection < 0.5:
                issues.append("工具选择不确定")
            if confidence_score.parameter_quality < 0.5:
                issues.append("参数质量较低")
            if confidence_score.structure_validity < 0.5:
                issues.append("结构有效性不足")
            if confidence_score.consistency < 0.5:
                issues.append("一致性较低")
            
            if issues:
                return f"低置信度，不建议执行。问题：{', '.join(issues)}"
            else:
                return "低置信度，建议重新生成或人工确认"
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取历史统计信息
        
        Returns:
            统计信息
        """
        if not self.history:
            return {
                "total_decisions": 0,
                "accepted_count": 0,
                "rejected_count": 0,
                "average_confidence": 0.0
            }
        
        total = len(self.history)
        accepted = sum(1 for h in self.history if h["accepted"])
        rejected = total - accepted
        avg_confidence = sum(h["score"] for h in self.history) / total
        
        # 按置信度级别统计
        high_count = sum(1 for h in self.history if h["score"] >= self.threshold.high_confidence)
        medium_count = sum(
            1 for h in self.history 
            if self.threshold.min_confidence <= h["score"] < self.threshold.high_confidence
        )
        low_count = sum(1 for h in self.history if h["score"] < self.threshold.min_confidence)
        
        return {
            "total_decisions": total,
            "accepted_count": accepted,
            "rejected_count": rejected,
            "acceptance_rate": accepted / total if total > 0 else 0.0,
            "average_confidence": avg_confidence,
            "high_confidence_count": high_count,
            "medium_confidence_count": medium_count,
            "low_confidence_count": low_count
        }
    
    def clear_history(self):
        """清空历史记录"""
        self.history.clear()
        logger.info("Confidence evaluation history cleared")


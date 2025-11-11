"""
不确定性监控
记录和分析LLM输出的不确定性指标，用于优化
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class UncertaintyMetrics:
    """不确定性指标"""
    timestamp: datetime
    prompt_hash: str  # Prompt的哈希值（用于识别相同prompt）
    consistency_score: float  # 一致性分数（如果使用了Self-Consistency）
    confidence_score: float  # 置信度分数
    validation_errors: int  # 验证错误数量
    validation_warnings: int  # 验证警告数量
    sample_count: int = 1  # 采样次数（Self-Consistency）
    valid_sample_count: int = 1  # 有效采样次数
    tool_selection_uncertainty: float = 0.0  # 工具选择不确定性
    parameter_uncertainty: float = 0.0  # 参数不确定性
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UncertaintyReport:
    """不确定性报告"""
    total_requests: int
    average_consistency: float
    average_confidence: float
    high_uncertainty_count: int  # 高不确定性请求数量
    low_uncertainty_count: int  # 低不确定性请求数量
    common_errors: List[tuple[str, int]]  # 常见错误（错误类型，出现次数）
    tool_uncertainty_map: Dict[str, float]  # 每个工具的不确定性
    trend: str  # 趋势：improving, stable, worsening
    recommendations: List[str]  # 优化建议


class UncertaintyMonitor:
    """不确定性监控器"""
    
    def __init__(
        self,
        high_uncertainty_threshold: float = 0.5,  # 高不确定性阈值
        low_uncertainty_threshold: float = 0.8  # 低不确定性阈值
    ):
        """
        初始化不确定性监控器
        
        Args:
            high_uncertainty_threshold: 高不确定性阈值（低于此值认为高不确定性）
            low_uncertainty_threshold: 低不确定性阈值（高于此值认为低不确定性）
        """
        self.high_uncertainty_threshold = high_uncertainty_threshold
        self.low_uncertainty_threshold = low_uncertainty_threshold
        self.metrics_history: List[UncertaintyMetrics] = []
        self.error_counter: Dict[str, int] = defaultdict(int)
        self.tool_uncertainty: Dict[str, List[float]] = defaultdict(list)
    
    def record(
        self,
        metrics: UncertaintyMetrics
    ):
        """
        记录不确定性指标
        
        Args:
            metrics: 不确定性指标
        """
        self.metrics_history.append(metrics)
        
        # 更新错误统计
        if metrics.validation_errors > 0:
            self.error_counter["validation_errors"] += metrics.validation_errors
        
        if metrics.validation_warnings > 0:
            self.error_counter["validation_warnings"] += metrics.validation_warnings
        
        # 记录工具不确定性
        if "tool_name" in metrics.additional_info:
            tool_name = metrics.additional_info["tool_name"]
            uncertainty = 1.0 - metrics.confidence_score
            self.tool_uncertainty[tool_name].append(uncertainty)
        
        logger.debug(
            f"Recorded uncertainty metrics: consistency={metrics.consistency_score:.2f}, "
            f"confidence={metrics.confidence_score:.2f}"
        )
    
    def get_report(
        self,
        window_size: Optional[int] = None  # 分析最近N条记录，None表示全部
    ) -> UncertaintyReport:
        """
        生成不确定性报告
        
        Args:
            window_size: 分析窗口大小（最近N条记录）
            
        Returns:
            不确定性报告
        """
        if not self.metrics_history:
            return UncertaintyReport(
                total_requests=0,
                average_consistency=0.0,
                average_confidence=0.0,
                high_uncertainty_count=0,
                low_uncertainty_count=0,
                common_errors=[],
                tool_uncertainty_map={},
                trend="stable",
                recommendations=["暂无数据"]
            )
        
        # 选择要分析的数据
        if window_size:
            metrics_to_analyze = self.metrics_history[-window_size:]
        else:
            metrics_to_analyze = self.metrics_history
        
        total = len(metrics_to_analyze)
        
        # 计算平均一致性
        consistency_scores = [m.consistency_score for m in metrics_to_analyze if m.consistency_score > 0]
        avg_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
        
        # 计算平均置信度
        confidence_scores = [m.confidence_score for m in metrics_to_analyze]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # 统计高/低不确定性
        high_uncertainty = sum(
            1 for m in metrics_to_analyze
            if m.confidence_score < self.high_uncertainty_threshold
        )
        low_uncertainty = sum(
            1 for m in metrics_to_analyze
            if m.confidence_score >= self.low_uncertainty_threshold
        )
        
        # 常见错误
        common_errors = sorted(
            self.error_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # 工具不确定性
        tool_uncertainty_map = {}
        for tool_name, uncertainties in self.tool_uncertainty.items():
            if uncertainties:
                avg_uncertainty = sum(uncertainties) / len(uncertainties)
                tool_uncertainty_map[tool_name] = avg_uncertainty
        
        # 趋势分析
        trend = self._analyze_trend(metrics_to_analyze)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            avg_consistency,
            avg_confidence,
            high_uncertainty,
            total,
            tool_uncertainty_map
        )
        
        return UncertaintyReport(
            total_requests=total,
            average_consistency=avg_consistency,
            average_confidence=avg_confidence,
            high_uncertainty_count=high_uncertainty,
            low_uncertainty_count=low_uncertainty,
            common_errors=common_errors,
            tool_uncertainty_map=tool_uncertainty_map,
            trend=trend,
            recommendations=recommendations
        )
    
    def _analyze_trend(
        self,
        metrics: List[UncertaintyMetrics]
    ) -> str:
        """
        分析趋势
        
        Args:
            metrics: 指标列表
            
        Returns:
            趋势：improving, stable, worsening
        """
        if len(metrics) < 10:
            return "stable"
        
        # 将数据分为两半
        mid = len(metrics) // 2
        first_half = metrics[:mid]
        second_half = metrics[mid:]
        
        # 计算前半部分和后半部分的平均置信度
        first_avg = sum(m.confidence_score for m in first_half) / len(first_half)
        second_avg = sum(m.confidence_score for m in second_half) / len(second_half)
        
        diff = second_avg - first_avg
        
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "worsening"
        else:
            return "stable"
    
    def _generate_recommendations(
        self,
        avg_consistency: float,
        avg_confidence: float,
        high_uncertainty_count: int,
        total: int,
        tool_uncertainty_map: Dict[str, float]
    ) -> List[str]:
        """
        生成优化建议
        
        Args:
            avg_consistency: 平均一致性
            avg_confidence: 平均置信度
            high_uncertainty_count: 高不确定性数量
            total: 总请求数
            tool_uncertainty_map: 工具不确定性映射
            
        Returns:
            建议列表
        """
        recommendations = []
        
        # 一致性建议
        if avg_consistency < 0.7:
            recommendations.append(
                "平均一致性较低，建议使用Self-Consistency机制（增加采样次数）"
            )
        
        # 置信度建议
        if avg_confidence < 0.6:
            recommendations.append(
                "平均置信度较低，建议：1) 降低temperature参数 2) 优化Prompt模板 3) 使用Self-Consistency"
            )
        
        # 高不确定性比例
        high_uncertainty_rate = high_uncertainty_count / total if total > 0 else 0
        if high_uncertainty_rate > 0.3:
            recommendations.append(
                f"高不确定性请求比例较高（{high_uncertainty_rate:.1%}），建议检查Prompt质量和模型参数"
            )
        
        # 工具不确定性
        if tool_uncertainty_map:
            high_uncertainty_tools = [
                tool for tool, uncertainty in tool_uncertainty_map.items()
                if uncertainty > 0.5
            ]
            if high_uncertainty_tools:
                recommendations.append(
                    f"以下工具的不确定性较高：{', '.join(high_uncertainty_tools)}，"
                    "建议在Prompt中提供更明确的工具使用示例"
                )
        
        # 如果没有问题，给出正面反馈
        if not recommendations:
            recommendations.append("不确定性指标良好，系统运行稳定")
        
        return recommendations
    
    def get_tool_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        获取工具统计信息
        
        Returns:
            工具统计信息
        """
        stats = {}
        
        for tool_name, uncertainties in self.tool_uncertainty.items():
            if uncertainties:
                stats[tool_name] = {
                    "count": len(uncertainties),
                    "average_uncertainty": sum(uncertainties) / len(uncertainties),
                    "min_uncertainty": min(uncertainties),
                    "max_uncertainty": max(uncertainties)
                }
        
        return stats
    
    def get_recent_metrics(
        self,
        limit: int = 10
    ) -> List[UncertaintyMetrics]:
        """
        获取最近的指标
        
        Args:
            limit: 返回数量限制
            
        Returns:
            最近的指标列表
        """
        return self.metrics_history[-limit:]
    
    def clear_history(self):
        """清空历史记录"""
        self.metrics_history.clear()
        self.error_counter.clear()
        self.tool_uncertainty.clear()
        logger.info("Uncertainty monitoring history cleared")
    
    def export_report(
        self,
        file_path: str,
        window_size: Optional[int] = None
    ):
        """
        导出报告到文件
        
        Args:
            file_path: 文件路径
            window_size: 分析窗口大小
        """
        report = self.get_report(window_size)
        
        import json
        report_dict = {
            "total_requests": report.total_requests,
            "average_consistency": report.average_consistency,
            "average_confidence": report.average_confidence,
            "high_uncertainty_count": report.high_uncertainty_count,
            "low_uncertainty_count": report.low_uncertainty_count,
            "common_errors": report.common_errors,
            "tool_uncertainty_map": report.tool_uncertainty_map,
            "trend": report.trend,
            "recommendations": report.recommendations
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Uncertainty report exported to {file_path}")


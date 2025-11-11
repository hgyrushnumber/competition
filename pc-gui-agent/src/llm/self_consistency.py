"""
Self-Consistency生成器
实现多次采样和投票机制，提高LLM输出的稳定性和可靠性
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from ..llm.ollama_client import OllamaClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class VotingStrategy(str, Enum):
    """投票策略"""
    MAJORITY = "majority"  # 简单多数投票
    WEIGHTED = "weighted"  # 加权投票
    CLUSTERING = "clustering"  # 聚类投票
    QUALITY_BASED = "quality_based"  # 基于质量的投票


@dataclass
class SampleResult:
    """采样结果"""
    content: str
    parsed_data: Optional[Dict[str, Any]] = None
    is_valid: bool = False
    quality_score: float = 0.0
    parse_error: Optional[str] = None


@dataclass
class ConsistencyResult:
    """一致性结果"""
    best_result: Dict[str, Any]
    consistency_score: float  # 一致性分数 (0-1)
    sample_count: int
    valid_sample_count: int
    voting_details: Dict[str, Any]


class SelfConsistencyGenerator:
    """Self-Consistency生成器"""
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        num_samples: int = 5,
        voting_strategy: VotingStrategy = VotingStrategy.MAJORITY,
        temperature: float = 0.7,
        early_stop_threshold: float = 0.9,  # 如果一致性达到此阈值，提前停止
        parallel: bool = True  # 是否并行采样
    ):
        """
        初始化Self-Consistency生成器
        
        Args:
            ollama_client: Ollama客户端
            num_samples: 采样次数
            voting_strategy: 投票策略
            temperature: 采样温度
            early_stop_threshold: 早期停止阈值（如果一致性达到此值，提前停止）
            parallel: 是否并行采样
        """
        self.ollama_client = ollama_client
        self.num_samples = num_samples
        self.voting_strategy = voting_strategy
        self.temperature = temperature
        self.early_stop_threshold = early_stop_threshold
        self.parallel = parallel
    
    async def generate_with_voting(
        self,
        prompt: str,
        parse_fn: Optional[Callable[[str], Dict[str, Any]]] = None,
        validate_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> ConsistencyResult:
        """
        使用投票机制生成结果
        
        Args:
            prompt: 提示词
            parse_fn: 解析函数，将文本解析为结构化数据（可选）
            validate_fn: 验证函数，验证解析后的数据是否有效（可选）
            
        Returns:
            一致性结果
        """
        logger.info(f"Generating with self-consistency (samples={self.num_samples}, strategy={self.voting_strategy.value})")
        
        # 步骤1：多次采样
        samples = await self._sample_multiple(prompt)
        
        # 步骤2：解析所有样本
        parsed_samples = []
        for sample in samples:
            parsed = self._parse_sample(sample, parse_fn)
            if parsed.is_valid:
                # 验证（如果提供了验证函数）
                if validate_fn:
                    parsed.is_valid = validate_fn(parsed.parsed_data)
                    if not parsed.is_valid:
                        parsed.quality_score = 0.0
                parsed_samples.append(parsed)
            else:
                logger.debug(f"Sample parsing failed: {parsed.parse_error}")
        
        if not parsed_samples:
            logger.warning("All samples failed to parse, returning empty result")
            return ConsistencyResult(
                best_result={},
                consistency_score=0.0,
                sample_count=len(samples),
                valid_sample_count=0,
                voting_details={"error": "All samples failed to parse"}
            )
        
        # 步骤3：计算质量分数
        for parsed in parsed_samples:
            parsed.quality_score = self._calculate_quality_score(parsed)
        
        # 步骤4：投票选择最佳结果
        best_result, voting_details = self._vote(parsed_samples)
        
        # 步骤5：计算一致性分数
        consistency_score = self._calculate_consistency_score(parsed_samples, best_result)
        
        logger.info(
            f"Self-consistency result: consistency={consistency_score:.2f}, "
            f"valid_samples={len(parsed_samples)}/{len(samples)}"
        )
        
        return ConsistencyResult(
            best_result=best_result,
            consistency_score=consistency_score,
            sample_count=len(samples),
            valid_sample_count=len(parsed_samples),
            voting_details=voting_details
        )
    
    async def _sample_multiple(self, prompt: str) -> List[str]:
        """
        多次采样
        
        Args:
            prompt: 提示词
            
        Returns:
            采样结果列表
        """
        if self.parallel:
            # 并行采样
            tasks = [
                self.ollama_client.generate_async(
                    prompt,
                    temperature=self.temperature
                )
                for _ in range(self.num_samples)
            ]
            samples = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 过滤异常
            valid_samples = []
            for sample in samples:
                if isinstance(sample, Exception):
                    logger.warning(f"Sample generation error: {sample}")
                else:
                    valid_samples.append(sample)
            
            return valid_samples
        else:
            # 串行采样（支持早期停止）
            samples = []
            for i in range(self.num_samples):
                sample = await self.ollama_client.generate_async(
                    prompt,
                    temperature=self.temperature
                )
                samples.append(sample)
                
                # 早期停止检查（如果已经有足够的一致性）
                if i >= 2:  # 至少需要3个样本才能判断一致性
                    parsed_samples = [self._parse_sample(s) for s in samples]
                    valid_samples = [p for p in parsed_samples if p.is_valid]
                    if valid_samples:
                        consistency = self._calculate_preliminary_consistency(valid_samples)
                        if consistency >= self.early_stop_threshold:
                            logger.info(f"Early stopping at sample {i+1} (consistency={consistency:.2f})")
                            break
            
            return samples
    
    def _parse_sample(
        self,
        content: str,
        parse_fn: Optional[Callable[[str], Dict[str, Any]]] = None
    ) -> SampleResult:
        """
        解析样本
        
        Args:
            content: 样本内容
            parse_fn: 自定义解析函数（可选）
            
        Returns:
            解析结果
        """
        if parse_fn:
            try:
                parsed_data = parse_fn(content)
                return SampleResult(
                    content=content,
                    parsed_data=parsed_data,
                    is_valid=True
                )
            except Exception as e:
                return SampleResult(
                    content=content,
                    is_valid=False,
                    parse_error=str(e)
                )
        else:
            # 默认JSON解析
            try:
                # 尝试提取JSON
                json_str = self._extract_json(content)
                parsed_data = json.loads(json_str)
                return SampleResult(
                    content=content,
                    parsed_data=parsed_data,
                    is_valid=True
                )
            except Exception as e:
                return SampleResult(
                    content=content,
                    is_valid=False,
                    parse_error=str(e)
                )
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON"""
        text = text.strip()
        
        # 查找markdown代码块
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        
        # 查找JSON对象
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return text
    
    def _calculate_quality_score(self, sample: SampleResult) -> float:
        """
        计算样本质量分数
        
        Args:
            sample: 样本结果
            
        Returns:
            质量分数 (0-1)
        """
        score = 1.0
        
        # 如果解析失败，分数为0
        if not sample.is_valid:
            return 0.0
        
        # 检查数据结构完整性
        if sample.parsed_data:
            # 如果有subtasks字段，检查是否为空
            if "subtasks" in sample.parsed_data:
                if not sample.parsed_data["subtasks"]:
                    score *= 0.5
                else:
                    # 检查每个subtask是否有必要的字段
                    for subtask in sample.parsed_data["subtasks"]:
                        if not isinstance(subtask, dict):
                            score *= 0.8
                        if "actions" not in subtask:
                            score *= 0.8
        
        return score
    
    def _vote(
        self,
        parsed_samples: List[SampleResult]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        投票选择最佳结果
        
        Args:
            parsed_samples: 解析后的样本列表
            
        Returns:
            (最佳结果, 投票详情)
        """
        if self.voting_strategy == VotingStrategy.MAJORITY:
            return self._majority_vote(parsed_samples)
        elif self.voting_strategy == VotingStrategy.WEIGHTED:
            return self._weighted_vote(parsed_samples)
        elif self.voting_strategy == VotingStrategy.CLUSTERING:
            return self._clustering_vote(parsed_samples)
        elif self.voting_strategy == VotingStrategy.QUALITY_BASED:
            return self._quality_based_vote(parsed_samples)
        else:
            return self._majority_vote(parsed_samples)
    
    def _majority_vote(
        self,
        parsed_samples: List[SampleResult]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """简单多数投票"""
        # 统计关键决策的出现频率
        tool_votes = {}
        subtask_counts = {}
        
        for sample in parsed_samples:
            if not sample.parsed_data:
                continue
            
            # 统计工具使用
            if "subtasks" in sample.parsed_data:
                for subtask in sample.parsed_data["subtasks"]:
                    if isinstance(subtask, dict) and "actions" in subtask:
                        for action in subtask["actions"]:
                            if isinstance(action, dict) and "tool" in action:
                                tool = action["tool"]
                                tool_votes[tool] = tool_votes.get(tool, 0) + 1
            
            # 统计subtask数量
            subtask_count = len(sample.parsed_data.get("subtasks", []))
            subtask_counts[subtask_count] = subtask_counts.get(subtask_count, 0) + 1
        
        # 选择最频繁的subtask数量
        most_common_subtask_count = max(subtask_counts.items(), key=lambda x: x[1])[0] if subtask_counts else 0
        
        # 选择包含最频繁工具组合的样本
        best_sample = None
        best_score = 0
        
        for sample in parsed_samples:
            if not sample.parsed_data or "subtasks" not in sample.parsed_data:
                continue
            
            score = 0
            # 如果subtask数量匹配，加分
            if len(sample.parsed_data["subtasks"]) == most_common_subtask_count:
                score += 2
            
            # 统计工具匹配度
            for subtask in sample.parsed_data["subtasks"]:
                if isinstance(subtask, dict) and "actions" in subtask:
                    for action in subtask["actions"]:
                        if isinstance(action, dict) and "tool" in action:
                            tool = action["tool"]
                            if tool in tool_votes:
                                score += tool_votes[tool]
            
            if score > best_score:
                best_score = score
                best_sample = sample
        
        if best_sample and best_sample.parsed_data:
            return best_sample.parsed_data, {
                "strategy": "majority",
                "tool_votes": tool_votes,
                "subtask_counts": subtask_counts,
                "best_score": best_score
            }
        
        # 如果没有找到，返回第一个有效样本
        for sample in parsed_samples:
            if sample.parsed_data:
                return sample.parsed_data, {"strategy": "majority", "fallback": True}
        
        return {}, {"strategy": "majority", "error": "No valid samples"}
    
    def _weighted_vote(
        self,
        parsed_samples: List[SampleResult]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """加权投票（根据质量分数）"""
        # 按质量分数加权
        weighted_samples = []
        for sample in parsed_samples:
            if sample.parsed_data:
                weight = sample.quality_score
                weighted_samples.append((sample.parsed_data, weight))
        
        if not weighted_samples:
            return {}, {"strategy": "weighted", "error": "No valid samples"}
        
        # 选择质量分数最高的
        best_data, best_weight = max(weighted_samples, key=lambda x: x[1])
        
        return best_data, {
            "strategy": "weighted",
            "best_weight": best_weight,
            "weights": [w for _, w in weighted_samples]
        }
    
    def _clustering_vote(
        self,
        parsed_samples: List[SampleResult]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """聚类投票（将相似结果聚类，选择最大簇）"""
        # 简化实现：使用简单相似度计算
        clusters = []
        used = set()
        
        for i, sample1 in enumerate(parsed_samples):
            if i in used or not sample1.parsed_data:
                continue
            
            cluster = [sample1]
            used.add(i)
            
            for j, sample2 in enumerate(parsed_samples[i+1:], start=i+1):
                if j in used or not sample2.parsed_data:
                    continue
                
                # 计算相似度
                similarity = self._calculate_similarity(
                    sample1.parsed_data,
                    sample2.parsed_data
                )
                
                if similarity > 0.7:  # 相似度阈值
                    cluster.append(sample2)
                    used.add(j)
            
            clusters.append(cluster)
        
        if not clusters:
            return {}, {"strategy": "clustering", "error": "No valid samples"}
        
        # 选择最大的簇
        largest_cluster = max(clusters, key=len)
        # 选择质量分数最高的作为代表
        best_sample = max(largest_cluster, key=lambda s: s.quality_score)
        
        return best_sample.parsed_data, {
            "strategy": "clustering",
            "cluster_count": len(clusters),
            "largest_cluster_size": len(largest_cluster),
            "similarity_threshold": 0.7
        }
    
    def _quality_based_vote(
        self,
        parsed_samples: List[SampleResult]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """基于质量的投票（结合频率和质量）"""
        # 统计频率
        sample_counts = {}
        for sample in parsed_samples:
            if not sample.parsed_data:
                continue
            # 使用JSON字符串作为key（简化）
            key = json.dumps(sample.parsed_data, sort_keys=True)
            sample_counts[key] = sample_counts.get(key, []) + [sample]
        
        # 计算每个唯一结果的综合分数
        scored_results = []
        for key, samples in sample_counts.items():
            frequency = len(samples) / len(parsed_samples)
            avg_quality = sum(s.quality_score for s in samples) / len(samples)
            # 综合分数 = 频率 * 0.4 + 质量 * 0.6
            combined_score = frequency * 0.4 + avg_quality * 0.6
            scored_results.append((samples[0].parsed_data, combined_score, frequency, avg_quality))
        
        if not scored_results:
            return {}, {"strategy": "quality_based", "error": "No valid samples"}
        
        # 选择综合分数最高的
        best_data, best_score, freq, qual = max(scored_results, key=lambda x: x[1])
        
        return best_data, {
            "strategy": "quality_based",
            "best_score": best_score,
            "frequency": freq,
            "quality": qual
        }
    
    def _calculate_similarity(
        self,
        data1: Dict[str, Any],
        data2: Dict[str, Any]
    ) -> float:
        """计算两个数据结构的相似度"""
        # 简化实现：比较关键字段
        if not data1 or not data2:
            return 0.0
        
        score = 0.0
        total = 0.0
        
        # 比较subtasks数量
        subtasks1 = data1.get("subtasks", [])
        subtasks2 = data2.get("subtasks", [])
        if len(subtasks1) == len(subtasks2):
            score += 0.3
        total += 0.3
        
        # 比较工具使用
        tools1 = set()
        tools2 = set()
        for subtask in subtasks1:
            if isinstance(subtask, dict) and "actions" in subtask:
                for action in subtask["actions"]:
                    if isinstance(action, dict) and "tool" in action:
                        tools1.add(action["tool"])
        
        for subtask in subtasks2:
            if isinstance(subtask, dict) and "actions" in subtask:
                for action in subtask["actions"]:
                    if isinstance(action, dict) and "tool" in action:
                        tools2.add(action["tool"])
        
        if tools1 and tools2:
            intersection = len(tools1 & tools2)
            union = len(tools1 | tools2)
            if union > 0:
                score += 0.7 * (intersection / union)
        total += 0.7
        
        return score / total if total > 0 else 0.0
    
    def _calculate_consistency_score(
        self,
        parsed_samples: List[SampleResult],
        best_result: Dict[str, Any]
    ) -> float:
        """计算一致性分数"""
        if not parsed_samples or not best_result:
            return 0.0
        
        # 计算所有样本与最佳结果的相似度
        similarities = []
        for sample in parsed_samples:
            if sample.parsed_data:
                similarity = self._calculate_similarity(sample.parsed_data, best_result)
                similarities.append(similarity)
        
        if not similarities:
            return 0.0
        
        # 一致性分数 = 平均相似度
        return sum(similarities) / len(similarities)
    
    def _calculate_preliminary_consistency(
        self,
        parsed_samples: List[SampleResult]
    ) -> float:
        """计算初步一致性（用于早期停止）"""
        if len(parsed_samples) < 2:
            return 0.0
        
        # 计算所有样本对之间的相似度
        similarities = []
        for i in range(len(parsed_samples)):
            for j in range(i + 1, len(parsed_samples)):
                if parsed_samples[i].parsed_data and parsed_samples[j].parsed_data:
                    similarity = self._calculate_similarity(
                        parsed_samples[i].parsed_data,
                        parsed_samples[j].parsed_data
                    )
                    similarities.append(similarity)
        
        if not similarities:
            return 0.0
        
        return sum(similarities) / len(similarities)


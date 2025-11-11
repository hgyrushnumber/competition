"""
错误处理器模块
提供错误分类、恢复策略和错误上下文记录
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ErrorType(str, Enum):
    """错误类型"""
    TIMEOUT = "timeout"  # 超时错误
    ELEMENT_NOT_FOUND = "element_not_found"  # 元素未找到
    PERMISSION_DENIED = "permission_denied"  # 权限错误
    NETWORK_ERROR = "network_error"  # 网络错误
    JSON_PARSE_ERROR = "json_parse_error"  # JSON解析错误
    TOOL_EXECUTION_ERROR = "tool_execution_error"  # 工具执行错误
    VALIDATION_ERROR = "validation_error"  # 验证错误
    UNKNOWN_ERROR = "unknown_error"  # 未知错误


class RecoveryStrategy(str, Enum):
    """恢复策略"""
    RETRY = "retry"  # 重试
    SKIP = "skip"  # 跳过
    ABORT = "abort"  # 中止
    FALLBACK = "fallback"  # 回退到备用方案
    MANUAL_INTERVENTION = "manual_intervention"  # 需要人工干预


@dataclass
class ErrorContext:
    """错误上下文"""
    error_type: ErrorType
    error_message: str
    original_exception: Optional[Exception] = None
    action_id: Optional[str] = None
    tool_name: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    stack_trace: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryAction:
    """恢复动作"""
    strategy: RecoveryStrategy
    should_retry: bool = False
    retry_delay: float = 1.0  # 重试延迟（秒）
    max_retries: int = 3
    fallback_action: Optional[Any] = None
    message: str = ""
    confidence: float = 0.0  # 恢复策略的置信度 (0-1)


class ErrorHandler:
    """错误处理器"""
    
    # 错误类型到恢复策略的映射
    ERROR_RECOVERY_MAP: Dict[ErrorType, RecoveryStrategy] = {
        ErrorType.TIMEOUT: RecoveryStrategy.RETRY,
        ErrorType.ELEMENT_NOT_FOUND: RecoveryStrategy.RETRY,
        ErrorType.NETWORK_ERROR: RecoveryStrategy.RETRY,
        ErrorType.TOOL_EXECUTION_ERROR: RecoveryStrategy.RETRY,
        ErrorType.JSON_PARSE_ERROR: RecoveryStrategy.FALLBACK,
        ErrorType.PERMISSION_DENIED: RecoveryStrategy.ABORT,
        ErrorType.VALIDATION_ERROR: RecoveryStrategy.ABORT,
        ErrorType.UNKNOWN_ERROR: RecoveryStrategy.MANUAL_INTERVENTION,
    }
    
    # 错误关键词匹配规则
    ERROR_KEYWORDS: Dict[ErrorType, List[str]] = {
        ErrorType.TIMEOUT: ["timeout", "超时", "timed out", "time out"],
        ErrorType.ELEMENT_NOT_FOUND: [
            "not found", "未找到", "找不到", "element not found",
            "selector not found", "no such element"
        ],
        ErrorType.PERMISSION_DENIED: [
            "permission", "权限", "denied", "forbidden", "access denied"
        ],
        ErrorType.NETWORK_ERROR: [
            "network", "网络", "connection", "连接", "failed to connect",
            "connection refused", "connection timeout"
        ],
        ErrorType.JSON_PARSE_ERROR: [
            "json", "parse", "解析", "decode", "invalid json",
            "json decode error"
        ],
        ErrorType.TOOL_EXECUTION_ERROR: [
            "tool", "工具", "execution", "执行", "failed to execute"
        ],
        ErrorType.VALIDATION_ERROR: [
            "validation", "验证", "invalid", "无效", "validate"
        ],
    }
    
    def __init__(self):
        """初始化错误处理器"""
        self.error_history: List[ErrorContext] = []
    
    def classify_error(
        self,
        error: Exception,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorType:
        """
        分类错误
        
        Args:
            error: 异常对象
            error_message: 错误消息（可选）
            context: 上下文信息（可选）
            
        Returns:
            错误类型
        """
        error_msg = error_message or str(error)
        error_msg_lower = error_msg.lower()
        
        # 检查错误类型
        error_type_name = type(error).__name__
        
        # 根据异常类型判断
        if "Timeout" in error_type_name or "timeout" in error_type_name:
            return ErrorType.TIMEOUT
        
        if "JSON" in error_type_name or "json" in error_type_name:
            return ErrorType.JSON_PARSE_ERROR
        
        if "Permission" in error_type_name or "Forbidden" in error_type_name:
            return ErrorType.PERMISSION_DENIED
        
        if "Network" in error_type_name or "Connection" in error_type_name:
            return ErrorType.NETWORK_ERROR
        
        # 根据错误消息关键词匹配
        for error_type, keywords in self.ERROR_KEYWORDS.items():
            if any(keyword in error_msg_lower for keyword in keywords):
                return error_type
        
        # 默认返回未知错误
        return ErrorType.UNKNOWN_ERROR
    
    def create_error_context(
        self,
        error: Exception,
        error_type: Optional[ErrorType] = None,
        action_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """
        创建错误上下文
        
        Args:
            error: 异常对象
            error_type: 错误类型（可选，会自动分类）
            action_id: 动作ID（可选）
            tool_name: 工具名称（可选）
            args: 工具参数（可选）
            retry_count: 重试次数
            additional_info: 额外信息（可选）
            
        Returns:
            错误上下文对象
        """
        if error_type is None:
            error_type = self.classify_error(error)
        
        import traceback
        stack_trace = traceback.format_exc()
        
        error_context = ErrorContext(
            error_type=error_type,
            error_message=str(error),
            original_exception=error,
            action_id=action_id,
            tool_name=tool_name,
            args=args or {},
            retry_count=retry_count,
            stack_trace=stack_trace,
            additional_info=additional_info or {}
        )
        
        # 记录错误历史
        self.error_history.append(error_context)
        
        return error_context
    
    def get_recovery_strategy(
        self,
        error_context: ErrorContext,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> RecoveryAction:
        """
        获取恢复策略
        
        Args:
            error_context: 错误上下文
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            恢复动作
        """
        error_type = error_context.error_type
        retry_count = error_context.retry_count
        
        # 获取默认恢复策略
        default_strategy = self.ERROR_RECOVERY_MAP.get(
            error_type,
            RecoveryStrategy.MANUAL_INTERVENTION
        )
        
        # 如果已经达到最大重试次数，改变策略
        if retry_count >= max_retries:
            if default_strategy == RecoveryStrategy.RETRY:
                # 重试失败后，尝试跳过或中止
                if error_type in [ErrorType.TIMEOUT, ErrorType.NETWORK_ERROR]:
                    default_strategy = RecoveryStrategy.SKIP
                else:
                    default_strategy = RecoveryStrategy.ABORT
        
        # 根据错误类型和重试次数调整策略
        should_retry = (
            default_strategy == RecoveryStrategy.RETRY and
            retry_count < max_retries
        )
        
        # 计算置信度
        confidence = self._calculate_confidence(error_context, default_strategy)
        
        # 生成恢复消息
        message = self._generate_recovery_message(error_context, default_strategy)
        
        return RecoveryAction(
            strategy=default_strategy,
            should_retry=should_retry,
            retry_delay=retry_delay,
            max_retries=max_retries,
            message=message,
            confidence=confidence
        )
    
    def _calculate_confidence(
        self,
        error_context: ErrorContext,
        strategy: RecoveryStrategy
    ) -> float:
        """
        计算恢复策略的置信度
        
        Args:
            error_context: 错误上下文
            strategy: 恢复策略
            
        Returns:
            置信度 (0-1)
        """
        # 基础置信度
        base_confidence = {
            RecoveryStrategy.RETRY: 0.7,
            RecoveryStrategy.SKIP: 0.5,
            RecoveryStrategy.ABORT: 0.9,
            RecoveryStrategy.FALLBACK: 0.6,
            RecoveryStrategy.MANUAL_INTERVENTION: 0.3,
        }.get(strategy, 0.5)
        
        # 根据错误类型调整
        error_type = error_context.error_type
        if error_type in [ErrorType.TIMEOUT, ErrorType.NETWORK_ERROR]:
            # 网络和超时错误，重试的置信度较高
            if strategy == RecoveryStrategy.RETRY:
                base_confidence = 0.8
        elif error_type == ErrorType.PERMISSION_DENIED:
            # 权限错误，重试无效
            if strategy == RecoveryStrategy.ABORT:
                base_confidence = 0.95
        
        # 根据重试次数调整
        if error_context.retry_count > 0:
            # 已经重试过，置信度降低
            base_confidence *= 0.9
        
        return min(1.0, max(0.0, base_confidence))
    
    def _generate_recovery_message(
        self,
        error_context: ErrorContext,
        strategy: RecoveryStrategy
    ) -> str:
        """
        生成恢复消息
        
        Args:
            error_context: 错误上下文
            strategy: 恢复策略
            
        Returns:
            恢复消息
        """
        error_type = error_context.error_type
        retry_count = error_context.retry_count
        
        messages = {
            RecoveryStrategy.RETRY: f"检测到{error_type.value}错误，将重试（第{retry_count + 1}次）",
            RecoveryStrategy.SKIP: f"检测到{error_type.value}错误，跳过当前步骤",
            RecoveryStrategy.ABORT: f"检测到{error_type.value}错误，中止任务执行",
            RecoveryStrategy.FALLBACK: f"检测到{error_type.value}错误，使用备用方案",
            RecoveryStrategy.MANUAL_INTERVENTION: f"检测到{error_type.value}错误，需要人工干预",
        }
        
        return messages.get(strategy, "未知错误，需要处理")
    
    def should_retry(
        self,
        error_context: ErrorContext,
        max_retries: int = 3
    ) -> bool:
        """
        判断是否应该重试
        
        Args:
            error_context: 错误上下文
            max_retries: 最大重试次数
            
        Returns:
            是否应该重试
        """
        if error_context.retry_count >= max_retries:
            return False
        
        recovery_action = self.get_recovery_strategy(error_context, max_retries)
        return recovery_action.should_retry
    
    def get_retry_delay(
        self,
        error_context: ErrorContext,
        base_delay: float = 1.0,
        use_exponential_backoff: bool = True
    ) -> float:
        """
        获取重试延迟（支持指数退避）
        
        Args:
            error_context: 错误上下文
            base_delay: 基础延迟（秒）
            use_exponential_backoff: 是否使用指数退避
            
        Returns:
            重试延迟（秒）
        """
        if not use_exponential_backoff:
            return base_delay
        
        # 指数退避：delay = base_delay * (2 ^ retry_count)
        retry_count = error_context.retry_count
        delay = base_delay * (2 ** retry_count)
        
        # 最大延迟限制为60秒
        return min(delay, 60.0)
    
    def get_error_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取错误摘要
        
        Args:
            limit: 返回的错误数量限制
            
        Returns:
            错误摘要列表
        """
        recent_errors = self.error_history[-limit:]
        
        return [
            {
                "error_type": error.error_type.value,
                "error_message": error.error_message,
                "action_id": error.action_id,
                "tool_name": error.tool_name,
                "retry_count": error.retry_count,
                "timestamp": error.timestamp.isoformat(),
            }
            for error in recent_errors
        ]
    
    def clear_history(self):
        """清空错误历史"""
        self.error_history.clear()
        logger.info("Error history cleared")


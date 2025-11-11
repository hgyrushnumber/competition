"""
记忆模块
"""
import aiosqlite
import json
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from .types import MemoryEntry, ToolUsage, Task
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Memory:
    """记忆模块"""
    
    def __init__(self, database_path: str = "./data/memory.db"):
        """
        初始化记忆模块
        
        Args:
            database_path: 数据库路径
        """
        self.database_path = database_path
        self._ensure_db_dir()
    
    def _ensure_db_dir(self) -> None:
        """确保数据库目录存在"""
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """初始化数据库"""
        async with aiosqlite.connect(self.database_path) as db:
            # 任务记忆表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS task_memories (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    task_goal TEXT NOT NULL,
                    task_result TEXT NOT NULL,
                    reflection TEXT,
                    tool_usage TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # 工具使用记录表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tool_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    execution_time REAL NOT NULL,
                    error TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            
            await db.commit()
            logger.info("Memory database initialized")
    
    async def store_task(
        self,
        task: Task,
        task_result: Dict[str, Any],
        reflection: Optional[Dict[str, Any]] = None,
        tool_usage: List[ToolUsage] = None
    ) -> None:
        """
        存储任务记忆
        
        Args:
            task: 任务对象
            task_result: 任务结果
            reflection: 反思结果（可选）
            tool_usage: 工具使用记录（可选）
        """
        tool_usage_list = [
            {
                "tool_name": tu.tool_name,
                "success": tu.success,
                "execution_time": tu.execution_time,
                "error": tu.error,
                "timestamp": tu.timestamp.isoformat()
            }
            for tu in (tool_usage or [])
        ]
        
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO task_memories 
                (id, task_id, task_goal, task_result, reflection, tool_usage, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"memory_{task.id}",
                task.id,
                task.goal,
                json.dumps(task_result, ensure_ascii=False),
                json.dumps(reflection, ensure_ascii=False) if reflection else None,
                json.dumps(tool_usage_list, ensure_ascii=False),
                datetime.now().isoformat()
            ))
            await db.commit()
            logger.info(f"Stored task memory: {task.id}")
    
    async def retrieve_similar_tasks(
        self,
        goal: str,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """
        检索相似任务
        
        Args:
            goal: 目标描述
            limit: 返回数量限制
            
        Returns:
            相似任务记忆列表
        """
        async with aiosqlite.connect(self.database_path) as db:
            # 简单的关键词匹配（后续可以改进为向量相似度）
            keywords = goal.lower().split()
            
            query = """
                SELECT * FROM task_memories
                WHERE task_goal LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """
            
            # 构建LIKE查询（简单实现）
            like_pattern = f"%{keywords[0]}%" if keywords else "%"
            
            async with db.execute(query, (like_pattern, limit)) as cursor:
                rows = await cursor.fetchall()
                
                memories = []
                for row in rows:
                    memory = MemoryEntry(
                        id=row[0],
                        task_id=row[1],
                        task_goal=row[2],
                        task_result=json.loads(row[3]),
                        reflection=json.loads(row[4]) if row[4] else None,
                        tool_usage=json.loads(row[5]) if row[5] else [],
                        created_at=datetime.fromisoformat(row[6])
                    )
                    memories.append(memory)
                
                return memories
    
    async def store_tool_usage(self, tool_usage: ToolUsage) -> None:
        """
        存储工具使用记录
        
        Args:
            tool_usage: 工具使用记录
        """
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute("""
                INSERT INTO tool_usage 
                (tool_name, success, execution_time, error, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tool_usage.tool_name,
                1 if tool_usage.success else 0,
                tool_usage.execution_time,
                tool_usage.error,
                tool_usage.timestamp.isoformat()
            ))
            await db.commit()
    
    async def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取工具统计信息
        
        Args:
            tool_name: 工具名称（可选，None表示所有工具）
            
        Returns:
            统计信息
        """
        async with aiosqlite.connect(self.database_path) as db:
            if tool_name:
                query = """
                    SELECT 
                        COUNT(*) as total,
                        SUM(success) as success_count,
                        AVG(execution_time) as avg_time
                    FROM tool_usage
                    WHERE tool_name = ?
                """
                async with db.execute(query, (tool_name,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        return {
                            "tool_name": tool_name,
                            "total": row[0],
                            "success_count": row[1],
                            "success_rate": row[1] / row[0] if row[0] > 0 else 0,
                            "avg_execution_time": row[2]
                        }
            else:
                query = """
                    SELECT 
                        tool_name,
                        COUNT(*) as total,
                        SUM(success) as success_count,
                        AVG(execution_time) as avg_time
                    FROM tool_usage
                    GROUP BY tool_name
                """
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    stats = {}
                    for row in rows:
                        stats[row[0]] = {
                            "total": row[1],
                            "success_count": row[2],
                            "success_rate": row[2] / row[1] if row[1] > 0 else 0,
                            "avg_execution_time": row[3]
                        }
                    return stats
            
            return {}
    
    async def get_work_memory(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作记忆（当前任务上下文）
        
        Args:
            task_id: 任务ID
            
        Returns:
            工作记忆字典
        """
        async with aiosqlite.connect(self.database_path) as db:
            async with db.execute("""
                SELECT task_result, reflection, tool_usage
                FROM task_memories
                WHERE task_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (task_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "task_result": json.loads(row[0]),
                        "reflection": json.loads(row[1]) if row[1] else None,
                        "tool_usage": json.loads(row[2]) if row[2] else []
                    }
                return None


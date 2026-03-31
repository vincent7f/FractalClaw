"""
对话历史记录器

记录用户与智能体的所有对话
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


class HistoryRecorder:
    """
    对话历史记录器
    
    将所有对话记录到指定文件
    """
    
    def __init__(self, log_file: str = "docs/prompts/histories.log"):
        self.log_file = log_file
        self._ensure_directory()
    
    def _ensure_directory(self):
        """确保目录存在"""
        path = Path(self.log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
    
    def record(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        记录单条对话
        
        Args:
            role: 角色 (user/assistant/system)
            content: 对话内容
            metadata: 附加元数据
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        self._append_entry(entry)
    
    def _append_entry(self, entry: Dict[str, Any]):
        """追加记录"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def record_user(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """记录用户消息"""
        self.record("user", content, metadata)
    
    def record_assistant(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """记录助手消息"""
        self.record("assistant", content, metadata)
    
    def record_system(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """记录系统消息"""
        self.record("system", content, metadata)
    
    def read_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        读取历史记录
        
        Args:
            limit: 限制返回条数
            
        Returns:
            对话历史列表
        """
        if not os.path.exists(self.log_file):
            return []
        
        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        if limit:
            return entries[-limit:]
        return entries
    
    def clear(self):
        """清空历史记录"""
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        history = self.read_history()
        
        return {
            "total_entries": len(history),
            "user_messages": sum(1 for e in history if e.get("role") == "user"),
            "assistant_messages": sum(1 for e in history if e.get("role") == "assistant"),
            "system_messages": sum(1 for e in history if e.get("role") == "system"),
            "first_entry": history[0]["timestamp"] if history else None,
            "last_entry": history[-1]["timestamp"] if history else None,
        }


# 全局记录器实例
_recorder: Optional[HistoryRecorder] = None


def get_recorder(log_file: str = "docs/prompts/histories.log") -> HistoryRecorder:
    """获取全局记录器"""
    global _recorder
    if _recorder is None:
        _recorder = HistoryRecorder(log_file)
    return _recorder


def record_conversation(role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
    """快捷记录函数"""
    get_recorder().record(role, content, metadata)


def record_user_message(content: str, metadata: Optional[Dict[str, Any]] = None):
    """记录用户消息"""
    get_recorder().record_user(content, metadata)


def record_assistant_message(content: str, metadata: Optional[Dict[str, Any]] = None):
    """记录助手消息"""
    get_recorder().record_assistant(content, metadata)


def record_system_message(content: str, metadata: Optional[Dict[str, Any]] = None):
    """记录系统消息"""
    get_recorder().record_system(content, metadata)


def read_conversation_history(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """读取对话历史"""
    return get_recorder().read_history(limit)

"""
Auto-commit script: 监视文件变化并自动提交到 Git
使用方法: python auto_commit.py
"""
import os
import time
import subprocess
import signal
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class GitAutoCommitHandler(FileSystemEventHandler):
    """Git 自动提交处理器"""

    def __init__(self, repo_path: str, ignore_patterns: list = None):
        self.repo_path = repo_path
        self.ignore_patterns = ignore_patterns or [
            '.git', '.codebuddy', '__pycache__', '.pyc',
            '.db', '.log', '.venv', 'node_modules'
        ]
        self.last_commit_time = 0
        self.debounce_seconds = 2  # 防抖：2秒内的变化视为同一次
        self.pending_changes = False

    def should_ignore(self, path: str) -> bool:
        """检查是否应该忽略该文件"""
        path_lower = path.lower()
        for pattern in self.ignore_patterns:
            if pattern.lower() in path_lower:
                return True
        return False

    def get_changed_files(self) -> list:
        """获取已更改的文件列表"""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                files = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        # 格式: XY filename (XY 是状态，如 M, A, D 等)
                        filename = line[3:] if len(line) > 2 else line
                        files.append(filename)
                return files
        except Exception as e:
            print(f"获取变更文件失败: {e}")
        return []

    def commit_changes(self, event_type: str = "update"):
        """提交所有更改"""
        # 防抖检查
        current_time = time.time()
        if current_time - self.last_commit_time < self.debounce_seconds:
            self.pending_changes = True
            return
        
        changed_files = self.get_changed_files()
        if not changed_files:
            return

        # 创建提交信息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"Auto-commit: {event_type} at {timestamp}\n\nChanges: {', '.join(changed_files[:5])}"
        if len(changed_files) > 5:
            commit_msg += f" ... and {len(changed_files) - 5} more"

        try:
            # Add all changes
            subprocess.run(['git', 'add', '-A'], cwd=self.repo_path, timeout=10)
            # Commit
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=self.repo_path,
                timeout=10
            )
            self.last_commit_time = current_time
            print(f"✓ Auto-committed at {timestamp}")
            print(f"  Files: {', '.join(changed_files[:3])}{'...' if len(changed_files) > 3 else ''}")
        except subprocess.TimeoutExpired:
            print("✗ Commit timeout")
        except Exception as e:
            print(f"✗ Commit failed: {e}")

    def on_modified(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            print(f"Modified: {event.src_path}")
            self.commit_changes("modified")

    def on_created(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            print(f"Created: {event.src_path}")
            self.commit_changes("created")

    def on_deleted(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            print(f"Deleted: {event.src_path}")
            self.commit_changes("deleted")

    def on_moved(self, event):
        if not event.is_directory and not self.should_ignore(event.dest_path):
            print(f"Moved: {event.src_path} -> {event.dest_path}")
            self.commit_changes("moved")


def main():
    repo_path = os.path.dirname(os.path.abspath(__file__))
    print(f"Watching: {repo_path}")
    print("Press Ctrl+C to stop")

    event_handler = GitAutoCommitHandler(repo_path)
    observer = Observer()
    observer.schedule(event_handler, repo_path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped")
    observer.join()


if __name__ == "__main__":
    main()

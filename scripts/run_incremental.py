#!/usr/bin/env python3
"""
简单的定时增量采集入口（不经 MCP）

- 读取 .env（若存在）
- 使用 WorkflowOrchestrator 直接执行工作流
- 默认仅采集+下载（识别/复制关闭，适合高频增量）
- 通过 fcntl 文件锁避免并发重叠执行（Linux/macOS）
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # 可选依赖，失败不致命

# 将 src 加入路径（scripts/ 上一级为项目根）
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from orchestrator.workflow_orchestrator import WorkflowOrchestrator  # noqa: E402
from core.settings import settings  # noqa: E402


def setup_logging(log_file: Path | None):
    log_level = getattr(logging, settings.logging.level, logging.INFO)
    log_format = settings.logging.format
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)


class FileLock:
    """简单文件锁，防止并发重复执行（Unix）。"""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._fh = None

    def acquire(self) -> bool:
        try:
            import fcntl  # Unix only
        except Exception:
            return True  # Windows 或缺少 fcntl 时直接放行

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "w")
        try:
            fcntl.flock(self._fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._fh.write(str(os.getpid()))
            self._fh.flush()
            return True
        except Exception:
            return False

    def release(self):
        try:
            import fcntl
            if self._fh:
                fcntl.flock(self._fh, fcntl.LOCK_UN)
        finally:
            if self._fh:
                try:
                    self._fh.close()
                except Exception:
                    pass


async def run_incremental(channel_url: str, max_posts: int | None, enable_recognition: bool, enable_copy: bool) -> int:
    logger = logging.getLogger(__name__)
    orchestrator = WorkflowOrchestrator()

    max_posts_effective = max_posts or settings.scraping.max_posts
    logger.info(
        f"[cron] 开始执行: url={channel_url}, max_posts={max_posts_effective}, "
        f"recognition={enable_recognition}, copy={enable_copy}"
    )

    start = datetime.now()
    try:
        result = await orchestrator.execute_complete_workflow(
            channel_url=channel_url,
            max_posts=max_posts_effective,
            enable_recognition=enable_recognition,
            enable_copy=enable_copy,
        )

        duration = (datetime.now() - start).total_seconds()
        if result.get("success"):
            summary = result.get("summary", {})
            phases = summary.get("phases", {})
            dl = phases.get("download", {})
            logger.info(
                "[cron] 成功 | images=%s duration=%.2fs dir=%s",
                dl.get("images_count"),
                duration,
                result.get("detailed_results", {}).get("download", {}).get("data", {}).get("download_directory"),
            )
            return 0
        else:
            logger.error("[cron] 失败: %s", result.get("message"))
            if result.get("error"):
                logger.error("[cron] 错误: %s", result["error"]) 
            return 2
    except Exception as e:
        logger.exception("[cron] 执行异常: %s", e)
        return 3


def main():
    if load_dotenv:
        # 读取 .env（若存在）
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

    parser = argparse.ArgumentParser(description="QQChannelMCP 定时增量采集入口（不经 MCP）")
    parser.add_argument("--channel-url", default="https://pd.qq.com/g/5yy11f95s1", help="频道链接")
    parser.add_argument("--max-posts", type=int, default=None, help="最大采集帖子数（默认用 settings.scraping.max_posts）")
    parser.add_argument("--recognition", action="store_true", help="启用识别（默认关闭）")
    parser.add_argument("--copy", action="store_true", help="启用复制（默认关闭）")
    parser.add_argument("--log-file", default=str(PROJECT_ROOT / "logs/cron.log"), help="日志文件路径")
    parser.add_argument("--no-lock", action="store_true", help="不使用文件锁（允许并发）")
    args = parser.parse_args()

    setup_logging(Path(args.log_file) if args.log_file else None)

    lock = None
    if not args.no_lock:
        lock = FileLock(Path(PROJECT_ROOT / "logs/cron.lock"))
        if not lock.acquire():
            print("已有实例在运行，跳过本次执行。", file=sys.stderr)
            sys.exit(10)

    try:
        exit_code = asyncio.run(
            run_incremental(
                channel_url=args.channel_url,
                max_posts=args.max_posts,
                enable_recognition=args.recognition,
                enable_copy=args.copy,
            )
        )
        sys.exit(exit_code)
    finally:
        if lock:
            lock.release()


if __name__ == "__main__":
    main()


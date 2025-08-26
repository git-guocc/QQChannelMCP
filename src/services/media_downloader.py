#!/usr/bin/env python3
"""
最小可用的媒体下载器（仅图片/GIF）
- 并发下载、基本重试、去重
- 跳过视频
"""

import asyncio
import logging
import os
from dataclasses import dataclass
import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Set

import aiohttp

from models.post import QQChannelPost
from utils.directory_manager import DirectoryManager

logger = logging.getLogger(__name__)


@dataclass
class DownloadItemResult:
    url: str
    success: bool
    file_path: Optional[str] = None
    bytes: int = 0
    error: Optional[str] = None


class MediaDownloader:
    """图片/GIF 下载器"""

    def __init__(self, base_dayupdate_dir: str = "data/dayupdate", timeout: int = 20, concurrency: int = 8, retries: int = 2):
        self.directory_manager = DirectoryManager(base_dayupdate_dir)
        self.timeout = timeout
        self.concurrency = concurrency
        self.retries = retries

    async def download_posts_media(self, posts: List[QQChannelPost]) -> Dict[str, Any]:
        """下载一批帖子中的图片和GIF"""
        total_images = sum(len(getattr(p, 'images', [])) for p in posts)
        total_gifs = sum(len(getattr(p, 'gifs', [])) for p in posts)

        # 复用当日目录，避免同一天多次运行创建多个目录
        dest_dir = self.directory_manager.get_today_directory(posts_count=None)
        images_dir = dest_dir / "images"
        gifs_dir = dest_dir / "gifs"

        # 读取 manifest.json（跨运行去重/统计）
        manifest = self._load_manifest(dest_dir)
        processed_posts: Set[str] = set(manifest.get("processed_post_ids", []))

        # 去重 URL
        image_urls: List[Tuple[QQChannelPost, str, int]] = []
        gif_urls: List[Tuple[QQChannelPost, str, int]] = []
        seen: Set[str] = set()
        for post in posts:
            for idx, url in enumerate(getattr(post, 'images', []) or []):
                if url and url not in seen:
                    seen.add(url)
                    image_urls.append((post, url, idx))
            for idx, url in enumerate(getattr(post, 'gifs', []) or []):
                if url and url not in seen:
                    seen.add(url)
                    gif_urls.append((post, url, idx))

        # 下载
        image_results = await self._download_many(image_urls, images_dir, kind="image")
        gif_results = await self._download_many(gif_urls, gifs_dir, kind="gif")

        all_results = image_results + gif_results
        downloaded = [r for r in all_results if r.success]
        failed = [r for r in all_results if not r.success]
        total_size = sum(r.bytes for r in downloaded)

        # 更新 manifest 统计
        manifest["last_run"] = datetime.now().isoformat()
        # 合并处理过的 post_id（本轮所有出现过的）
        for p in posts:
            if getattr(p, 'post_id', None):
                processed_posts.add(p.post_id)
        manifest["processed_post_ids"] = sorted(processed_posts)
        # 更新文件级统计（累计）
        manifest["total_images"] = manifest.get("total_images", 0) + total_images
        manifest["total_gifs"] = manifest.get("total_gifs", 0) + total_gifs
        manifest["downloaded_files_sum"] = manifest.get("downloaded_files_sum", 0) + len(downloaded)
        manifest["failed_files_sum"] = manifest.get("failed_files_sum", 0) + len(failed)
        manifest["total_size_sum"] = manifest.get("total_size_sum", 0) + total_size
        self._save_manifest(dest_dir, manifest)

        return {
            "download_directory": str(dest_dir),
            "images_dir": str(images_dir),
            "gifs_dir": str(gifs_dir),
            "total_images": total_images,
            "total_gifs": total_gifs,
            "attempted": len(all_results),
            "downloaded_files": len(downloaded),
            "failed_files": len(failed),
            "total_size": total_size,
            "manifest": manifest,
            "results": [r.__dict__ for r in all_results],
        }

    async def _download_many(self, items: List[Tuple[QQChannelPost, str, int]], dest_dir: Path, kind: str) -> List[DownloadItemResult]:
        sem = asyncio.Semaphore(self.concurrency)
        dest_dir.mkdir(parents=True, exist_ok=True)

        async def worker(post: QQChannelPost, url: str, idx: int) -> DownloadItemResult:
            async with sem:
                return await self._download_one(post, url, idx, dest_dir, kind)

        tasks = [worker(p, u, i) for (p, u, i) in items]
        return await asyncio.gather(*tasks)

    async def _download_one(self, post: QQChannelPost, url: str, idx: int, dest_dir: Path, kind: str) -> DownloadItemResult:
        # 文件命名：{YYYYMMDD_HHMM}_{post_id}_{type}_{index:02}{ext}
        from datetime import datetime
        ts = post.post_time if getattr(post, 'post_time', None) else datetime.now()
        date_prefix = ts.strftime('%Y%m%d_%H%M')
        name_hint = f"{date_prefix}_{post.post_id}_{kind}_{idx:02d}"
        for attempt in range(self.retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                headers = {"User-Agent": "QQChannelMCP/1.0"}
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            raise RuntimeError(f"HTTP {resp.status}")

                        ctype = resp.headers.get("Content-Type", "").lower()
                        ext = self._guess_ext(url, ctype, kind)
                        file_path = dest_dir / f"{name_hint}{ext}"
                        # 已存在则跳过，避免重复下载
                        if file_path.exists():
                            return DownloadItemResult(url=url, success=True, file_path=str(file_path), bytes=0)

                        data = await resp.read()
                        with open(file_path, "wb") as f:
                            f.write(data)

                        return DownloadItemResult(url=url, success=True, file_path=str(file_path), bytes=len(data))
            except Exception as e:
                err = str(e)
                logger.warning(f"下载失败（第{attempt+1}次）：{url} -> {err}")
                await asyncio.sleep(0.3 * (attempt + 1))
                last_error = err
        return DownloadItemResult(url=url, success=False, error=last_error)

    def _guess_ext(self, url: str, content_type: str, kind: str) -> str:
        # 先看 Content-Type
        if "image/jpeg" in content_type:
            return ".jpg"
        if "image/png" in content_type:
            return ".png"
        if "image/gif" in content_type:
            return ".gif"
        if "image/webp" in content_type:
            return ".webp"
        # 从 URL 猜测
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            if url.lower().split("?")[0].endswith(ext):
                return ext if ext != ".jpeg" else ".jpg"
        # 默认
        return ".gif" if kind == "gif" else ".jpg"

    def _manifest_path(self, day_dir: Path) -> Path:
        return day_dir / "manifest.json"

    def _load_manifest(self, day_dir: Path) -> Dict[str, Any]:
        try:
            p = self._manifest_path(day_dir)
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "processed_post_ids": [],
            "total_images": 0,
            "total_gifs": 0,
            "downloaded_files_sum": 0,
            "failed_files_sum": 0,
            "total_size_sum": 0,
            "last_run": None,
        }

    def _save_manifest(self, day_dir: Path, manifest: Dict[str, Any]) -> None:
        try:
            p = self._manifest_path(day_dir)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"写入manifest失败: {e}")

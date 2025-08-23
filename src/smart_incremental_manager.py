#!/usr/bin/env python3
"""
智能增量更新管理器
解决重复下载和序号混乱问题
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class SmartIncrementalManager:
    """智能增量更新管理器"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.post_mapping = {}      # post_id -> 序号映射
        self.file_records = {}      # 文件名 -> 文件信息记录
        self.content_hashes = {}    # 内容哈希 -> 文件记录
        self.next_sequence = 1      # 下一个可用序号
        self.mapping_file = base_dir / "posts_mapping.json"
        self.counter_file = base_dir / "sequence_counter.json"
        
        # 加载现有映射关系
        self.load_existing_mapping()
    
    def get_post_identifier(self, post) -> str:
        """获取帖子的唯一标识"""
        # 优先级1: 官方post_id
        if hasattr(post, 'post_id') and post.post_id:
            return f"official_{post.post_id}"
        
        # 优先级2: 时间+内容组合
        time_str = post.post_time.strftime("%Y%m%d_%H%M%S") if hasattr(post, 'post_time') and post.post_time else "unknown"
        content_hash = self.calculate_content_hash(post)
        return f"content_{time_str}_{content_hash[:8]}"
    
    def calculate_content_hash(self, post) -> str:
        """计算帖子内容哈希"""
        try:
            content_parts = []
            
            # 发帖时间
            if hasattr(post, 'post_time') and post.post_time:
                content_parts.append(post.post_time.isoformat())
            else:
                content_parts.append("unknown_time")
            
            # 图片数量
            image_count = len(post.images) if hasattr(post, 'images') and post.images else 0
            content_parts.append(str(image_count))
            
            # 图片URL（前3个，排序后取）
            if hasattr(post, 'images') and post.images:
                sorted_urls = sorted(post.images)[:3]
                content_parts.extend(sorted_urls)
            
            # 作者信息
            if hasattr(post, 'author_name') and post.author_name:
                content_parts.append(post.author_name)
            
            content_str = "|".join(content_parts)
            return hashlib.md5(content_str.encode()).hexdigest()
            
        except Exception as e:
            logger.warning(f"计算内容哈希失败: {e}")
            return hashlib.md5(str(post).encode()).hexdigest()
    
    def load_existing_mapping(self):
        """加载现有文件的映射关系"""
        try:
            # 加载映射文件
            if self.mapping_file.exists():
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.post_mapping = data.get('post_mapping', {})
                    self.content_hashes = data.get('content_hashes', {})
                    logger.info(f"加载了 {len(self.post_mapping)} 个帖子的映射关系")
            
            # 加载序号计数器
            if self.counter_file.exists():
                with open(self.counter_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.next_sequence = data.get('next_sequence', 1)
                    logger.info(f"下一个可用序号: {self.next_sequence}")
            
            # 如果没有映射文件，扫描现有文件重建
            if not self.post_mapping:
                self.rebuild_mapping_from_files()
                
        except Exception as e:
            logger.error(f"加载映射关系失败: {e}")
            self.rebuild_mapping_from_files()
    
    def rebuild_mapping_from_files(self):
        """从现有文件重建映射关系"""
        try:
            images_dir = self.base_dir / "images"
            if not images_dir.exists():
                return
            
            max_sequence = 0
            for file_path in images_dir.glob("*_image_*.jpg"):
                filename = file_path.name
                # 解析文件名: 001_image_01_20250823_185049.jpg
                parts = filename.split("_")
                if len(parts) >= 4:
                    sequence = int(parts[0])
                    max_sequence = max(max_sequence, sequence)
                    
                    # 从时间戳重建post_id（临时方案）
                    timestamp = f"{parts[3]}_{parts[4]}"
                    temp_post_id = f"rebuilt_{timestamp}"
                    
                    # 记录文件信息
                    self.file_records[filename] = {
                        'sequence': sequence,
                        'timestamp': timestamp,
                        'file_path': str(file_path),
                        'size': file_path.stat().st_size
                    }
            
            # 重要：新帖子总是从1开始，不受现有文件影响
            self.next_sequence = 1
            logger.info(f"从文件重建映射关系，新帖子序号从1开始")
            
        except Exception as e:
            logger.error(f"重建映射关系失败: {e}")
            self.next_sequence = 1
    
    def get_post_sequence(self, post) -> int:
        """获取帖子的序号（新或已有）"""
        post_id = self.get_post_identifier(post)
        
        if post_id in self.post_mapping:
            # 已有帖子，返回原有序号
            sequence = self.post_mapping[post_id]
            logger.debug(f"帖子 {post_id} 使用已有序号: {sequence}")
            return sequence
        else:
            # 新帖子，分配新序号
            sequence = self.next_sequence
            self.post_mapping[post_id] = sequence
            self.next_sequence += 1
            
            # 记录内容哈希
            content_hash = self.calculate_content_hash(post)
            self.content_hashes[content_hash] = {
                'post_id': post_id,
                'sequence': sequence,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"新帖子 {post_id} 分配序号: {sequence}")
            return sequence
    
    def finalize_initial_sequence(self):
        """完成首次下载后，重新按照时间排序所有序号"""
        try:
            logger.info("重新按照发帖时间排序所有序号...")
            self._recalculate_sequences()
        except Exception as e:
            logger.error(f"重新排序序号失败: {e}")
    
    def _recalculate_sequences(self):
        """重新计算所有帖子的序号，按照发帖时间排序"""
        try:
            # 收集所有需要重新排序的帖子信息
            posts_to_sort = []
            
            for post_id, old_sequence in self.post_mapping.items():
                # 从内容哈希中获取发帖时间
                post_time = None
                for content_hash, record in self.content_hashes.items():
                    if record['post_id'] == post_id:
                        try:
                            if 'post_time' in record:
                                post_time = datetime.fromisoformat(record['post_time'])
                            else:
                                post_time = datetime.fromisoformat(record['timestamp'])
                            break
                        except:
                            pass
                
                if post_time:
                    posts_to_sort.append({
                        'post_id': post_id,
                        'post_time': post_time,
                        'old_sequence': old_sequence
                    })
            
            if not posts_to_sort:
                logger.warning("没有找到有效的发帖时间信息")
                return
            
            # 按照发帖时间排序（最早发帖序号最小）
            posts_to_sort.sort(
                key=lambda x: x['post_time'],
                reverse=False  # 最旧在前，序号最小
            )
            
            # 重新分配连续序号
            new_mapping = {}
            for i, post_info in enumerate(posts_to_sort):
                new_sequence = i + 1
                new_mapping[post_info['post_id']] = new_sequence
                
                # 更新内容哈希记录
                for content_hash, record in self.content_hashes.items():
                    if record['post_id'] == post_info['post_id']:
                        record['sequence'] = new_sequence
            
            # 更新映射和计数器
            self.post_mapping = new_mapping
            self.next_sequence = len(new_mapping) + 1
            
            logger.info(f"重新计算序号完成，当前序号范围: 1-{len(new_mapping)}")
            
        except Exception as e:
            logger.error(f"重新计算序号失败: {e}")
    
    def shift_existing_sequences(self, shift_amount):
        """将现有帖子的序号向后移动指定数量"""
        try:
            logger.info(f"开始移动现有帖子序号，当前映射: {self.post_mapping}")
            new_mapping = {}
            for post_id, old_sequence in self.post_mapping.items():
                new_mapping[post_id] = old_sequence + shift_amount
                logger.info(f"帖子 {post_id}: {old_sequence} → {old_sequence + shift_amount}")
            
            self.post_mapping = new_mapping
            logger.info(f"现有帖子序号已向后移动 {shift_amount} 位，新映射: {self.post_mapping}")
            
        except Exception as e:
            logger.error(f"移动现有序号失败: {e}")
    
    def get_next_sequence_for_new_posts(self, new_post_count):
        """为新帖子分配序号（在现有序号基础上递增）"""
        current_max = max(self.post_mapping.values()) if self.post_mapping else 0
        return current_max + 1
    
    def record_post_time(self, post, post_time):
        """记录帖子的发帖时间"""
        try:
            post_id = self.get_post_identifier(post)
            content_hash = self.calculate_content_hash(post)
            
            # 更新或创建内容哈希记录
            if content_hash in self.content_hashes:
                self.content_hashes[content_hash]['post_time'] = post_time.isoformat()
            else:
                self.content_hashes[content_hash] = {
                    'post_id': post_id,
                    'post_time': post_time.isoformat(),
                    'timestamp': datetime.now().isoformat()
                }
            
            logger.debug(f"记录帖子 {post_id} 的发帖时间: {post_time}")
            
        except Exception as e:
            logger.warning(f"记录发帖时间失败: {e}")
    
    def has_existing_mapping(self) -> bool:
        """检查是否有现有的映射关系"""
        return len(self.post_mapping) > 0
    
    def is_duplicate_post(self, post) -> bool:
        """检测是否为重复帖子"""
        try:
            content_hash = self.calculate_content_hash(post)
            
            if content_hash in self.content_hashes:
                existing_record = self.content_hashes[content_hash]
                
                # 如果内容哈希相同，检查发帖时间差异
                if hasattr(post, 'post_time') and post.post_time and 'post_time' in existing_record:
                    try:
                        existing_post_time = datetime.fromisoformat(existing_record['post_time'])
                        time_diff = abs((post.post_time - existing_post_time).total_seconds())
                        
                        # 如果发帖时间相同或非常接近（1分钟内），认为是重复
                        if time_diff < 60:
                            logger.info(f"检测到重复帖子（发帖时间相同）: {self.get_post_identifier(post)}")
                            return True
                    except:
                        pass
                
                # 如果发帖时间无法比较，检查内容哈希是否完全相同
                # 这里我们放宽条件，只有内容完全相同时才认为是重复
                logger.debug(f"内容哈希相同但发帖时间不同，可能不是重复帖子: {self.get_post_identifier(post)}")
                return False  # 改为False，让系统继续处理
            
            return False
            
        except Exception as e:
            logger.warning(f"重复检测失败: {e}")
            return False
    
    def save_mapping(self):
        """保存映射关系到文件"""
        try:
            # 保存帖子映射
            mapping_data = {
                'post_mapping': self.post_mapping,
                'content_hashes': self.content_hashes,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
            
            # 保存序号计数器
            counter_data = {
                'next_sequence': self.next_sequence,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.counter_file, 'w', encoding='utf-8') as f:
                json.dump(counter_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"映射关系已保存，当前序号: {self.next_sequence - 1}")
            
        except Exception as e:
            logger.error(f"保存映射关系失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_mapped_posts': len(self.post_mapping),
            'next_sequence': self.next_sequence,
            'total_files': len(self.file_records),
            'mapping_file': str(self.mapping_file),
            'counter_file': str(self.counter_file)
        }
    
    def print_mapping_summary(self):
        """打印映射关系摘要"""
        print(f"\n📊 增量更新管理器状态")
        print(f"=" * 40)
        print(f"📝 已映射帖子数: {len(self.post_mapping)}")
        print(f"🔢 下一个可用序号: {self.next_sequence}")
        print(f"📁 文件记录数: {len(self.file_records)}")
        print(f"💾 映射文件: {self.mapping_file}")
        print(f"🔢 计数器文件: {self.counter_file}")
        
        if self.post_mapping:
            print(f"\n📋 帖子映射关系:")
            for post_id, sequence in sorted(self.post_mapping.items(), key=lambda x: x[1]):
                print(f"  {sequence:03d}: {post_id[:50]}...")

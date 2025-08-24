# HelloKitty图片筛选和复制功能实现

async def _filter_and_copy_hellokitty_images(self):
    """筛选HelloKitty图片并复制到HelloKitty文件夹"""
    try:
        logger.info("开始筛选HelloKitty图片...")
        
        # 获取所有下载的图片
        image_files = list(self.download_dir.glob("*_image_*.jpg"))
        if not image_files:
            logger.info("没有找到需要筛选的图片")
            return
        
        logger.info(f"找到 {len(image_files)} 张图片需要筛选")
        
        # 创建HelloKitty文件夹
        hellokitty_dir = self.download_dir.parent / "HelloKitty"
        hellokitty_dir.mkdir(exist_ok=True)
        
        # 初始化AI客户端
        ai_client = self._get_ai_client()
        if not ai_client:
            logger.warning("AI客户端初始化失败，跳过图片筛选")
            return
        
        # 筛选HelloKitty图片
        hellokitty_count = 0
        for image_file in image_files:
            try:
                # 使用AI分析图片
                is_hellokitty = await self._analyze_image_for_hellokitty(ai_client, str(image_file))
                
                if is_hellokitty:
                    # 复制到HelloKitty文件夹
                    dest_file = hellokitty_dir / image_file.name
                    import shutil
                    shutil.copy2(image_file, dest_file)
                    hellokitty_count += 1
                    logger.info(f"复制HelloKitty图片: {image_file.name}")
                else:
                    logger.info(f"跳过非HelloKitty图片: {image_file.name}")
                    
            except Exception as e:
                logger.warning(f"筛选图片失败 {image_file.name}: {e}")
                # 筛选失败时保留图片
        
        logger.info(f"筛选完成，复制了 {hellokitty_count}/{len(image_files)} 张HelloKitty图片到 {hellokitty_dir}")
        
    except Exception as e:
        logger.error(f"图片筛选和复制失败: {e}")

def _get_ai_client(self):
    """获取AI客户端"""
    try:
        from core.ai_client import AIClient
        from core.config import QQChannelConfig
        
        config = QQChannelConfig()
        return AIClient(config)
    except Exception as e:
        logger.error(f"AI客户端初始化失败: {e}")
        return None

async def _analyze_image_for_hellokitty(self, ai_client, image_path: str) -> bool:
    """分析图片是否包含HelloKitty元素"""
    try:
        prompt = """
        请分析这张图片是否包含HelloKitty元素。
        
        HelloKitty特征：
        - 白色小猫形象
        - 通常戴着蝴蝶结
        - 可爱的卡通风格
        - 可能是HelloKitty品牌相关
        - 粉色、红色等HelloKitty常见颜色
        
        请只回答：是 或 否
        """
        
        result = await ai_client.analyze_image(image_path, prompt)
        
        if result.success:
            return "是" in result.content
        else:
            logger.warning(f"AI分析失败: {result.error}")
            return False
            
    except Exception as e:
        logger.error(f"图片分析失败: {e}")
        return False

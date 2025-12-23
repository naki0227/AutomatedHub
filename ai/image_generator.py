"""
画像生成モジュール
Gemini Imagen を使用（google-genai SDK）
"""
from pathlib import Path
from typing import Optional
import base64
import os

from core.config import get_config
from core.utils import logger, get_timestamp, ensure_dir


class ImageGenerator:
    """画像生成クライアント（Gemini Imagen）"""
    
    def __init__(self):
        config = get_config()
        self.output_dir = config.project_root / "ai" / "generated_images"
        ensure_dir(self.output_dir)
        
        self.client = None
        self.openai_client = None
        
        # google-genai SDK を使用
        if config.validate_gemini():
            try:
                from google import genai
                
                # API キーを設定
                self.client = genai.Client(api_key=config.gemini_api_key)
                logger.info("Gemini Imagen (google-genai) initialized")
            except ImportError:
                logger.warning("google-genai package not installed")
            except Exception as e:
                logger.warning(f"Gemini Imagen initialization failed: {e}")
        
        # OpenAI (DALL-E) はオプション
        if config.openai_api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=config.openai_api_key)
                logger.info("DALL-E fallback enabled")
            except ImportError:
                pass
        
        if not self.client and not self.openai_client:
            logger.warning("No image generation available - images will be skipped")
        
        logger.info("ImageGenerator initialized")
    
    def is_available(self) -> bool:
        """画像生成が利用可能か"""
        return self.client is not None or self.openai_client is not None
    
    def generate(
        self,
        prompt: str,
        save_path: Optional[Path] = None,
        use_dalle_fallback: bool = True
    ) -> Optional[Path]:
        """
        画像を生成して保存
        
        Args:
            prompt: 画像生成プロンプト（英語推奨）
            save_path: 保存先パス（省略時は自動生成）
            use_dalle_fallback: DALL-Eをフォールバックとして使用
        
        Returns:
            生成された画像のパス、または None
        """
        if not self.is_available():
            logger.info("Image generation skipped (not available)")
            return None
        
        if save_path is None:
            save_path = self.output_dir / f"{get_timestamp()}.png"
        
        # Gemini Imagenで生成を試みる
        if self.client:
            try:
                image_path = self._generate_with_imagen(prompt, save_path)
                if image_path:
                    return image_path
            except Exception as e:
                logger.warning(f"Gemini Imagen failed: {e}")
        
        # フォールバック: DALL-E
        if use_dalle_fallback and self.openai_client:
            try:
                return self._generate_with_dalle(prompt, save_path)
            except Exception as e:
                logger.error(f"DALL-E fallback also failed: {e}")
        
        return None
    
    def _generate_with_imagen(self, prompt: str, save_path: Path) -> Optional[Path]:
        """Gemini Imagenで画像生成"""
        if not self.client:
            return None
        
        logger.info(f"Generating image with Imagen: {prompt[:50]}...")
        
        from google.genai import types
        
        response = self.client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            )
        )
        
        if response.generated_images:
            # 画像を保存
            image = response.generated_images[0].image
            
            # PILで保存
            image.save(str(save_path))
            logger.info(f"Image saved: {save_path}")
            return save_path
        
        return None
    
    def _generate_with_dalle(self, prompt: str, save_path: Path) -> Optional[Path]:
        """DALL-E 3で画像生成"""
        if not self.openai_client:
            return None
        
        logger.info(f"Generating image with DALL-E: {prompt[:50]}...")
        
        from PIL import Image
        import io
        
        response = self.openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
            response_format="b64_json"
        )
        
        # Base64から画像を保存
        image_data = base64.b64decode(response.data[0].b64_json)
        image = Image.open(io.BytesIO(image_data))
        image.save(save_path)
        
        logger.info(f"Image saved: {save_path}")
        return save_path
    
    def generate_sns_image(
        self,
        topic: str,
        platform: str = "x",
        style: str = "modern"
    ) -> Optional[Path]:
        """SNS投稿用の画像を生成"""
        
        if not self.is_available():
            logger.info("SNS image generation skipped (not available)")
            return None
        
        # プロンプトを構築
        prompt = f"""
{topic}, {style} design, clean layout, 
high quality, professional, social media post,
no text overlay, vibrant colors
""".strip()
        
        save_path = self.output_dir / f"{platform}_{get_timestamp()}.png"
        
        return self.generate(prompt, save_path)

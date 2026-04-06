import base64
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from aicp.errors import AicpError


class MediaOperation(str, Enum):
    GENERATE_IMAGE = "generate_image"
    GENERATE_VIDEO = "generate_video"
    UPSCALE = "upscale"
    VARIATE = "variate"


class MediaProvider(str, Enum):
    FAL = "fal"
    REPLICATE = "replicate"
    OPENAI = "openai"
    LOCAL = "local"


class MediaError(AicpError):
    pass


class MediaProviderError(MediaError):
    pass


class MediaNotSupportedError(MediaError):
    pass


@dataclass
class ImageGenerationResult:
    images: list[str]
    seed: Optional[int]
    width: int
    height: int
    model: str
    duration_ms: int
    provider: str


@dataclass
class VideoGenerationResult:
    video_url: str
    duration_seconds: int
    width: int
    height: int
    model: str
    duration_ms: int
    provider: str


class MediaConfig(BaseModel):
    operation: MediaOperation
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    provider: MediaProvider = Field(default=MediaProvider.FAL)
    model: Optional[str] = None
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    num_images: int = Field(default=1, ge=1, le=4)
    guidance_scale: float = Field(default=7.5, ge=1, le=20)
    num_inference_steps: int = Field(default=50, ge=1, le=100)
    seed: Optional[int] = None
    api_key: Optional[str] = None


class MediaService:
    def __init__(self):
        self._api_keys: dict[MediaProvider, str] = {}
        self._default_models: dict[MediaOperation, str] = {
            MediaOperation.GENERATE_IMAGE: "flux-pro",
            MediaOperation.GENERATE_VIDEO: "kling-1.0",
        }

    def configure_provider(self, provider: MediaProvider, api_key: str) -> None:
        self._api_keys[provider] = api_key

    def _get_api_key(self, provider: MediaProvider) -> Optional[str]:
        return self._api_keys.get(provider)

    def _get_default_model(self, operation: MediaOperation) -> str:
        return self._default_models.get(operation, "default")

    async def generate_image(
        self,
        prompt: str,
        provider: MediaProvider = MediaProvider.FAL,
        model: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 50,
        seed: Optional[int] = None,
    ) -> ImageGenerationResult:
        if provider == MediaProvider.LOCAL:
            return await self._generate_image_local(
                prompt, width, height, num_images, seed
            )
        if provider == MediaProvider.FAL:
            return await self._generate_image_fal(
                prompt, model or "flux-pro", width, height, num_images,
                guidance_scale, num_inference_steps, seed
            )
        if provider == MediaProvider.REPLICATE:
            return await self._generate_image_replicate(
                prompt, model or "sdxl", width, height, num_images, seed
            )
        if provider == MediaProvider.OPENAI:
            return await self._generate_image_dalle(
                prompt, width, height, num_images
            )
        raise MediaNotSupportedError(f"Image generation not supported for {provider}")

    async def _generate_image_local(
        self,
        prompt: str,
        width: int,
        height: int,
        num_images: int,
        seed: Optional[int],
    ) -> ImageGenerationResult:
        raise MediaNotSupportedError(
            "Local image generation requires diffusion or COMFYUI installed"
        )

    async def _generate_image_fal(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
        num_images: int,
        guidance_scale: float,
        num_inference_steps: int,
        seed: Optional[int],
    ) -> ImageGenerationResult:
        api_key = self._get_api_key(MediaProvider.FAL)
        if not api_key:
            raise MediaProviderError("FAL API key not configured")
        try:
            import fal_client

            @fal_client.on_queue_update
            def update_queue(update):
                if isinstance(update, fal_client.InProgress):
                    for log in update.logs:
                        pass

            result = fal_client.run(
                "fal-ai/flux-pro",
                arguments={
                    "prompt": prompt,
                    "image_size": {"width": width, "height": height},
                    "num_images": num_images,
                    "guidance_scale": guidance_scale,
                    "num_inference_steps": num_inference_steps,
                    "seed": seed,
                },
            )
            images = []
            for img in result.get("images", []):
                if img.get("url"):
                    images.append(img["url"])
            duration_ms = int(result.get("timing", {}).get("inference", 0))
            return ImageGenerationResult(
                images=images,
                seed=seed,
                width=width,
                height=height,
                model=model,
                duration_ms=duration_ms,
                provider="fal",
            )
        except ImportError:
            raise MediaProviderError("fal-client not installed")
        except Exception as e:
            raise MediaProviderError(f"FAL image generation failed: {e}")

    async def _generate_image_replicate(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
        num_images: int,
        seed: Optional[int],
    ) -> ImageGenerationResult:
        api_key = self._get_api_key(MediaProvider.REPLICATE)
        if not api_key:
            raise MediaProviderError("Replicate API key not configured")
        raise MediaNotSupportedError("Replicate integration coming soon")

    async def _generate_image_dalle(
        self,
        prompt: str,
        width: int,
        height: int,
        num_images: int,
    ) -> ImageGenerationResult:
        api_key = self._get_api_key(MediaProvider.OPENAI)
        if not api_key:
            raise MediaProviderError("OpenAI API key not configured")
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            size_map = {
                (1024, 1024): "1024x1024",
                (1792, 1024): "1792x1024",
                (1024, 1792): "1024x1792",
            }
            size = size_map.get((width, height), "1024x1024")
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                n=num_images,
            )
            images = [img.url for img in response.data]
            return ImageGenerationResult(
                images=images,
                seed=None,
                width=width,
                height=height,
                model="dall-e-3",
                duration_ms=0,
                provider="openai",
            )
        except ImportError:
            raise MediaProviderError("openai not installed")
        except Exception as e:
            raise MediaProviderError(f"OpenAI image generation failed: {e}")

    async def generate_video(
        self,
        prompt: str,
        provider: MediaProvider = MediaProvider.FAL,
        model: Optional[str] = None,
        width: int = 1024,
        height: int = 576,
    ) -> VideoGenerationResult:
        if provider == MediaProvider.FAL:
            return await self._generate_video_fal(
                prompt, model or "kling-1.0", width, height
            )
        if provider == MediaProvider.REPLICATE:
            return await self._generate_video_replicate(prompt, model or "minimax", width, height)
        raise MediaNotSupportedError(f"Video generation not supported for {provider}")

    async def _generate_video_fal(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
    ) -> VideoGenerationResult:
        api_key = self._get_api_key(MediaProvider.FAL)
        if not api_key:
            raise MediaProviderError("FAL API key not configured")
        raise MediaNotSupportedError("Video generation coming soon")

    async def _generate_video_replicate(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
    ) -> VideoGenerationResult:
        api_key = self._get_api_key(MediaProvider.REPLICATE)
        if not api_key:
            raise MediaProviderError("Replicate API key not configured")
        raise MediaNotSupportedError("Video generation coming soon")

    async def upscale(
        self,
        image_url: str,
        scale: int = 2,
    ) -> ImageGenerationResult:
        raise MediaNotSupportedError("Upscale coming soon")

    async def variate(
        self,
        image_url: str,
        prompt: str,
        strength: float = 0.7,
    ) -> ImageGenerationResult:
        raise MediaNotSupportedError("Variate coming soon")

    async def process_config(self, config: MediaConfig) -> dict[str, Any]:
        if config.operation == MediaOperation.GENERATE_IMAGE:
            if not config.prompt:
                raise MediaError("prompt required for image generation")
            result = await self.generate_image(
                prompt=config.prompt,
                provider=config.provider,
                model=config.model,
                width=config.width,
                height=config.height,
                num_images=config.num_images,
                guidance_scale=config.guidance_scale,
                num_inference_steps=config.num_inference_steps,
                seed=config.seed,
            )
            return {
                "images": result.images,
                "seed": result.seed,
                "width": result.width,
                "height": result.height,
                "model": result.model,
                "duration_ms": result.duration_ms,
            }
        if config.operation == MediaOperation.GENERATE_VIDEO:
            if not config.prompt:
                raise MediaError("prompt required for video generation")
            result = await self.generate_video(
                prompt=config.prompt,
                provider=config.provider,
                model=config.model,
                width=config.width,
                height=config.height,
            )
            return {
                "video_url": result.video_url,
                "duration_seconds": result.duration_seconds,
                "width": result.width,
                "height": result.height,
                "model": result.model,
            }
        raise MediaNotSupportedError(f"Operation {config.operation} not supported")
import pytest
from aicp_runtime.services.media import (
    MediaConfig,
    MediaError,
    MediaNotSupportedError,
    MediaOperation,
    MediaProvider,
    MediaService,
)


class TestMediaConfig:
    def test_default_config(self):
        config = MediaConfig(operation=MediaOperation.GENERATE_IMAGE)
        assert config.operation == MediaOperation.GENERATE_IMAGE
        assert config.provider == MediaProvider.FAL
        assert config.width == 1024

    def test_custom_config(self):
        config = MediaConfig(
            operation=MediaOperation.GENERATE_IMAGE,
            prompt="A cat",
            width=512,
            height=512,
            num_images=2,
        )
        assert config.prompt == "A cat"
        assert config.width == 512


class TestMediaEnums:
    def test_operation_values(self):
        assert MediaOperation.GENERATE_IMAGE == "generate_image"
        assert MediaOperation.GENERATE_VIDEO == "generate_video"
        assert MediaOperation.UPSCALE == "upscale"

    def test_provider_values(self):
        assert MediaProvider.FAL == "fal"
        assert MediaProvider.REPLICATE == "replicate"
        assert MediaProvider.OPENAI == "openai"


class TestMediaService:
    def test_init(self):
        service = MediaService()
        assert service._default_models[MediaOperation.GENERATE_IMAGE] == "flux-pro"

    def test_configure_provider(self):
        service = MediaService()
        service.configure_provider(MediaProvider.FAL, "test-key-123")
        assert service._get_api_key(MediaProvider.FAL) == "test-key-123"


@pytest.mark.asyncio
class TestMediaServiceOperations:
    async def test_generate_image_requires_prompt(self):
        config = MediaConfig(operation=MediaOperation.GENERATE_IMAGE)
        service = MediaService()
        with pytest.raises(MediaError):
            await service.process_config(config)

    async def test_local_provider_not_supported(self):
        service = MediaService()
        with pytest.raises(MediaNotSupportedError):
            await service.generate_image("test", provider=MediaProvider.LOCAL)

    async def test_openai_requires_api_key(self):
        service = MediaService()
        with pytest.raises(MediaError):
            await service.generate_image("test", provider=MediaProvider.OPENAI)

    async def test_fal_requires_api_key(self):
        service = MediaService()
        with pytest.raises(MediaError):
            await service.generate_image("test", provider=MediaProvider.FAL)

    async def test_generate_video_not_supported(self):
        service = MediaService()
        with pytest.raises(MediaError):
            await service.generate_video("test", provider=MediaProvider.FAL)


class TestMediaErrors:
    def test_media_error_is_aicp_error(self):
        from aicp.errors import AicpError

        assert issubclass(MediaError, AicpError)

    def test_media_provider_error_is_media_error(self):
        assert issubclass(MediaNotSupportedError, MediaError)

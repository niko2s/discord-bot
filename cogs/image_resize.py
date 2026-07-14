import asyncio
from io import BytesIO
from typing import Tuple
import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, UnidentifiedImageError


MAX_OUTPUT_PIXELS = 25_000_000


class Resize(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(
        name="resize_pct", description="Resize an image by desired percentage"
    )
    @app_commands.describe(image="Image to resize")
    @app_commands.choices(
        desired_size=[
            app_commands.Choice(name=f"{int(s*100)}%", value=s)
            for s in [0.25, 0.5, 0.75, 1.5, 2.0, 2.5, 5.0]
        ]
    )
    async def resize_by_percentage(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        desired_size: app_commands.Choice[float],
    ):
        if image.width is None or image.height is None:
            await interaction.response.send_message(
                "Only image attachments can be resized.", ephemeral=True
            )
            return

        filename_modification = desired_size.name[:-1] + "pct"  # removed % for filename

        await handle_resize_request(
            interaction,
            image,
            filename_modification,
            (
                max(1, int(image.width * desired_size.value)),
                max(1, int(image.height * desired_size.value)),
            ),
        )

    @app_commands.command(
        name="resize_abs", description="Resize an image by absolute value"
    )
    @app_commands.describe(image="Image to resize")
    @app_commands.choices(
        axis=[
            app_commands.Choice(name="x", value=0),
            app_commands.Choice(name="y", value=1),
        ]
    )
    @app_commands.describe(pixels="Amount of pixels on selected axis")
    async def resize_by_absolute(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        axis: app_commands.Choice[int],
        pixels: int,
    ):
        """
        Args:
                interaction (discord.Interaction): Discord interaction
                image (discord.Attachment): Image to resize
                axis (app_commands.Choice[int]): 0 if x, 1 if y
                pixels (int): Desired amount of pixels on axis
        """
        if image.width is None or image.height is None:
            await interaction.response.send_message(
                "Only image attachments can be resized.", ephemeral=True
            )
            return
        if pixels < 1:
            await interaction.response.send_message(
                "The pixel size must be greater than zero.", ephemeral=True
            )
            return

        filename_modification = f"{axis.name}-{pixels}px"

        # calculate target size with images aspect ratio
        target_size = None
        if axis.value:
            # new y(height in pixels) is given
            x = int(image.width / image.height * pixels)
            target_size = (x, pixels)
        else:
            # new x(width in pixels) is given
            y = pixels * image.height // image.width
            target_size = (pixels, y)

        await handle_resize_request(
            interaction, image, filename_modification, target_size
        )


async def handle_resize_request(
    interaction: discord.Interaction,
    image: discord.Attachment,
    filename_modification: str,
    target_size: Tuple[int, int],
):
    """Handle entire interaction and resize image to desired size

    Args:
            interaction (discord.Interaction): Discord interaction
            image (discord.Attachment): Image to resize
            filename_modification (str): Description of the resize operation, appended to new image
            target_size (int, int): Size as Tuple(width: int, height: int) of resized image
    """
    await interaction.response.defer(thinking=True)

    if not image.content_type or not image.content_type.startswith("image/"):
        await interaction.followup.send(
            f"Wrong file format `{image.content_type}`, only images supported"
        )
        return

    width, height = target_size
    if width < 1 or height < 1 or width * height > MAX_OUTPUT_PIXELS:
        await interaction.followup.send(
            "The requested image dimensions are too large."
        )
        return

    try:
        data = await image.read()
        img_buffer, extension = await asyncio.to_thread(
            resize_image, data, target_size
        )
    except (
        discord.HTTPException,
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        await interaction.followup.send("The attachment is not a supported image.")
        return

    name = image.filename.rsplit(".", 1)[0]
    await interaction.followup.send(
        file=discord.File(
            img_buffer, f"{name}-{filename_modification}.{extension.lower()}"
        )
    )


def resize_image(data: bytes, target_size: Tuple[int, int]) -> tuple[BytesIO, str]:
    with Image.open(BytesIO(data)) as image:
        if image.width * image.height > MAX_OUTPUT_PIXELS:
            raise ValueError("input image dimensions are too large")
        image.load()
        image_format = image.format
        if image_format is None:
            raise ValueError("unknown image format")
        resized = image.resize(target_size, Image.Resampling.LANCZOS)
        img_buffer = BytesIO()
        resized.save(img_buffer, format=image_format)
        img_buffer.seek(0)
        return img_buffer, image_format


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Resize(client))

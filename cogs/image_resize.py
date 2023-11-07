import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image
from utils import download
from io import BytesIO


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
        desired_size: app_commands.Choice[float]
    ):
        filename_modification = desired_size.name[:-1] + "pct" # removed % for filename

        await handle_resize_request(
            interaction,
            image,
            filename_modification,
            (
                int(image.width * desired_size.value),
                int(image.height * desired_size.value),
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
    target_size: (int, int)
):
    """Handle entire interaction and resize image to desired size
    
	Args:
		interaction (discord.Interaction): Discord interaction
		image (discord.Attachment): Image to resize
		filename_modification (str): Description of the resize operation, will be appended to the resized image
		target_size (int, int): Size as Tuple(width: int, height: int) of resized image
	"""
    await interaction.response.defer(thinking=True)

    type_, subtype = image.content_type.split("/")
    name, ext = image.filename.rsplit(".", 1)

    if type_ == ("image"):
        # read discord.Attachment into PIL.Image and resize it
        data = await download.download_file(image.url)
        img = Image.open(data)
        img = img.resize(
            target_size,
            Image.LANCZOS,
        )

        # write to buffer, so it can be sent
        img_buffer = BytesIO()
        img.save(img_buffer, format=subtype)
        img_buffer.seek(0)

        await interaction.followup.send(
            file=discord.File(img_buffer, f"{name}-{filename_modification}.{ext}")
        )
    else:
        await interaction.followup.send(
            f"Wrong file format `{image.content_type}`, only images supported"
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Resize(client))

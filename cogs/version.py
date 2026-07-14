import os

import discord
from discord import app_commands
from discord.ext import commands


class Version(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="version", description="Show the running bot version")
    async def version(self, interaction: discord.Interaction):
        git_sha = os.environ.get("BOT_GIT_SHA", "unknown")
        repository_url = os.environ.get("BOT_REPOSITORY_URL", "unknown")
        version = git_sha[:7] if git_sha != "unknown" else "dev"

        commit = f"`{git_sha}`"
        if git_sha != "unknown" and repository_url != "unknown":
            commit = f"[`{git_sha}`]({repository_url}/commit/{git_sha})"

        await interaction.response.send_message(
            f"Version: `{version}`\nCommit: {commit}"
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Version(client))

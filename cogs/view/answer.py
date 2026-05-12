import logging
import discord
from discord.ui import View


class AnswerSelection(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.values = {}  # user: selected

    async def _record(self, interaction: discord.Interaction, choice: int) -> None:
        key = interaction.user.global_name or interaction.user.name
        self.values[key] = choice
        try:
            await interaction.response.defer()
        except discord.InteractionResponded:
            pass

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def option1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._record(interaction, 1)

    @discord.ui.button(label="2", style=discord.ButtonStyle.green)
    async def option2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._record(interaction, 2)

    @discord.ui.button(label="3", style=discord.ButtonStyle.blurple)
    async def option3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._record(interaction, 3)

    @discord.ui.button(label="4", style=discord.ButtonStyle.green)
    async def option4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._record(interaction, 4)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        logging.exception(
            "AnswerSelection button error (item=%s): %s", getattr(item, "label", "?"), error
        )

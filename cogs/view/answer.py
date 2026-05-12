import logging
import discord
from discord.ui import View, Button


class _AnswerButton(Button):
    def __init__(
        self,
        choice: int,
        label: str,
        style: discord.ButtonStyle,
        emoji: str | None = None,
    ):
        super().__init__(label=label, style=style, emoji=emoji)
        self.choice = choice

    async def callback(self, interaction: discord.Interaction):
        view: "AnswerSelection" = self.view  # type: ignore[assignment]
        await view._record(interaction, self.choice)


class AnswerSelection(View):
    def __init__(self, *, boolean: bool = False):
        super().__init__(timeout=None)
        self.values: dict[str, int] = {}

        if boolean:
            self.add_item(_AnswerButton(1, "True",  discord.ButtonStyle.success))
            self.add_item(_AnswerButton(2, "False", discord.ButtonStyle.danger))
        else:
            self.add_item(_AnswerButton(1, "1", discord.ButtonStyle.blurple))
            self.add_item(_AnswerButton(2, "2", discord.ButtonStyle.green))
            self.add_item(_AnswerButton(3, "3", discord.ButtonStyle.blurple))
            self.add_item(_AnswerButton(4, "4", discord.ButtonStyle.green))

    async def _record(self, interaction: discord.Interaction, choice: int) -> None:
        key = interaction.user.global_name or interaction.user.name
        self.values[key] = choice
        try:
            await interaction.response.defer()
        except discord.InteractionResponded:
            pass

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        logging.exception(
            "AnswerSelection button error (item=%s): %s",
            getattr(item, "label", "?"),
            error,
        )

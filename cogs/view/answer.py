import discord
from discord.ui import View


class AnswerSelection(View):
    def __init__(self):
        super().__init__()
        self.values = {}  # user: selected

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def option1(self, interaction: discord.Interaction):
        self.values[interaction.user.global_name] = 1
        await interaction.response.defer()

    @discord.ui.button(label="2", style=discord.ButtonStyle.green)
    async def option2(self, interaction: discord.Interaction):
        self.values[interaction.user.global_name] = 2
        await interaction.response.defer()

    @discord.ui.button(label="3", style=discord.ButtonStyle.blurple)
    async def option3(self, interaction: discord.Interaction):
        self.values[interaction.user.global_name] = 3
        await interaction.response.defer()

    @discord.ui.button(label="4", style=discord.ButtonStyle.green)
    async def option4(self, interaction: discord.Interaction):
        self.values[interaction.user.global_name] = 4
        await interaction.response.defer()

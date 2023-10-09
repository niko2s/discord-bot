# Discord-Bot

## Disclaimer
This repository is created for my educational and non-commercial use, showcasing coding skills. It uses code from [xtekky/gpt4free](https://github.com/xtekky/gpt4free). Use at your own risk. For license info, see [LICENSE](LICENSE) and [LEGAL_NOTICE.md](LEGAL_NOTICE.md) (same as [xtekky/gpt4free](https://github.com/xtekky/gpt4free)).

To exclude the referenced repository, remove [cogs/ai.py](cogs/ai.py) and `g4f==0.0.2.8` from [requirements.txt](requirements.txt).

Use all APIs at own risk, refer to their respective licenses, that can be found on the websites/repositories.


## Features
If the functionality is based on information retrieval using APIs, the source is given.
### Multiplayer Trivia
- Source: [The Trivia API](https://the-trivia-api.com/)
- Play trivia quizzes alone or with friends
- This API is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).  For more information, refer to their website.


![Trivia-Quiz](https://github.com/niko2s/discord-bot/assets/90977134/cdb77dbd-5a21-4d84-8c48-7288b217b674)

### Chat with AI
- Source: [xtekky/gpt4free](https://github.com/xtekky/gpt4free)
- Chat or ask questions to AI

### Dictionary Lookup
- Source: [Free Dictionary API](https://dictionaryapi.dev/)
- Get word pronunciation, definitions, synonyms, antonyms
  
![Screenshot 2023-10-09 at 23 49 28](https://github.com/niko2s/discord-bot/assets/90977134/43fd645e-3d75-492f-949b-bd9b88f838cf)


![Screenshot 2023-10-09 at 23 49 36](https://github.com/niko2s/discord-bot/assets/90977134/fb673ed7-ac12-4474-8f40-2d31433e48c9)

### Urban Dictionary (NSFW)
- Source: [RapidAPI/UrbanDictionary](https://rapidapi.com/archergardinersheridan/api/urban-dictionary7)
- Informal and slang word lookup
- NSFW: May contain inappropriate language



## Usage

1. **Register the Application**:
   - Register your application on the [Discord Developer Portal](https://discord.com/developers/applications)
   - For assistance, refer to the [registration guide](https://discordpy.readthedocs.io/en/stable/discord.html) provided by [discord.py](https://github.com/Rapptz/discord.py), the library utilized for bot creation

2. **Configure Environment**:
   - Download or clone this repository to your local machine
   - Rename the file `.env.example` to `.env`
   - Populate the `.env` file with the necessary API credentials
   - The Chat with AI feature is enabled by default; to disable it, follow the instructions mentioned in the Disclaimer section

4. **Run the Bot**:
   - Open a terminal in this repository's directory and execute:
   ```sh
   python3 bot.py
   ```
5. **Try the Command**:
   - type `/` in a text channel the bot has access to, and a list of all available commands along with brief descriptions and required parameters will appear
     
   ![Commands](https://github.com/niko2s/discord-bot/assets/90977134/4e589c5a-272e-4e60-b4ec-9bb1c1701f87)


## Copyright

This program is licensed under the [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.txt)

```
niko2s/discord-bot: Copyright (C) 2023 niko2s

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
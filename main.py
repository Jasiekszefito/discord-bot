import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

load_dotenv()

# ------------------- ZMIENNE ŚRODOWISKOWE -------------------
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))
LEGIT_CHANNEL_ID = int(os.getenv("LEGIT_CHANNEL_ID", 0))
OFFER_CHANNEL_ID = int(os.getenv("OFFER_CHANNEL_ID", 0))
OFERTA = os.getenv("OFERTA", "")

# ------------------- KEEP ALIVE -------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot działa!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# ------------------- BOT -------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ticket_owners = {}
ticket_data = {}

# ------------------- MODALE I VIEW -------------------
class TicketModal(discord.ui.Modal):
    def __init__(self, user, category):
        super().__init__(title=f"Ticket: {category}")
        self.user = user
        self.category = category

        self.problem = discord.ui.TextInput(
            label="Opisz problem / produkt",
            style=discord.TextStyle.paragraph,
            placeholder="Np. opis problemu lub nazwa produktu",
            required=True,
            max_length=1000
        )
        self.add_item(self.problem)

        if category == "Zakup produktu":
            self.amount = discord.ui.TextInput(label="Ilość", placeholder="Podaj ilość", required=True)
            self.price = discord.ui.TextInput(label="Cena", placeholder="Podaj cenę", required=True)
            self.add_item(self.amount)
            self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            self.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{self.user.name}",
            overwrites=overwrites
        )

        if self.category == "Zakup produktu":
            desc = f"{self.user.mention} chce kupić **{self.problem.value}**\nIlość: {self.amount.value}\nCena: {self.price.value}"
            ticket_data[channel.id] = {
                "user": self.user,
                "produkt": self.problem.value,
                "ilosc": self.amount.value,
                "cena": self.price.value
            }
        else:
            desc = f"{self.user.mention} zgłosił problem:\n{self.problem.value}"

        embed = discord.Embed(
            title=f"🎟️ Ticket: {self.category}",
            description=desc,
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Ticket by M0N3HUS8L")

        ticket_owners[channel.id] = self.user.id
        await channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Utworzono ticket: {channel.mention}", ephemeral=True)

class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(label="Reklamacja", description="Złóż reklamację"),
            discord.SelectOption(label="Zakup produktu", description="Kup produkt"),
            discord.SelectOption(label="Zgłoszenie problemu", description="Zgłoś problem")
        ]
        self.select = discord.ui.Select(
            placeholder="Wybierz kategorię ticketa...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select"
        )
        self.add_item(self.select)
        self.select.callback = self.select_callback

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(interaction.user, self.select.values[0]))

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="❌ Zamknij ticket", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Ticket zamknięty. Kanał zostanie usunięty za 5s", ephemeral=True)
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))
        await interaction.channel.delete()

class OfferSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        options = [
            discord.SelectOption(label="Oferta 1", description="Mentoring Standard", emoji="🎓"),
            discord.SelectOption(label="Oferta 2", description="Mentoring Plus", emoji="💼"),
            discord.SelectOption(label="Oferta 3", description="Mentoring Premium", emoji="🚀")
        ]

        self.select = discord.ui.Select(
            placeholder="Kliknij, aby zobaczyć szczegóły oferty...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="offer_select"
        )
        self.add_item(self.select)
        self.select.callback = self.select_callback

    async def select_callback(self, interaction: discord.Interaction):
        opis = {
            "Oferta 1": (
                "💡 **Oferta 1 – Mentoring Standard**\n"
                "- Mentoring indywidualny\n"
                "- 10 pytań do pomocy\n"
                "- Cena: 50PLN\n"
            ),
            "Oferta 2": (
                "💡 **Oferta 2 – Mentoring Plus**\n"
                "- Mentoring indywidualny\n"
                "- 20 pytań do pomocy\n"
                "- Cena: 100PLN\n"
            ),
            "Oferta 3": (
                "💡 **Oferta 3 – Premium 24/7**\n"
                "- Mentoring premium\n"
                "- Pomoc 24/7\n"
                "- Cena: 200PLN\n"
            )
        }

        embed = discord.Embed(
            title=f"{self.select.values[0]}",
            description=opis[self.select.values[0]],
            color=discord.Color.green()
        )

        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(label="Kup produkt", style=discord.ButtonStyle.green)

        async def button_callback(button_interaction: discord.Interaction):
            await button_interaction.response.send_modal(
                TicketModal(button_interaction.user, "Zakup produktu")
            )

        button.callback = button_callback
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ------------------- KOMENDY -------------------
@bot.command(name="regulamin")
async def regulamin(ctx):
    embed = discord.Embed(
        title="📜 Regulamin Serwera",
        description="Witaj na naszym serwerze! Prosimy o przestrzeganie poniższych zasad:",
        color=discord.Color.blue()
    )
    embed.add_field(name="1️⃣ Pełna kultura", value="Szanuj innych członków serwera.", inline=False)
    embed.add_field(name="2️⃣ Zero scamu", value="Nie oszukuj innych.", inline=False)
    embed.add_field(name="3️⃣ Prywatność", value="Nie udostępniaj danych osobowych.", inline=False)
    embed.add_field(name="4️⃣ Ticket Support", value="Używaj systemu ticketów.", inline=False)
    embed.add_field(name="5️⃣ Dobre zachowanie", value="Bądź miły i baw się dobrze!", inline=False)
    embed.set_image(url="https://i.imgur.com/pRPq8YW.jpeg")
    embed.set_footer(text="Regulamin by M0N3HUS8L")
    await ctx.send(embed=embed)

@bot.command(name="ticketpanel")
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎫 Kliknij Aby Stworzyć Ticketa",
        description="Wybierz kategorię ticketa",
        color=discord.Color.green()
    )
    embed.set_image(url="https://i.imgur.com/pRPq8YW.jpeg")
    await ctx.send(embed=embed, view=TicketCategoryView())

@bot.command(name="oferta")
async def oferta_prefix(ctx):
    embed = discord.Embed(
        title="🛒 Oferta produktów",
        description="Kliknij w dropdown poniżej, aby wybrać ofertę:",
        color=discord.Color.gold()
    )
    embed.set_image(url="https://i.imgur.com/pRPq8YW.jpeg")
    await ctx.send(embed=embed, view=OfferSelectView())

@bot.tree.command(name="oferta", description="Sprawdź ofertę produktów")
async def oferta(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛒 Oferta produktów",
        description="Kliknij w dropdown poniżej, aby wybrać ofertę:",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=OfferSelectView(), ephemeral=True)

# ------------------- ADMIN -------------------
@bot.tree.command(name="przejmij", description="Przejmij ticket jako admin")
@app_commands.checks.has_permissions(manage_channels=True)
async def przejmij(interaction: discord.Interaction):
    channel = interaction.channel
    if channel.id not in ticket_owners:
        await interaction.response.send_message("❌ To nie jest ticket.", ephemeral=True)
        return
    owner = interaction.guild.get_member(ticket_owners[channel.id])
    overwrites = {
        channel.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        owner: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        channel.guild.me: discord.PermissionOverwrite(view_channel=True)
    }
    await channel.edit(overwrites=overwrites)
    await interaction.response.send_message(f"✅ Ticket przejęty przez {interaction.user.mention}")

@bot.tree.command(name="wezwij", description="Wezwij właściciela ticketa")
@app_commands.checks.has_permissions(manage_channels=True)
async def wezwij(interaction: discord.Interaction):
    channel = interaction.channel
    if channel.id not in ticket_owners:
        await interaction.response.send_message("❌ To nie jest ticket.", ephemeral=True)
        return
    owner = interaction.guild.get_member(ticket_owners[channel.id])
    await channel.send(f"🔔 {owner.mention}, administracja cię wzywa!")
    await interaction.response.send_message("✅ Właściciel wezwany", ephemeral=True)

# ------------------- READY -------------------
@bot.event
async def on_ready():
    print(f"🤖 Zalogowano jako {bot.user} (ID: {bot.user.id})")
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print("✅ Slash commands zsynchronizowane.")

# ------------------- RUN -------------------
bot.run(TOKEN)

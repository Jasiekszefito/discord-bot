import os
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# ====== ENV ======
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))
OFFER_CHANNEL_ID = int(os.getenv("OFFER_CHANNEL_ID", 0))
PROMO_CHANNEL_ID = int(os.getenv("PROMO_CHANNEL_ID", 0))
BUMP_CHANNEL_ID = int(os.getenv("BUMP_CHANNEL_ID", 0))
OFERTA = os.getenv("OFERTA", "")

# ====== BOT ======
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== STANY ======
ticket_owners = {}
ticket_data = {}
promo_tasks = {}

PROMO_IMAGE = "https://i.imgur.com/pRPq8YW.jpeg"
PROMO_DURATION_HOURS = 48
BUMP_INTERVAL_HOURS = 1

# ====== KLASY UI ======
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="❌ Zamknij ticket", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Ticket zamknięty. Kanał zostanie usunięty za 5s", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketModal(discord.ui.Modal):
    def __init__(self, user: discord.Member, category: str):
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
            name=f"ticket-{self.user.name}".replace(" ", "-")[:90],
            overwrites=overwrites
        )

        if self.category == "Zakup produktu":
            desc = f"{self.user.mention} chce kupić **{self.problem.value}**\nIlość: {self.amount.value}\nCena: {self.price.value}"
            ticket_data[channel.id] = {
                "user": self.user.id,
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
        ).set_footer(text="Ticket by M0N3HUS8L")

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
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(interaction.user, self.select.values[0]))

class OfferSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(label="Oferta 1", description="Mentoring Standard", emoji="🎓"),
            discord.SelectOption(label="Oferta 2", description="Mentoring Plus", emoji="💼"),
            discord.SelectOption(label="Oferta 3", description="Mentoring Premium", emoji="🚀"),
        ]
        self.select = discord.ui.Select(
            placeholder="Kliknij, aby zobaczyć szczegóły oferty...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        opis = {
            "Oferta 1": "💡 **Oferta 1 – Mentoring Standard**\n- Mentoring indywidualny\n- 10 pytań do pomocy\n- Cena: 50 PLN",
            "Oferta 2": "💡 **Oferta 2 – Mentoring Plus**\n- Mentoring indywidualny\n- 20 pytań do pomocy\n- Cena: 100 PLN",
            "Oferta 3": "💡 **Oferta 3 – Premium 24/7**\n- Mentoring premium\n- Pomoc 24/7\n- Cena: 200 PLN"
        }
        embed = discord.Embed(
            title=self.select.values[0],
            description=opis[self.select.values[0]],
            color=discord.Color.green()
        )
        view = discord.ui.View()
        btn = discord.ui.Button(label="Kup produkt", style=discord.ButtonStyle.green)
        async def _buy_cb(i: discord.Interaction):
            await i.response.send_modal(TicketModal(i.user, "Zakup produktu"))
        btn.callback = _buy_cb
        view.add_item(btn)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ====== PROMOCJA ======
def create_promo_embed(end_time):
    remaining = (end_time - datetime.utcnow()).total_seconds()
    hours, rem = divmod(int(remaining), 3600)
    minutes, seconds = divmod(rem, 60)
    embed = discord.Embed(
        title="🎉 Witamy na serwerze!",
        description=(
            "Jesteśmy tu, aby pomóc Ci zarobić! 💸\n\n"
            f"🔥 **PROMOCJA -25% na wszystko przez 48h!** 🔥\n\n"
            f"⏳ Pozostało: **{hours:02d}:{minutes:02d}:{seconds:02d}**"
        ),
        color=discord.Color.green()
    )
    embed.set_image(url=PROMO_IMAGE)
    embed.set_footer(text="Nie przegap okazji! 🚀")
    return embed

async def promo_countdown_loop():
    await bot.wait_until_ready()
    promo_channel = bot.get_channel(PROMO_CHANNEL_ID)
    if not promo_channel:
        print("Nie znaleziono kanału promocji.")
        return
    end_time = datetime.utcnow() + timedelta(hours=PROMO_DURATION_HOURS)
    msg = await promo_channel.send(embed=create_promo_embed(end_time))
    while True:
        remaining = (end_time - datetime.utcnow()).total_seconds()
        if remaining <= 0:
            embed = discord.Embed(title="🎉 PROMOCJA ZAKOŃCZONA!", description="Dziękujemy za udział! 🚀", color=discord.Color.red())
            embed.set_image(url=PROMO_IMAGE)
            await msg.edit(embed=embed)
            break
        await msg.edit(embed=create_promo_embed(end_time))
        await asyncio.sleep(60)

# ====== AUTO BUMP ======
async def auto_bump_loop():
    await bot.wait_until_ready()
    bump_channel = bot.get_channel(BUMP_CHANNEL_ID)
    if not bump_channel:
        print("Nie znaleziono kanału do bumpa.")
        return
    while True:
        try:
            await bump_channel.send("/bump")
            print(f"✅ Wysłano /bump w kanale {bump_channel.name}")
        except Exception as e:
            print(f"❌ Błąd podczas bump: {e}")
        await asyncio.sleep(BUMP_INTERVAL_HOURS * 3600)

# ====== KOMENDY PREFIX ======
@bot.command(name="regulamin")
async def regulamin(ctx):
    embed = discord.Embed(title="📜 Regulamin Serwera", description="Witaj na naszym serwerze! Prosimy o przestrzeganie zasad.", color=discord.Color.blue())
    embed.add_field(name="1️⃣ Pełna kultura", value="Szanuj innych.", inline=False)
    embed.add_field(name="2️⃣ Zero scamu", value="Nie wysyłaj phishingu.", inline=False)
    embed.add_field(name="3️⃣ Prywatność", value="Nie udostępniaj cudzych danych.", inline=False)
    embed.add_field(name="4️⃣ Ticket Support", value="Używaj ticketów.", inline=False)
    embed.add_field(name="5️⃣ Dobre zachowanie", value="Bądź miły i pomagaj.", inline=False)
    embed.set_image(url=PROMO_IMAGE)
    embed.set_footer(text="Regulamin by M0N3HUS8L")
    await ctx.send(embed=embed)

@bot.command(name="ticketpanel")
async def ticketpanel(ctx):
    embed = discord.Embed(title="🎫 Kliknij Aby Stworzyć Ticketa", description="Wybierz kategorię ticketa", color=discord.Color.green())
    embed.set_image(url=PROMO_IMAGE)
    await ctx.send(embed=embed, view=TicketCategoryView())

@bot.command(name="oferta")
async def oferta_prefix(ctx):
    embed = discord.Embed(title="🛒 Oferta produktów", description="Kliknij w dropdown", color=discord.Color.gold())
    embed.set_image(url=PROMO_IMAGE)
    await ctx.send(embed=embed, view=OfferSelectView())

# ====== SLASH ======
@bot.tree.command(name="oferta", description="Sprawdź ofertę produktów")
async def oferta_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Oferta produktów", description="Kliknij w dropdown", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, view=OfferSelectView(), ephemeral=True)

# ====== READY ======
@bot.event
async def on_ready():
    print(f"Bot zalogowany jako {bot.user} (ID: {bot.user.id})")
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print("Slash commands zsynchronizowane.")
    # Start background tasks
    bot.loop.create_task(promo_countdown_loop())
    bot.loop.create_task(auto_bump_loop())

# ====== RUN ======
bot.run(TOKEN)

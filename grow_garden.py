#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌱 Grow Garden | باغ سبز
نسخه نهایی بدون باگ
- رفع کامل database is locked
- دکمه برداشت (تکی و همه) کاملاً کار می‌کند
- ساخته شده توسط @silent_vision
"""

import os
import sys
import time
import sqlite3
import logging
import random
import traceback
import re
from typing import Optional, List, Tuple
from contextlib import contextmanager

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

# ======================== تنظیمات ========================
BOT_TOKEN = "CFJHBC0MRHYDXQULQCLLOHPYEUKPSVSWGBGZLQHHKMPWZUOFSNXRDEZEIKHYSRDT"

# آیدی خودت را اینجا بگذار تا پنل مدیریت فعال شود
ADMIN_IDS = [
    # "u0Hrfvc0470e7f2f3f6d2074b14fd99b"
]

DB_PATH = "grow_garden.db"
OFFSET_FILE = "offset.txt"
POLL_INTERVAL = 1.4
MAX_RETRY = 3
MAX_MESSAGE_AGE = 180

START_MONEY = 500
START_WATER = 25
START_ENERGY = 50
START_SEEDS = {"wheat": 4, "carrot": 3, "potato": 2}
WATER_REGEN_PER_HOUR = 6
ENERGY_REGEN_PER_HOUR = 4
LUCKY_BOX_PRICE = 150

# ======================== لاگ ========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("grow_garden.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GrowGarden")

# ======================== داده‌های بازی ========================
SEEDS = {
    "wheat": {"name": "🌾 گندم", "rarity": "common", "price": 20, "sell": 48, "grow": 30, "water": 1, "xp": 8, "mut": 0.02, "gold": 0.01, "leg": 0.001},
    "carrot": {"name": "🥕 هویج", "rarity": "common", "price": 25, "sell": 58, "grow": 55, "water": 1, "xp": 10, "mut": 0.025, "gold": 0.012, "leg": 0.001},
    "potato": {"name": "🥔 سیب‌زمینی", "rarity": "common", "price": 30, "sell": 68, "grow": 80, "water": 2, "xp": 12, "mut": 0.02, "gold": 0.01, "leg": 0.001},
    "corn": {"name": "🌽 ذرت", "rarity": "common", "price": 35, "sell": 78, "grow": 110, "water": 2, "xp": 14, "mut": 0.03, "gold": 0.015, "leg": 0.002},
    "tomato": {"name": "🍅 گوجه", "rarity": "common", "price": 40, "sell": 88, "grow": 140, "water": 2, "xp": 16, "mut": 0.025, "gold": 0.012, "leg": 0.001},
    "onion": {"name": "🧅 پیاز", "rarity": "common", "price": 22, "sell": 52, "grow": 45, "water": 1, "xp": 9, "mut": 0.02, "gold": 0.01, "leg": 0.001},
    "cucumber": {"name": "🥒 خیار", "rarity": "common", "price": 28, "sell": 62, "grow": 70, "water": 1, "xp": 11, "mut": 0.022, "gold": 0.011, "leg": 0.001},
    "strawberry": {"name": "🍓 توت‌فرنگی", "rarity": "rare", "price": 80, "sell": 185, "grow": 180, "water": 2, "xp": 30, "mut": 0.05, "gold": 0.03, "leg": 0.005},
    "blueberry": {"name": "🫐 بلوبری", "rarity": "rare", "price": 90, "sell": 205, "grow": 210, "water": 2, "xp": 35, "mut": 0.05, "gold": 0.03, "leg": 0.005},
    "grape": {"name": "🍇 انگور", "rarity": "rare", "price": 100, "sell": 225, "grow": 240, "water": 3, "xp": 40, "mut": 0.06, "gold": 0.035, "leg": 0.006},
    "cherry": {"name": "🍒 گیلاس", "rarity": "rare", "price": 110, "sell": 245, "grow": 270, "water": 3, "xp": 45, "mut": 0.055, "gold": 0.032, "leg": 0.005},
    "watermelon": {"name": "🍉 هندوانه", "rarity": "rare", "price": 130, "sell": 285, "grow": 300, "water": 3, "xp": 50, "mut": 0.05, "gold": 0.03, "leg": 0.005},
    "pepper": {"name": "🌶️ فلفل", "rarity": "rare", "price": 70, "sell": 165, "grow": 150, "water": 2, "xp": 28, "mut": 0.04, "gold": 0.025, "leg": 0.004},
    "rose": {"name": "🌹 رز", "rarity": "epic", "price": 250, "sell": 560, "grow": 300, "water": 3, "xp": 80, "mut": 0.08, "gold": 0.05, "leg": 0.01},
    "tulip": {"name": "🌷 لاله", "rarity": "epic", "price": 280, "sell": 610, "grow": 360, "water": 3, "xp": 90, "mut": 0.08, "gold": 0.05, "leg": 0.01},
    "lavender": {"name": "🪻 اسطوخودوس", "rarity": "epic", "price": 300, "sell": 660, "grow": 420, "water": 3, "xp": 100, "mut": 0.09, "gold": 0.055, "leg": 0.012},
    "lotus": {"name": "🪷 نیلوفر", "rarity": "epic", "price": 350, "sell": 760, "grow": 480, "water": 4, "xp": 120, "mut": 0.1, "gold": 0.06, "leg": 0.015},
    "magic_flower": {"name": "🌺 گل جادویی", "rarity": "epic", "price": 400, "sell": 920, "grow": 540, "water": 4, "xp": 150, "mut": 0.12, "gold": 0.07, "leg": 0.02},
    "orchid": {"name": "🌸 ارکیده", "rarity": "epic", "price": 320, "sell": 710, "grow": 400, "water": 3, "xp": 110, "mut": 0.09, "gold": 0.055, "leg": 0.012},
    "sun_flower": {"name": "🌟 گل خورشید", "rarity": "legendary", "price": 800, "sell": 2050, "grow": 600, "water": 5, "xp": 250, "mut": 0.15, "gold": 0.1, "leg": 0.04},
    "moon_flower": {"name": "🌙 گل ماه", "rarity": "legendary", "price": 900, "sell": 2250, "grow": 720, "water": 5, "xp": 280, "mut": 0.15, "gold": 0.1, "leg": 0.04},
    "dragon_tree": {"name": "🐉 درخت اژدها", "rarity": "legendary", "price": 1200, "sell": 3100, "grow": 900, "water": 6, "xp": 350, "mut": 0.18, "gold": 0.12, "leg": 0.05},
    "crystal_flower": {"name": "💎 گل کریستالی", "rarity": "legendary", "price": 1500, "sell": 3900, "grow": 1080, "water": 6, "xp": 400, "mut": 0.2, "gold": 0.15, "leg": 0.06},
    "mythic_flower": {"name": "👑 گل افسانه‌ای", "rarity": "legendary", "price": 2000, "sell": 5200, "grow": 1200, "water": 7, "xp": 500, "mut": 0.25, "gold": 0.18, "leg": 0.08},
    "phoenix_flower": {"name": "🔥 گل ققنوس", "rarity": "legendary", "price": 1100, "sell": 2850, "grow": 800, "water": 5, "xp": 320, "mut": 0.17, "gold": 0.11, "leg": 0.045},
    "golden_flower": {"name": "✨ گل طلایی افسانه‌ای", "rarity": "mythic", "price": 5000, "sell": 15500, "grow": 1800, "water": 8, "xp": 1000, "mut": 0.3, "gold": 0.5, "leg": 0.2},
    "rainbow_flower": {"name": "🌈 گل رنگین‌کمانی", "rarity": "mythic", "price": 6000, "sell": 18500, "grow": 2100, "water": 8, "xp": 1200, "mut": 0.35, "gold": 0.4, "leg": 0.25},
    "mythic_king": {"name": "👑 گل اسطوره‌ای", "rarity": "mythic", "price": 8000, "sell": 25500, "grow": 2400, "water": 10, "xp": 1500, "mut": 0.4, "gold": 0.45, "leg": 0.3},
}

FERTILIZERS = {
    "normal": {"name": "🧪 کود معمولی", "price": 50, "grow_reduce": 0.12, "mut_bonus": 0.015, "gold_bonus": 0.008, "leg_bonus": 0.002},
    "fast": {"name": "⚡ کود رشد سریع", "price": 120, "grow_reduce": 0.28, "mut_bonus": 0.025, "gold_bonus": 0.012, "leg_bonus": 0.003},
    "rare": {"name": "💎 کود کمیاب", "price": 250, "grow_reduce": 0.18, "mut_bonus": 0.06, "gold_bonus": 0.035, "leg_bonus": 0.012},
    "golden": {"name": "🌟 کود طلایی", "price": 500, "grow_reduce": 0.22, "mut_bonus": 0.09, "gold_bonus": 0.09, "leg_bonus": 0.025},
    "legendary": {"name": "👑 کود لجندری", "price": 1200, "grow_reduce": 0.32, "mut_bonus": 0.16, "gold_bonus": 0.13, "leg_bonus": 0.055},
}

SOILS = {
    "normal": {"name": "🟫 خاک معمولی", "price": 0, "grow_bonus": 0.0, "mut_bonus": 0.0, "gold_bonus": 0.0, "leg_bonus": 0.0},
    "fertile": {"name": "🌱 خاک حاصلخیز", "price": 300, "grow_bonus": 0.15, "mut_bonus": 0.025, "gold_bonus": 0.012, "leg_bonus": 0.003},
    "rare": {"name": "💎 خاک کمیاب", "price": 800, "grow_bonus": 0.12, "mut_bonus": 0.055, "gold_bonus": 0.035, "leg_bonus": 0.012},
    "magic": {"name": "🌟 خاک جادویی", "price": 1500, "grow_bonus": 0.22, "mut_bonus": 0.11, "gold_bonus": 0.055, "leg_bonus": 0.022},
    "legendary": {"name": "👑 خاک افسانه‌ای", "price": 4000, "grow_bonus": 0.32, "mut_bonus": 0.16, "gold_bonus": 0.11, "leg_bonus": 0.055},
}

PETS = {
    "chicken": {"name": "🐔 مرغ", "price": 200, "effect": "extra_harvest", "bonus": 0.06},
    "rabbit": {"name": "🐰 خرگوش", "price": 350, "effect": "extra_product", "bonus": 0.09},
    "cat": {"name": "🐱 گربه", "price": 400, "effect": "seed_chance", "bonus": 0.12},
    "dog": {"name": "🐶 سگ", "price": 450, "effect": "xp_bonus", "bonus": 0.12},
    "fox": {"name": "🦊 روباه", "price": 600, "effect": "mut_bonus", "bonus": 0.06},
    "panda": {"name": "🐼 پاندا", "price": 1200, "effect": "gold_bonus", "bonus": 0.09},
    "dragon": {"name": "🐉 اژدها", "price": 5000, "effect": "leg_bonus", "bonus": 0.12},
}

WEATHERS = {
    "sunny": {"name": "☀️ آفتابی", "grow_bonus": 0.06, "water_save": 0.0, "mut_bonus": 0.0},
    "rainy": {"name": "🌧️ بارانی", "grow_bonus": 0.0, "water_save": 0.35, "mut_bonus": 0.025},
    "storm": {"name": "⛈️ طوفانی", "grow_bonus": -0.04, "water_save": 0.0, "mut_bonus": 0.09},
    "snowy": {"name": "❄️ برفی", "grow_bonus": -0.08, "water_save": 0.0, "mut_bonus": 0.03},
    "foggy": {"name": "🌫️ مه‌آلود", "grow_bonus": 0.0, "water_save": 0.12, "mut_bonus": 0.04},
    "rainbow": {"name": "🌈 رنگین‌کمانی", "grow_bonus": 0.12, "water_save": 0.12, "mut_bonus": 0.11},
    "magic_night": {"name": "🌙 شب جادویی", "grow_bonus": 0.16, "water_save": 0.0, "mut_bonus": 0.16},
}

MUTATIONS = {
    "golden": {"name": "🌟 طلایی", "mult": 3.0},
    "rainbow": {"name": "🌈 رنگین‌کمانی", "mult": 4.2},
    "crystal": {"name": "💎 کریستالی", "mult": 3.6},
    "inferno": {"name": "🔥 آتشین", "mult": 2.9},
    "frozen": {"name": "❄️ یخ‌زده", "mult": 2.6},
    "electric": {"name": "⚡ الکتریکی", "mult": 3.3},
    "moonlit": {"name": "🌙 مهتابی", "mult": 3.9},
    "solar": {"name": "☀️ خورشیدی", "mult": 3.7},
    "mythic": {"name": "👑 اسطوره‌ای", "mult": 6.5},
}

GARDEN_LEVELS = {
    1: {"plots": 4, "cost": 0},
    2: {"plots": 6, "cost": 500},
    3: {"plots": 8, "cost": 1500},
    4: {"plots": 10, "cost": 4000},
    5: {"plots": 12, "cost": 10000},
    6: {"plots": 15, "cost": 25000},
}

DAILY_REWARDS = {
    1: {"money": 120},
    2: {"seed": "carrot", "count": 2},
    3: {"fertilizer": "normal", "count": 1},
    4: {"diamond": 6},
    5: {"lucky_box": 1},
    6: {"money": 280},
    7: {"diamond": 18, "seed": "rose", "count": 1},
}

# ======================== دیتابیس (بدون قفل) ========================
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 60000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY, chat_id TEXT, name TEXT DEFAULT 'باغبان', username TEXT,
            level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0, money INTEGER DEFAULT 500, diamond INTEGER DEFAULT 0,
            water INTEGER DEFAULT 25, energy INTEGER DEFAULT 50, garden_level INTEGER DEFAULT 1,
            soil_type TEXT DEFAULT 'normal', plots_count INTEGER DEFAULT 4,
            harvest_count INTEGER DEFAULT 0, plant_count INTEGER DEFAULT 0,
            gold_plants INTEGER DEFAULT 0, leg_plants INTEGER DEFAULT 0, quests_done INTEGER DEFAULT 0,
            join_date REAL, last_active REAL, last_water_regen REAL, last_energy_regen REAL,
            daily_streak INTEGER DEFAULT 0, last_daily REAL DEFAULT 0,
            current_weather TEXT DEFAULT 'sunny', weather_until REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS plots (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, plot_index INTEGER,
            seed_id TEXT, planted_at REAL, finish_at REAL, water_needed INTEGER DEFAULT 0,
            watered INTEGER DEFAULT 0, fertilizer TEXT, mutation TEXT,
            is_gold INTEGER DEFAULT 0, is_leg INTEGER DEFAULT 0, status TEXT DEFAULT 'empty',
            UNIQUE(user_id, plot_index)
        );
        CREATE TABLE IF NOT EXISTS inventory (
            user_id TEXT, item_type TEXT, item_id TEXT, quantity INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, item_type, item_id)
        );
        CREATE TABLE IF NOT EXISTS pets (user_id TEXT, pet_id TEXT, PRIMARY KEY (user_id, pet_id));
        CREATE TABLE IF NOT EXISTS processed_updates (update_key TEXT PRIMARY KEY, processed_at REAL);
        CREATE INDEX IF NOT EXISTS idx_plots_user ON plots(user_id);
        CREATE INDEX IF NOT EXISTS idx_inv_user ON inventory(user_id);
        CREATE INDEX IF NOT EXISTS idx_proc ON processed_updates(update_key);
        """)
    logger.info("دیتابیس آماده شد.")

def load_offset() -> Optional[str]:
    try:
        if os.path.exists(OFFSET_FILE):
            with open(OFFSET_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val and val.lower() != "none":
                    return val
    except Exception:
        pass
    return None

def save_offset(offset_id: Optional[str]):
    try:
        with open(OFFSET_FILE, "w", encoding="utf-8") as f:
            f.write(str(offset_id) if offset_id else "")
    except Exception:
        pass

# ======================== API ========================
class RubikaAPI:
    def __init__(self, token: str):
        self.token = token
        self.base = f"https://botapi.rubika.ir/v3/{token}"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.offset_id = load_offset()
        logger.info(f"Offset بارگذاری شد: {self.offset_id}")

    def _post(self, method: str, data: dict = None, retries: int = MAX_RETRY) -> dict:
        url = f"{self.base}/{method}"
        for attempt in range(retries):
            try:
                r = self.session.post(url, json=data or {}, timeout=25)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.warning(f"API {method} تلاش {attempt+1}: {e}")
                time.sleep(0.8 * (attempt + 1))
        return {"status": "ERROR"}

    def get_updates(self, limit: int = 40) -> dict:
        payload = {"limit": limit}
        if self.offset_id:
            payload["offset_id"] = self.offset_id
        res = self._post("getUpdates", payload)
        if res.get("status") == "OK" and "data" in res:
            data = res["data"]
            next_off = data.get("next_offset_id")
            if next_off:
                self.offset_id = str(next_off)
                save_offset(self.offset_id)
            return data
        return {}

    def send_message(self, chat_id: str, text: str, chat_keypad: dict = None,
                     inline_keypad: dict = None, chat_keypad_type: str = "New") -> dict:
        payload = {"chat_id": str(chat_id), "text": text}
        if chat_keypad:
            payload["chat_keypad"] = chat_keypad
            payload["chat_keypad_type"] = chat_keypad_type
        if inline_keypad:
            payload["inline_keypad"] = inline_keypad
        return self._post("sendMessage", payload)

    def get_chat(self, chat_id: str) -> dict:
        return self._post("getChat", {"chat_id": str(chat_id)})

    def get_name(self, chat_id: str) -> str:
        try:
            res = self.get_chat(chat_id)
            if res.get("status") == "OK":
                chat = res.get("data", {}).get("chat", {}) or res.get("data", {})
                return (chat.get("first_name") or chat.get("title") or
                        chat.get("username") or chat.get("last_name") or "باغبان")
        except Exception:
            pass
        return "باغبان"

# ======================== کیبورد ========================
def btn(text: str, bid: str) -> dict:
    return {"id": str(bid), "type": "Simple", "button_text": str(text)}

def make_kb(rows: List[List[Tuple[str, str]]], resize=True) -> dict:
    return {
        "rows": [{"buttons": [btn(t, i) for t, i in row]} for row in rows],
        "resize_keyboard": resize,
        "one_time_keyboard": False
    }

def main_kb():
    return make_kb([
        [("🌳 باغ من", "garden"), ("👤 پروفایل", "profile")],
        [("🛒 فروشگاه", "shop"), ("💧 آب دادن همه", "water_all")],
        [("🌾 برداشت همه", "harvest_all"), ("🎁 جعبه شانسی", "lucky_box")],
        [("🏆 لیدربورد", "leaderboard"), ("🎯 مأموریت‌ها", "quests")],
        [("🎁 جایزه روزانه", "daily"), ("🌦️ آب‌وهوا", "weather")],
        [("🐾 حیوانات من", "pets"), ("📖 آموزش", "help")],
    ])

def shop_kb():
    return make_kb([
        [("🌱 خرید بذر", "shop_seeds"), ("🧪 خرید کود", "shop_fert")],
        [("🟫 خرید خاک", "shop_soil"), ("🏡 ارتقای باغ", "shop_upgrade")],
        [("🐾 خرید حیوان", "shop_pets"), ("🎁 جعبه شانسی", "lucky_box")],
        [("🔙 بازگشت به منو", "main_menu")],
    ])

def admin_kb():
    return make_kb([
        [("👥 تعداد کاربران", "adm_users"), ("📊 آمار بازی", "adm_stats")],
        [("💾 وضعیت دیتابیس", "adm_db"), ("🔄 تازه‌سازی", "adm_refresh")],
        [("🔙 خروج از پنل", "main_menu")],
    ])

# ======================== بازیکن ========================
def get_player(user_id: str, chat_id: str = "", name: str = None) -> dict:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM players WHERE user_id=?", (user_id,))
        row = c.fetchone()
        now = time.time()
        if row:
            c.execute("UPDATE players SET last_active=?, chat_id=? WHERE user_id=?", (now, chat_id or row["chat_id"], user_id))
            if name and name != "باغبان" and (not row["name"] or row["name"] == "باغبان"):
                c.execute("UPDATE players SET name=? WHERE user_id=?", (name, user_id))
            return dict(c.execute("SELECT * FROM players WHERE user_id=?", (user_id,)).fetchone())
        c.execute("""INSERT INTO players (user_id, chat_id, name, money, water, energy,
                     join_date, last_active, last_water_regen, last_energy_regen, weather_until)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (user_id, chat_id, name or "باغبان", START_MONEY, START_WATER, START_ENERGY,
                   now, now, now, now, now + 3600))
        for i in range(4):
            c.execute("INSERT INTO plots (user_id, plot_index, status) VALUES (?,?, 'empty')", (user_id, i))
        for sid, qty in START_SEEDS.items():
            c.execute("INSERT INTO inventory (user_id, item_type, item_id, quantity) VALUES (?,?,?,?)",
                      (user_id, "seed", sid, qty))
        return dict(c.execute("SELECT * FROM players WHERE user_id=?", (user_id,)).fetchone())

def add_item(user_id: str, itype: str, iid: str, qty: int = 1):
    with get_db() as conn:
        conn.execute("""INSERT INTO inventory (user_id, item_type, item_id, quantity) VALUES (?,?,?,?)
                        ON CONFLICT(user_id, item_type, item_id) DO UPDATE SET quantity = quantity + ?""",
                     (user_id, itype, iid, qty, qty))

def remove_item(user_id: str, itype: str, iid: str, qty: int = 1) -> bool:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_type=? AND item_id=?", (user_id, itype, iid))
        r = c.fetchone()
        if not r or r["quantity"] < qty:
            return False
        c.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id=? AND item_type=? AND item_id=?",
                  (qty, user_id, itype, iid))
        return True

def change_money(user_id: str, amount: int) -> bool:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT money FROM players WHERE user_id=?", (user_id,))
        r = c.fetchone()
        if not r or (r["money"] + amount) < 0:
            return False
        c.execute("UPDATE players SET money = money + ? WHERE user_id=?", (amount, user_id))
        return True

def change_diamond(user_id: str, amount: int) -> bool:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT diamond FROM players WHERE user_id=?", (user_id,))
        r = c.fetchone()
        if not r or (r["diamond"] + amount) < 0:
            return False
        c.execute("UPDATE players SET diamond = diamond + ? WHERE user_id=?", (amount, user_id))
        return True

def regen(user_id: str):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT water, energy, last_water_regen, last_energy_regen FROM players WHERE user_id=?", (user_id,))
        r = c.fetchone()
        if not r:
            return
        now = time.time()
        hw = (now - (r["last_water_regen"] or now)) / 3600
        aw = int(hw * WATER_REGEN_PER_HOUR)
        if aw > 0:
            c.execute("UPDATE players SET water=MIN(120, water+?), last_water_regen=? WHERE user_id=?", (aw, now, user_id))
        he = (now - (r["last_energy_regen"] or now)) / 3600
        ae = int(he * ENERGY_REGEN_PER_HOUR)
        if ae > 0:
            c.execute("UPDATE players SET energy=MIN(120, energy+?), last_energy_regen=? WHERE user_id=?", (ae, now, user_id))

def update_weather(user_id: str):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT weather_until FROM players WHERE user_id=?", (user_id,))
        r = c.fetchone()
        if r and time.time() > (r["weather_until"] or 0):
            w = random.choice(list(WEATHERS.keys()))
            c.execute("UPDATE players SET current_weather=?, weather_until=? WHERE user_id=?",
                      (w, time.time() + random.randint(1800, 7200), user_id))

# ======================== باغ (بدون تودرتو بودن کانکشن) ========================
def get_plots(user_id: str) -> List[dict]:
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM plots WHERE user_id=? ORDER BY plot_index", (user_id,)).fetchall()]

def plant(user_id: str, idx: int, seed_id: str) -> Tuple[bool, str]:
    if seed_id not in SEEDS:
        return False, "بذر نامعتبر."
    if not remove_item(user_id, "seed", seed_id, 1):
        return False, "بذر کافی ندارید."
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT status FROM plots WHERE user_id=? AND plot_index=?", (user_id, idx))
        pl = c.fetchone()
        if not pl or pl["status"] != "empty":
            add_item(user_id, "seed", seed_id, 1)
            return False, "این زمین خالی نیست."
        p = dict(c.execute("SELECT * FROM players WHERE user_id=?", (user_id,)).fetchone())
        soil = SOILS.get(p["soil_type"], SOILS["normal"])
        weather = WEATHERS.get(p["current_weather"], WEATHERS["sunny"])
        grow = SEEDS[seed_id]["grow"] * (1 - soil["grow_bonus"]) * (1 - weather.get("grow_bonus", 0))
        grow = max(15, int(grow))
        now = time.time()
        c.execute("""UPDATE plots SET seed_id=?, planted_at=?, finish_at=?, water_needed=?, watered=0,
                     fertilizer=NULL, mutation=NULL, is_gold=0, is_leg=0, status='growing'
                     WHERE user_id=? AND plot_index=?""",
                  (seed_id, now, now + grow, SEEDS[seed_id]["water"], user_id, idx))
        c.execute("UPDATE players SET plant_count = plant_count + 1 WHERE user_id=?", (user_id,))
    return True, f"✅ {SEEDS[seed_id]['name']} کاشته شد!\n⏳ زمان رشد: {grow} ثانیه"

def water_one(user_id: str, idx: int) -> Tuple[bool, str]:
    regen(user_id)
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM plots WHERE user_id=? AND plot_index=?", (user_id, idx))
        pl = c.fetchone()
        if not pl or not pl["seed_id"]:
            return False, "گیاهی وجود ندارد."
        if pl["watered"] >= pl["water_needed"]:
            return False, "این گیاه دیگر نیاز به آب ندارد."
        c.execute("SELECT water FROM players WHERE user_id=?", (user_id,))
        if c.fetchone()["water"] < 1:
            return False, "💧 آب کافی ندارید."
        c.execute("UPDATE players SET water = water - 1 WHERE user_id=?", (user_id,))
        c.execute("UPDATE plots SET watered = watered + 1 WHERE user_id=? AND plot_index=?", (user_id, idx))
    return True, "💧 آبیاری انجام شد!"

def harvest_one(user_id: str, idx: int) -> Tuple[bool, str]:
    """نسخه بدون تودرتو بودن کانکشن - رفع کامل database is locked"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM plots WHERE user_id=? AND plot_index=?", (user_id, idx))
        pl = c.fetchone()
        if not pl or not pl["seed_id"]:
            return False, "چیزی برای برداشت نیست."
        now = time.time()
        if pl["finish_at"] > now:
            return False, f"هنوز آماده نیست ({int(pl['finish_at']-now)} ثانیه مانده)."

        seed = SEEDS[pl["seed_id"]]
        p = dict(c.execute("SELECT * FROM players WHERE user_id=?", (user_id,)).fetchone())
        soil = SOILS.get(p["soil_type"], SOILS["normal"])
        weather = WEATHERS.get(p["current_weather"], WEATHERS["sunny"])

        mut_c = seed["mut"] + soil["mut_bonus"] + weather.get("mut_bonus", 0)
        gold_c = seed["gold"] + soil["gold_bonus"]
        leg_c = seed["leg"] + soil["leg_bonus"]

        if pl["fertilizer"] and pl["fertilizer"] in FERTILIZERS:
            f = FERTILIZERS[pl["fertilizer"]]
            mut_c += f["mut_bonus"]
            gold_c += f["gold_bonus"]
            leg_c += f["leg_bonus"]

        pets = [r["pet_id"] for r in c.execute("SELECT pet_id FROM pets WHERE user_id=?", (user_id,)).fetchall()]
        for pid in pets:
            pe = PETS.get(pid, {})
            if pe.get("effect") == "mut_bonus": mut_c += pe["bonus"]
            if pe.get("effect") == "gold_bonus": gold_c += pe["bonus"]
            if pe.get("effect") == "leg_bonus": leg_c += pe["bonus"]

        is_gold = 1 if random.random() < gold_c else 0
        is_leg = 1 if random.random() < leg_c else 0
        mutation = random.choice(list(MUTATIONS.keys())) if random.random() < mut_c else None

        sell = seed["sell"]
        if is_gold:
            sell = int(sell * 3.2)
            c.execute("UPDATE players SET gold_plants = gold_plants + 1 WHERE user_id=?", (user_id,))
        if is_leg:
            sell = int(sell * 5.5)
            c.execute("UPDATE players SET leg_plants = leg_plants + 1 WHERE user_id=?", (user_id,))
        if mutation:
            sell = int(sell * MUTATIONS[mutation]["mult"])
        if any(PETS.get(pid, {}).get("effect") == "extra_product" for pid in pets) and random.random() < 0.12:
            sell = int(sell * 1.25)

        # پول و آمار
        c.execute("UPDATE players SET money = money + ?, harvest_count = harvest_count + 1 WHERE user_id=?", (sell, user_id))

        # XP داخل همین کانکشن
        xp_gain = seed["xp"] + (60 if is_leg else 25 if is_gold else 0)
        c.execute("SELECT level, xp FROM players WHERE user_id=?", (user_id,))
        r = c.fetchone()
        xp = r["xp"] + xp_gain
        lvl = r["level"]
        while xp >= lvl * 100:
            xp -= lvl * 100
            lvl += 1
        c.execute("UPDATE players SET level=?, xp=? WHERE user_id=?", (lvl, xp, user_id))

        # بذر برگشتی
        if random.random() < 0.32 + (0.12 if any(PETS.get(pid, {}).get("effect") == "seed_chance" for pid in pets) else 0):
            c.execute("""INSERT INTO inventory (user_id, item_type, item_id, quantity) VALUES (?,?,?,1)
                         ON CONFLICT(user_id, item_type, item_id) DO UPDATE SET quantity = quantity + 1""",
                      (user_id, "seed", pl["seed_id"]))

        # پاک کردن زمین
        c.execute("""UPDATE plots SET seed_id=NULL, planted_at=NULL, finish_at=NULL, water_needed=0,
                     watered=0, fertilizer=NULL, mutation=NULL, is_gold=0, is_leg=0, status='empty'
                     WHERE user_id=? AND plot_index=?""", (user_id, idx))

        msg = f"🌾 برداشت موفق!\n{seed['name']}\n💰 +{sell:,} سکه\n✨ +{xp_gain} XP"
        if is_gold: msg += "\n🌟 گیاه طلایی!"
        if is_leg: msg += "\n👑 گیاه لجندری!"
        if mutation: msg += f"\n🧬 جهش: {MUTATIONS[mutation]['name']}"
        return True, msg

# ======================== هندلرها ========================
api = RubikaAPI(BOT_TOKEN)

def is_processed(key: str) -> bool:
    with get_db() as conn:
        return bool(conn.execute("SELECT 1 FROM processed_updates WHERE update_key=?", (key,)).fetchone())

def mark_processed(key: str):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO processed_updates (update_key, processed_at) VALUES (?,?)", (key, time.time()))

def handle_start(chat_id, user_id, name):
    p = get_player(user_id, chat_id, name)
    text = (
        f"🌱 سلام {p['name']} عزیز!\n\n"
        f"به بازی **Grow Garden | باغ سبز** خوش آمدی!\n\n"
        f"یک باغ کوچک، {p['money']} سکه و چند بذر اولیه بهت دادم.\n"
        f"از منوی پایین شروع کن و باغبانی کن!\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🛠 ساخته شده توسط @silent_vision"
    )
    api.send_message(chat_id, text, chat_keypad=main_kb())

def handle_profile(chat_id, user_id):
    regen(user_id)
    update_weather(user_id)
    p = get_player(user_id, chat_id)
    text = (
        f"👤 پروفایل باغبان\n"
        f"━━━━━━━━━━━━━━\n"
        f"🆔 آیدی: `{user_id}`\n"
        f"🏷️ نام: {p['name']}\n"
        f"⭐ سطح: {p['level']}\n"
        f"✨ XP: {p['xp']}/{p['level']*100}\n"
        f"💰 پول: {p['money']:,}\n"
        f"💎 الماس: {p['diamond']}\n"
        f"💧 آب: {p['water']}\n"
        f"⚡ انرژی: {p['energy']}\n"
        f"🏡 سطح باغ: {p['garden_level']}\n"
        f"🟫 خاک: {SOILS.get(p['soil_type'],{}).get('name',p['soil_type'])}\n"
        f"🌱 زمین‌ها: {p['plots_count']}\n"
        f"🌾 برداشت‌ها: {p['harvest_count']}\n"
        f"🌟 طلایی: {p['gold_plants']}\n"
        f"👑 لجندری: {p['leg_plants']}\n\n"
        f"🛠 ساخته شده توسط @silent_vision"
    )
    api.send_message(chat_id, text, chat_keypad=main_kb())

def handle_garden(chat_id, user_id):
    regen(user_id)
    update_weather(user_id)
    plots = get_plots(user_id)
    p = get_player(user_id, chat_id)
    now = time.time()
    lines = [f"🌳 باغ {p['name']}\n🏡 سطح: {p['garden_level']} | 🌦️ {WEATHERS.get(p['current_weather'],{}).get('name','☀️')}\n━━━━━━━━━━━━━━"]
    buttons = []
    for pl in plots:
        idx = pl["plot_index"]
        if not pl["seed_id"] or pl["status"] == "empty":
            lines.append(f"🟫 زمین {idx+1}: خالی")
            buttons.append([(f"🌱 کاشت زمین {idx+1}", f"choose_plant_{idx}")])
        else:
            seed = SEEDS.get(pl["seed_id"], {})
            rem = max(0, int(pl["finish_at"] - now))
            if rem <= 0:
                lines.append(f"{seed.get('name','؟')} — 🌳 آماده برداشت")
                buttons.append([(f"🌾 برداشت زمین {idx+1}", f"harvest_{idx}")])
            else:
                need_water = pl["watered"] < pl["water_needed"]
                st = f"🌿 در حال رشد ({rem}ث)" + (" | 💧 نیاز آب" if need_water else "")
                lines.append(f"{seed.get('name','؟')} — {st}")
                row = []
                if need_water:
                    row.append((f"💧 آب زمین {idx+1}", f"water_{idx}"))
                row.append((f"ℹ️ وضعیت {idx+1}", f"status_{idx}"))
                buttons.append(row)
    buttons.append([("🔙 منوی اصلی", "main_menu")])
    api.send_message(chat_id, "\n".join(lines), chat_keypad=make_kb(buttons))

def handle_choose_plant(chat_id, user_id, idx: int):
    with get_db() as conn:
        inv = conn.execute("SELECT item_id, quantity FROM inventory WHERE user_id=? AND item_type='seed' AND quantity>0",
                           (user_id,)).fetchall()
    if not inv:
        api.send_message(chat_id, "❌ بذری در انبار ندارید. از فروشگاه بخرید.", chat_keypad=shop_kb())
        return
    buttons = []
    for r in inv:
        sid = r["item_id"]
        if sid in SEEDS:
            buttons.append([(f"{SEEDS[sid]['name']} (x{r['quantity']})", f"do_plant_{idx}_{sid}")])
    buttons.append([("🔙 بازگشت به باغ", "garden")])
    api.send_message(chat_id, f"🌱 کدام بذر را در زمین {idx+1} می‌کارید؟", chat_keypad=make_kb(buttons))

def handle_shop(chat_id, user_id):
    p = get_player(user_id, chat_id)
    api.send_message(chat_id, f"🛒 فروشگاه\n💰 پول شما: {p['money']:,}\n💎 الماس: {p['diamond']}", chat_keypad=shop_kb())

def handle_shop_seeds(chat_id, user_id, page: int = 0):
    p = get_player(user_id, chat_id)
    items = list(SEEDS.items())
    per_page = 8
    start = page * per_page
    chunk = items[start:start+per_page]
    lines = [f"🌱 خرید بذر (صفحه {page+1})\n💰 پول: {p['money']:,}\n━━━━━━━━━━━━━━"]
    buttons = []
    for sid, s in chunk:
        lines.append(f"{s['name']} | {s['price']} سکه | رشد {s['grow']}ث")
        buttons.append([(f"خرید {s['name']}", f"buy_seed_{sid}")])
    nav = []
    if start > 0:
        nav.append(("◀️ قبلی", f"shop_seeds_{page-1}"))
    if start + per_page < len(items):
        nav.append(("بعدی ▶️", f"shop_seeds_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([("🔙 بازگشت به فروشگاه", "shop")])
    api.send_message(chat_id, "\n".join(lines), chat_keypad=make_kb(buttons))

def handle_buy_seed(chat_id, user_id, seed_id: str):
    if seed_id not in SEEDS:
        api.send_message(chat_id, "بذر نامعتبر.", chat_keypad=shop_kb())
        return
    s = SEEDS[seed_id]
    if not change_money(user_id, -s["price"]):
        api.send_message(chat_id, "❌ پول کافی ندارید.", chat_keypad=shop_kb())
        return
    add_item(user_id, "seed", seed_id, 1)
    api.send_message(chat_id, f"✅ {s['name']} خریداری شد و به انبار اضافه شد!", chat_keypad=shop_kb())

def handle_shop_fert(chat_id, user_id):
    p = get_player(user_id, chat_id)
    lines = [f"🧪 خرید کود\n💰 پول: {p['money']:,}\n━━━━━━━━━━━━━━"]
    buttons = []
    for fid, f in FERTILIZERS.items():
        lines.append(f"{f['name']} — {f['price']} سکه")
        buttons.append([(f"خرید {f['name']}", f"buy_fert_{fid}")])
    buttons.append([("🔙 بازگشت", "shop")])
    api.send_message(chat_id, "\n".join(lines), chat_keypad=make_kb(buttons))

def handle_buy_fert(chat_id, user_id, fid: str):
    if fid not in FERTILIZERS:
        return
    f = FERTILIZERS[fid]
    if not change_money(user_id, -f["price"]):
        api.send_message(chat_id, "❌ پول کافی ندارید.", chat_keypad=shop_kb())
        return
    add_item(user_id, "fert", fid, 1)
    api.send_message(chat_id, f"✅ {f['name']} خریداری شد!", chat_keypad=shop_kb())

def handle_shop_soil(chat_id, user_id):
    p = get_player(user_id, chat_id)
    lines = [f"🟫 خرید خاک\nخاک فعلی: {SOILS.get(p['soil_type'],{}).get('name')}\n💰 پول: {p['money']:,}\n━━━━━━━━━━━━━━"]
    buttons = []
    for sid, s in SOILS.items():
        if sid == "normal":
            continue
        lines.append(f"{s['name']} — {s['price']} سکه")
        buttons.append([(f"خرید {s['name']}", f"buy_soil_{sid}")])
    buttons.append([("🔙 بازگشت", "shop")])
    api.send_message(chat_id, "\n".join(lines), chat_keypad=make_kb(buttons))

def handle_buy_soil(chat_id, user_id, sid: str):
    if sid not in SOILS:
        return
    s = SOILS[sid]
    if not change_money(user_id, -s["price"]):
        api.send_message(chat_id, "❌ پول کافی ندارید.", chat_keypad=shop_kb())
        return
    with get_db() as conn:
        conn.execute("UPDATE players SET soil_type=? WHERE user_id=?", (sid, user_id))
    api.send_message(chat_id, f"✅ خاک باغ به {s['name']} تغییر کرد!", chat_keypad=shop_kb())

def handle_shop_upgrade(chat_id, user_id):
    p = get_player(user_id, chat_id)
    lvl = p["garden_level"]
    next_lvl = lvl + 1
    if next_lvl not in GARDEN_LEVELS:
        api.send_message(chat_id, "🏡 باغ شما به حداکثر سطح رسیده است!", chat_keypad=shop_kb())
        return
    cost = GARDEN_LEVELS[next_lvl]["cost"]
    plots = GARDEN_LEVELS[next_lvl]["plots"]
    text = f"🏡 ارتقای باغ\nسطح فعلی: {lvl}\nسطح بعدی: {next_lvl}\nزمین‌ها: {plots}\nهزینه: {cost:,} سکه\n💰 پول شما: {p['money']:,}"
    buttons = [[(f"✅ ارتقا به سطح {next_lvl}", "do_upgrade")], [("🔙 بازگشت", "shop")]]
    api.send_message(chat_id, text, chat_keypad=make_kb(buttons))

def handle_do_upgrade(chat_id, user_id):
    p = get_player(user_id, chat_id)
    next_lvl = p["garden_level"] + 1
    if next_lvl not in GARDEN_LEVELS:
        api.send_message(chat_id, "حداکثر سطح رسیده.", chat_keypad=shop_kb())
        return
    cost = GARDEN_LEVELS[next_lvl]["cost"]
    if not change_money(user_id, -cost):
        api.send_message(chat_id, "❌ پول کافی ندارید.", chat_keypad=shop_kb())
        return
    new_plots = GARDEN_LEVELS[next_lvl]["plots"]
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE players SET garden_level=?, plots_count=? WHERE user_id=?", (next_lvl, new_plots, user_id))
        current = c.execute("SELECT COUNT(*) as c FROM plots WHERE user_id=?", (user_id,)).fetchone()["c"]
        for i in range(current, new_plots):
            c.execute("INSERT OR IGNORE INTO plots (user_id, plot_index, status) VALUES (?,?, 'empty')", (user_id, i))
    api.send_message(chat_id, f"🎉 باغ به سطح {next_lvl} ارتقا یافت! تعداد زمین‌ها: {new_plots}", chat_keypad=main_kb())

def handle_shop_pets(chat_id, user_id):
    p = get_player(user_id, chat_id)
    with get_db() as conn:
        owned = {r["pet_id"] for r in conn.execute("SELECT pet_id FROM pets WHERE user_id=?", (user_id,)).fetchall()}
    lines = [f"🐾 خرید حیوان\n💰 پول: {p['money']:,}\n━━━━━━━━━━━━━━"]
    buttons = []
    for pid, pet in PETS.items():
        if pid in owned:
            lines.append(f"{pet['name']} — ✅ دارید")
        else:
            lines.append(f"{pet['name']} — {pet['price']} سکه")
            buttons.append([(f"خرید {pet['name']}", f"buy_pet_{pid}")])
    buttons.append([("🔙 بازگشت", "shop")])
    api.send_message(chat_id, "\n".join(lines), chat_keypad=make_kb(buttons))

def handle_buy_pet(chat_id, user_id, pid: str):
    if pid not in PETS:
        return
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM pets WHERE user_id=? AND pet_id=?", (user_id, pid)).fetchone():
            api.send_message(chat_id, "این حیوان را قبلاً دارید.", chat_keypad=shop_kb())
            return
    pet = PETS[pid]
    if not change_money(user_id, -pet["price"]):
        api.send_message(chat_id, "❌ پول کافی ندارید.", chat_keypad=shop_kb())
        return
    with get_db() as conn:
        conn.execute("INSERT INTO pets (user_id, pet_id) VALUES (?,?)", (user_id, pid))
    api.send_message(chat_id, f"✅ {pet['name']} به باغ شما پیوست!", chat_keypad=main_kb())

def handle_lucky(chat_id, user_id):
    if not change_money(user_id, -LUCKY_BOX_PRICE):
        api.send_message(chat_id, "❌ پول کافی ندارید.", chat_keypad=main_kb())
        return
    r = random.random()
    if r < 0.001:
        seed = "golden_flower"
    elif r < 0.05:
        seed = random.choice([k for k,v in SEEDS.items() if v["rarity"]=="legendary"])
    elif r < 0.15:
        seed = random.choice([k for k,v in SEEDS.items() if v["rarity"]=="epic"])
    elif r < 0.40:
        seed = random.choice([k for k,v in SEEDS.items() if v["rarity"]=="rare"])
    else:
        seed = random.choice([k for k,v in SEEDS.items() if v["rarity"]=="common"])
    add_item(user_id, "seed", seed, 1)
    api.send_message(chat_id, f"🎁 جعبه باز شد!\nنتیجه: {SEEDS[seed]['name']}", chat_keypad=main_kb())

def handle_leaderboard(chat_id, user_id):
    with get_db() as conn:
        rows = conn.execute("SELECT name, level, money, harvest_count, gold_plants, leg_plants FROM players ORDER BY money DESC LIMIT 10").fetchall()
    lines = ["🏆 لیدربورد\n━━━━━━━━━━━━━━"]
    medals = ["🥇","🥈","🥉"] + ["🔹"]*7
    for i, r in enumerate(rows):
        lines.append(f"{medals[i]} {r['name']}\n⭐{r['level']} | 💰{r['money']:,} | 🌾{r['harvest_count']}")
    api.send_message(chat_id, "\n".join(lines), chat_keypad=main_kb())

def handle_daily(chat_id, user_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT last_daily, daily_streak FROM players WHERE user_id=?", (user_id,))
        r = c.fetchone()
        now = time.time()
        last = r["last_daily"] or 0
        streak = r["daily_streak"] or 0
        if now - last < 82000:
            api.send_message(chat_id, "🎁 جایزه امروز را قبلاً گرفتید.", chat_keypad=main_kb())
            return
        if now - last > 172800:
            streak = 0
        streak = min(7, streak + 1)
        reward = DAILY_REWARDS.get(streak, DAILY_REWARDS[7])
        msg = f"🎁 جایزه روز {streak} (استریک {streak})\n"
        if "money" in reward:
            change_money(user_id, reward["money"])
            msg += f"💰 +{reward['money']}\n"
        if "diamond" in reward:
            change_diamond(user_id, reward["diamond"])
            msg += f"💎 +{reward['diamond']}\n"
        if "seed" in reward:
            add_item(user_id, "seed", reward["seed"], reward.get("count", 1))
            msg += f"🌱 بذر دریافت شد\n"
        if "fertilizer" in reward:
            add_item(user_id, "fert", reward["fertilizer"], 1)
            msg += "🧪 کود دریافت شد\n"
        if "lucky_box" in reward:
            msg += "🎁 یک جعبه شانسی رایگان!\n"
            add_item(user_id, "seed", random.choice(list(SEEDS.keys())[:10]), 1)
        c.execute("UPDATE players SET last_daily=?, daily_streak=? WHERE user_id=?", (now, streak, user_id))
    api.send_message(chat_id, msg, chat_keypad=main_kb())

def handle_help(chat_id, user_id):
    text = (
        "📖 آموزش Grow Garden\n\n"
        "۱. /start → شروع و دریافت باغ\n"
        "۲. فروشگاه → خرید بذر / کود / خاک / حیوان\n"
        "۳. باغ من → کاشت در زمین خالی\n"
        "۴. آب دادن وقتی گیاه نیاز دارد\n"
        "۵. صبر کردن تا زمان واقعی رشد تمام شود\n"
        "۶. برداشت و کسب پول و XP\n"
        "۷. ارتقای باغ برای زمین بیشتر\n"
        "۸. حیوانات و کود برای شانس بالاتر\n"
        "۹. جایزه روزانه و مأموریت‌ها\n\n"
        "موفق باشید! 🌱\n\n"
        "🛠 ساخته شده توسط @silent_vision"
    )
    api.send_message(chat_id, text, chat_keypad=main_kb())

def handle_weather(chat_id, user_id):
    update_weather(user_id)
    p = get_player(user_id, chat_id)
    w = WEATHERS.get(p["current_weather"], WEATHERS["sunny"])
    rem = max(0, int((p["weather_until"] or 0) - time.time()))
    api.send_message(chat_id, f"🌦️ {w['name']}\n⏳ تغییر بعدی: {rem} ثانیه\nرشد: {w['grow_bonus']*100:.0f}% | صرفه‌جویی آب: {w['water_save']*100:.0f}%", chat_keypad=main_kb())

def handle_pets(chat_id, user_id):
    with get_db() as conn:
        owned = [r["pet_id"] for r in conn.execute("SELECT pet_id FROM pets WHERE user_id=?", (user_id,)).fetchall()]
    lines = ["🐾 حیوانات شما\n━━━━━━━━━━━━━━"]
    for pid in owned:
        lines.append(PETS.get(pid, {}).get("name", pid))
    if not owned:
        lines.append("هنوز حیوانی ندارید.")
    buttons = [[("🛒 خرید حیوان", "shop_pets"), ("🔙 منو", "main_menu")]]
    api.send_message(chat_id, "\n".join(lines), chat_keypad=make_kb(buttons))

def handle_quests(chat_id, user_id):
    api.send_message(chat_id, "🎯 مأموریت‌ها به‌زودی با جوایز بیشتر به‌روزرسانی می‌شوند.\nفعلاً از کاشت و برداشت لذت ببرید!", chat_keypad=main_kb())

def handle_admin(chat_id, user_id, bid: str = None):
    if user_id not in ADMIN_IDS:
        api.send_message(chat_id, "❌ دسترسی ندارید.", chat_keypad=main_kb())
        return
    if bid is None or bid in ("admin_panel", "/admin"):
        api.send_message(chat_id, "🛠️ پنل مدیریت\nفقط برای مدیران", chat_keypad=admin_kb())
        return
    if bid == "adm_users":
        with get_db() as conn:
            cnt = conn.execute("SELECT COUNT(*) as c FROM players").fetchone()["c"]
        api.send_message(chat_id, f"👥 تعداد کاربران: {cnt}", chat_keypad=admin_kb())
    elif bid == "adm_stats":
        with get_db() as conn:
            stats = conn.execute("""SELECT COUNT(*) as users,
                SUM(harvest_count) as harvests, SUM(gold_plants) as golds, SUM(leg_plants) as legs,
                SUM(money) as total_money, SUM(diamond) as total_diamond FROM players""").fetchone()
        api.send_message(chat_id,
            f"📊 آمار بازی:\nکاربران: {stats['users']}\nبرداشت‌ها: {stats['harvests']}\n"
            f"طلایی: {stats['golds']}\nلجندری: {stats['legs']}\n"
            f"مجموع پول: {stats['total_money']:,}\nمجموع الماس: {stats['total_diamond']}",
            chat_keypad=admin_kb())
    elif bid == "adm_db":
        size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        api.send_message(chat_id, f"💾 حجم دیتابیس: {size/1024:.1f} KB", chat_keypad=admin_kb())
    elif bid == "adm_refresh":
        api.send_message(chat_id, "🔄 پنل تازه‌سازی شد.", chat_keypad=admin_kb())

# ======================== پردازش آپدیت ========================
def process_update(update: dict):
    try:
        chat_id = user_id = text = message_id = button_id = msg_time = None

        if update.get("type") == "NewMessage":
            msg = update.get("new_message", {})
            chat_id = update.get("chat_id") or update.get("object_guid")
            user_id = msg.get("sender_id")
            text = (msg.get("text") or "").strip()
            message_id = str(msg.get("message_id", ""))
            aux = msg.get("aux_data") or {}
            button_id = aux.get("button_id")
            try:
                msg_time = int(msg.get("time") or 0)
            except:
                msg_time = 0
        elif "inline_message" in update:
            msg = update["inline_message"]
            chat_id = msg.get("chat_id")
            user_id = msg.get("sender_id")
            text = (msg.get("text") or "").strip()
            message_id = str(msg.get("message_id", ""))
            aux = msg.get("aux_data") or {}
            button_id = aux.get("button_id")
            msg_time = 0
        else:
            return

        if not chat_id or not user_id:
            return

        if msg_time and msg_time > 1000000000:
            age = time.time() - msg_time
            if age > MAX_MESSAGE_AGE:
                return

        update_key = f"{chat_id}|{message_id}|{button_id or text[:80]}"
        if is_processed(update_key):
            return
        mark_processed(update_key)

        name = api.get_name(chat_id) or "باغبان"

        if text.startswith("/"):
            cmd = text.split()[0].lower()
            if cmd == "/start":
                handle_start(chat_id, user_id, name)
                return
            if cmd in ("/profile", "/me"):
                handle_profile(chat_id, user_id)
                return
            if cmd == "/garden":
                handle_garden(chat_id, user_id)
                return
            if cmd == "/shop":
                handle_shop(chat_id, user_id)
                return
            if cmd == "/help":
                handle_help(chat_id, user_id)
                return
            if cmd == "/daily":
                handle_daily(chat_id, user_id)
                return
            if cmd == "/leaderboard":
                handle_leaderboard(chat_id, user_id)
                return
            if cmd == "/admin" and user_id in ADMIN_IDS:
                handle_admin(chat_id, user_id)
                return

        bid = (button_id or text or "").strip()

        if bid in ("main_menu", "بازگشت به منو"):
            api.send_message(chat_id, "منوی اصلی:", chat_keypad=main_kb())
            return

        if bid == "profile":
            handle_profile(chat_id, user_id)
            return
        if bid == "garden":
            handle_garden(chat_id, user_id)
            return
        if bid == "shop":
            handle_shop(chat_id, user_id)
            return
        if bid == "lucky_box":
            handle_lucky(chat_id, user_id)
            return
        if bid == "leaderboard":
            handle_leaderboard(chat_id, user_id)
            return
        if bid == "daily":
            handle_daily(chat_id, user_id)
            return
        if bid == "help":
            handle_help(chat_id, user_id)
            return
        if bid == "weather":
            handle_weather(chat_id, user_id)
            return
        if bid == "pets":
            handle_pets(chat_id, user_id)
            return
        if bid == "quests":
            handle_quests(chat_id, user_id)
            return

        if bid.startswith("adm_") or bid == "admin_panel":
            handle_admin(chat_id, user_id, bid)
            return

        # آب و برداشت همه
        if bid in ("water_all", "💧 آب دادن همه") or "آب دادن همه" in bid:
            count = 0
            for pl in get_plots(user_id):
                if pl["seed_id"] and pl["watered"] < pl["water_needed"]:
                    ok, _ = water_one(user_id, pl["plot_index"])
                    if ok:
                        count += 1
            api.send_message(chat_id, f"💧 {count} گیاه آبیاری شد.", chat_keypad=main_kb())
            return

        if bid in ("harvest_all", "🌾 برداشت همه") or "برداشت همه" in bid:
            msgs = []
            for pl in get_plots(user_id):
                if pl["seed_id"] and pl["finish_at"] and pl["finish_at"] <= time.time():
                    ok, msg = harvest_one(user_id, pl["plot_index"])
                    if ok:
                        msgs.append(msg)
            if msgs:
                api.send_message(chat_id, "\n\n".join(msgs[:6]), chat_keypad=main_kb())
            else:
                api.send_message(chat_id, "هیچ گیاه آماده‌ای برای برداشت وجود ندارد.", chat_keypad=main_kb())
            return

        # فروشگاه
        if bid == "shop_seeds" or bid.startswith("shop_seeds_"):
            page = 0
            if bid.startswith("shop_seeds_"):
                try:
                    page = int(bid.split("_")[-1])
                except:
                    page = 0
            handle_shop_seeds(chat_id, user_id, page)
            return
        if bid.startswith("buy_seed_"):
            handle_buy_seed(chat_id, user_id, bid[9:])
            return
        if bid == "shop_fert":
            handle_shop_fert(chat_id, user_id)
            return
        if bid.startswith("buy_fert_"):
            handle_buy_fert(chat_id, user_id, bid[9:])
            return
        if bid == "shop_soil":
            handle_shop_soil(chat_id, user_id)
            return
        if bid.startswith("buy_soil_"):
            handle_buy_soil(chat_id, user_id, bid[9:])
            return
        if bid == "shop_upgrade":
            handle_shop_upgrade(chat_id, user_id)
            return
        if bid == "do_upgrade":
            handle_do_upgrade(chat_id, user_id)
            return
        if bid == "shop_pets":
            handle_shop_pets(chat_id, user_id)
            return
        if bid.startswith("buy_pet_"):
            handle_buy_pet(chat_id, user_id, bid[8:])
            return

        # کاشت
        if bid.startswith("choose_plant_"):
            try:
                idx = int(bid.split("_")[-1])
                handle_choose_plant(chat_id, user_id, idx)
            except ValueError:
                pass
            return
        if bid.startswith("do_plant_"):
            try:
                parts = bid.split("_")
                idx = int(parts[2])
                sid = "_".join(parts[3:])
                ok, msg = plant(user_id, idx, sid)
                api.send_message(chat_id, msg, chat_keypad=main_kb())
            except (ValueError, IndexError):
                api.send_message(chat_id, "خطا در کاشت.", chat_keypad=main_kb())
            return

        # آب و برداشت تکی (پشتیبانی کامل از متن فارسی)
        if bid.startswith("water_") or "آب زمین" in bid:
            try:
                if bid.startswith("water_"):
                    idx = int(bid.split("_")[-1])
                else:
                    m = re.search(r'(\d+)', bid)
                    if not m:
                        raise ValueError
                    idx = int(m.group(1)) - 1
                ok, msg = water_one(user_id, idx)
                api.send_message(chat_id, msg, chat_keypad=main_kb())
            except (ValueError, IndexError):
                api.send_message(chat_id, "خطا در آبیاری.", chat_keypad=main_kb())
            return

        if bid.startswith("harvest_") or "برداشت زمین" in bid:
            try:
                if bid.startswith("harvest_"):
                    idx = int(bid.split("_")[-1])
                else:
                    m = re.search(r'(\d+)', bid)
                    if not m:
                        raise ValueError
                    idx = int(m.group(1)) - 1
                ok, msg = harvest_one(user_id, idx)
                api.send_message(chat_id, msg, chat_keypad=main_kb())
            except (ValueError, IndexError):
                api.send_message(chat_id, "خطا در برداشت.", chat_keypad=main_kb())
            return

        if button_id or text:
            api.send_message(chat_id, "منوی اصلی:", chat_keypad=main_kb())

    except Exception as e:
        logger.error(f"خطا در پردازش: {e}\n{traceback.format_exc()}")

# ======================== حلقه اصلی ========================
def main():
    init_db()
    logger.info("🌱 ربات Grow Garden شروع شد | ساخته شده توسط @silent_vision")
    try:
        data = api.get_updates(limit=5)
        logger.info(f"اولین دریافت آپدیت انجام شد. offset فعلی: {api.offset_id}")
    except Exception as e:
        logger.warning(f"خطا در دریافت اولیه: {e}")

    while True:
        try:
            data = api.get_updates(limit=35)
            for upd in data.get("updates", []):
                process_update(upd)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("ربات متوقف شد.")
            break
        except Exception as e:
            logger.error(f"خطای حلقه اصلی: {e}")
            time.sleep(4)

if __name__ == "__main__":
    main()
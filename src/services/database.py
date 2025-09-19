# services/database.py

import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

conn = None


# -------------------------
# Инициализация базы данных
# -------------------------
def init_db():
    global conn
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cur = conn.cursor()
    # Создание таблиц
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
        username TEXT,
        telegram_id BIGINT UNIQUE,
        created_at TIMESTAMP DEFAULT NOW(),
        last_active TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS channels (
        channel_id SERIAL PRIMARY KEY,
        user_id INT REFERENCES users(user_id),
        name TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        status TEXT DEFAULT 'active'
    );
    CREATE TABLE IF NOT EXISTS ideas (
        idea_id SERIAL PRIMARY KEY,
        title TEXT UNIQUE
    );
    CREATE TABLE IF NOT EXISTS styles (
        style_id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    );
    CREATE TABLE IF NOT EXISTS posts (
        post_id SERIAL PRIMARY KEY,
        channel_id INT REFERENCES channels(channel_id),
        idea_id INT REFERENCES ideas(idea_id),
        style_id INT REFERENCES styles(style_id),
        text TEXT,
        published_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS logs (
        log_id SERIAL PRIMARY KEY,
        user_id INT REFERENCES users(user_id),
        post_id INT REFERENCES posts(post_id),
        event_type TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)
    conn.commit()
    cur.close()


# -------------------------
# Пользователи
# -------------------------
def add_user(telegram_id, username):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users WHERE telegram_id=%s", (telegram_id,))
    user = cur.fetchone()
    if not user:
        cur.execute(
            "INSERT INTO users (username, telegram_id) VALUES (%s, %s) RETURNING *",
            (username, telegram_id)
        )
        user = cur.fetchone()
        conn.commit()
    cur.close()
    return user


def get_user(telegram_id):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users WHERE telegram_id=%s", (telegram_id,))
    user = cur.fetchone()
    cur.close()
    return user


# -------------------------
# Каналы
# -------------------------
def add_channel(user_id, name):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO channels (user_id, name) VALUES (%s, %s) RETURNING *",
        (user_id, name)
    )
    channel = cur.fetchone()
    conn.commit()
    cur.close()
    return channel


def get_channels(user_id):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM channels WHERE user_id=%s", (user_id,))
    channels = cur.fetchall()
    cur.close()
    return channels


def get_channels_by_name(name):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM channels WHERE name=%s", (name,))
    channels = cur.fetchall()
    cur.close()
    return channels


# -------------------------
# Посты
# -------------------------
def add_post(channel_id: int, idea_title: str, style_name: str, text: str):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --- идея ---
    cur.execute("SELECT idea_id FROM ideas WHERE title=%s", (idea_title,))
    idea = cur.fetchone()
    if not idea:
        cur.execute("INSERT INTO ideas (title) VALUES (%s) RETURNING idea_id", (idea_title,))
        idea = cur.fetchone()

    # --- стиль ---
    cur.execute("SELECT style_id FROM styles WHERE name=%s", (style_name,))
    style = cur.fetchone()
    if not style:
        cur.execute("INSERT INTO styles (name) VALUES (%s) RETURNING style_id", (style_name,))
        style = cur.fetchone()

    # --- пост ---
    cur.execute(
        """
        INSERT INTO posts (channel_id, idea_id, style_id, text)
        VALUES (%s, %s, %s, %s)
        RETURNING *
        """,
        (channel_id, idea["idea_id"], style["style_id"], text)
    )
    post = cur.fetchone()
    conn.commit()
    cur.close()
    return post


def get_last_posts(channel_id: int, limit=10):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT p.text, i.title AS idea, s.name AS style, p.published_at
        FROM posts p
        LEFT JOIN ideas i ON p.idea_id = i.idea_id
        LEFT JOIN styles s ON p.style_id = s.style_id
        WHERE p.channel_id=%s
        ORDER BY p.published_at DESC
        LIMIT %s
    """, (channel_id, limit))
    posts = cur.fetchall()
    cur.close()
    return posts


# -------------------------
# Логи
# -------------------------
def add_log(user_id, post_id, event_type):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (user_id, post_id, event_type) VALUES (%s, %s, %s)",
        (user_id, post_id, event_type)
    )
    conn.commit()
    cur.close()

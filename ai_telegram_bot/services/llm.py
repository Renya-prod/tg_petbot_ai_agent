# services/llm.py

import re
import openai
import aiohttp
import asyncio
from config import OPENAI_API_KEY, PROXY_URL

openai.api_key = OPENAI_API_KEY


# -------------------------
# Асинхронный запрос к OpenAI
# -------------------------
async def ask_openai(prompt: str) -> str:
    """
    Отправка запроса в OpenAI GPT с поддержкой прокси.
    """
    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            proxy=PROXY_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            },
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise ValueError(f"Ошибка OpenAI API: {resp.status}, ответ: {text}")

            data = await resp.json()
            return data["choices"][0]["message"]["content"]


# -------------------------
# Генерация идей + стилей
# -------------------------
async def generate_post_ideas(posts: list[str]) -> list[dict]:
    """
    На основе последних постов генерируем 3 идеи и стили для каждой.
    Формат ответа: [{"idea": "Название", "styles": ["Стиль1", "Стиль2", "Стиль3"]}, ...]
    """
    prompt = (
        "Ты — помощник для создания контента в телеграм-канале.\n"
        "На основе этих постов:\n"
        + "\n".join(posts)
        + "\n\nСгенерируй 3 новые идеи для постов (каждая идея короткая в два-три слова). "
        "Для каждой идеи предложи 3 возможных стиля (в одно-два слова).\n"
        "Отвечай строго в формате:\n"
        "1. <Идея>\n   - <Стиль 1>\n   - <Стиль 2>\n   - <Стиль 3>\n"
        "2. <Идея>\n   - <Стиль 1>\n   - <Стиль 2>\n   - <Стиль 3>\n"
        "3. <Идея>\n   - <Стиль 1>\n   - <Стиль 2>\n   - <Стиль 3>\n"
    )

    resp = await ask_openai(prompt)
    ideas = []

    current = None
    for line in resp.splitlines():
        line = line.strip()
        if not line:
            continue

        if re.match(r"^\d+[\.\)]\s*", line):
            if current:
                ideas.append(current)
            idea_text = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            current = {"idea": idea_text, "styles": []}

        elif re.match(r"^[-•–]\s*", line) and current:
            style_text = re.sub(r"^[-•–]\s*", "", line).strip()
            current["styles"].append(style_text)

    if current:
        ideas.append(current)

    if not ideas:
        ideas = [
            {"idea": "Новая идея 1", "styles": ["Инфо", "Юмор", "Серьёзный"]},
            {"idea": "Новая идея 2", "styles": ["Инфо", "Юмор", "Серьёзный"]},
            {"idea": "Новая идея 3", "styles": ["Инфо", "Юмор", "Серьёзный"]},
        ]

    return ideas[:3]


# -------------------------
# Генерация черновика поста
# -------------------------
async def generate_post_draft(channel_name: str, idea: str, style: str, posts: list[str]) -> str:
    """
    Генерирует черновик поста по выбранной идее и стилю.
    Включает последние посты канала для сохранения тематики.
    """
    recent_posts = "\n".join(posts) if posts else "Нет предыдущих постов."

    prompt = (
        f"Ты пишешь пост для телеграм-канала '{channel_name}'.\n\n"
        f"Последние (прошлые) посты канала:\n{recent_posts}\n\n"
        f"Выбранная тема поста: {idea}\n"
        f"Выбранный стиль поста: {style}\n\n"
        "Создай связный телеграм-пост, "
        "чтобы он соответствовал выбранным теме и стилю, а также сохранял общую тематику прошлых постов."
    )
    draft = await ask_openai(prompt)
    return draft.strip()

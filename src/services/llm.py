# services/llm.py

import requests
import re
import urllib3
from config import GIGACHAT_TOKEN, GIGACHAT_URL

# Подавляем InsecureRequestWarning (если verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# -------------------------
# Основная функция запроса к Gigachat
# -------------------------
def ask_gigachat(prompt: str) -> str:
    """
    Запрос в GigaChat с токеном.
    """
    headers = {"Authorization": f"Bearer {GIGACHAT_TOKEN}"}
    payload = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    resp = requests.post(GIGACHAT_URL, headers=headers, json=payload, verify=False)

    try:
        data = resp.json()
    except Exception as e:
        raise ValueError(f"Ошибка при разборе ответа GigaChat: {e} / Ответ: {resp.text}")

    if "choices" not in data or not data["choices"]:
        raise ValueError(f"Ошибка API GigaChat: отсутствует поле 'choices'. Ответ: {data}")

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
        + "\n\nСгенерируй 3 новые идеи для постов(каждая идея короткая без длинных предложений). Для каждой идеи предложи 3 возможных стиля(в одно-два слова).\n"
        "Отвечай строго в формате:\n"
        "1. <Идея>\n   - <Стиль 1>\n   - <Стиль 2>\n   - <Стиль 3>\n"
        "2. <Идея>\n   - <Стиль 1>\n   - <Стиль 2>\n   - <Стиль 3>\n"
        "3. <Идея>\n   - <Стиль 1>\n   - <Стиль 2>\n   - <Стиль 3>\n"
    )

    resp = ask_gigachat(prompt)
    ideas = []

    current = None
    for line in resp.splitlines():
        line = line.strip()
        if not line:
            continue

        # новая идея
        if re.match(r"^\d+[\.\)]\s*", line):
            if current:
                ideas.append(current)
            idea_text = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            current = {"idea": idea_text, "styles": []}

        # стиль (разные маркеры: -, •, –)
        elif re.match(r"^[-•–]\s*", line) and current:
            style_text = re.sub(r"^[-•–]\s*", "", line).strip()
            current["styles"].append(style_text)

    if current:
        ideas.append(current)

    # fallback если модель вернула не по формату
    if not ideas:
        ideas = [
            {"idea": "Новая идея 1", "styles": ["Инфо", "Юмор", "Серьёзный"]},
            {"idea": "Новая идея 2", "styles": ["Инфо", "Юмор", "Серьёзный"]},
            {"idea": "Новая идея 3", "styles": ["Инфо", "Юмор", "Серьёзный"]},
        ]

    return ideas[:3]  # максимум 3 идеи


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
        f"Последние посты канала:\n{recent_posts}\n\n"
        f"Новая тема поста: {idea}\n"
        f"Стиль поста: {style}\n\n"
        "Создай связный телеграм-пост в 3–5 предложениях, "
        "чтобы он соответствовал теме и стилю, а также сохранял общую тематику прошлых постов."
    )
    draft = ask_gigachat(prompt)
    return draft.strip()

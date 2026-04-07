"""
arqParse Subscription Server
HTTPS сервер на порту 9000 для управления персональными подписками.
"""

import sqlite3
import uuid
import secrets
import os
import logging
from datetime import datetime
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import uvicorn
import bcrypt

# ─── Пути ──────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DB_PATH = os.path.join(DATA_DIR, "subs.db")

CERT_DIR = "/root/cert/ip"
CERT_PATH = os.path.join(CERT_DIR, "fullchain.pem")
KEY_PATH = os.path.join(CERT_DIR, "privkey.pem")
PORT = 9000

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ─── Логирование ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "server.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("arqsubserver")

# ─── БД ────────────────────────────────────────────────────────
def init_db():
    """Создаёт таблицы если не существуют."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                token TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id TEXT PRIMARY KEY REFERENCES users(id),
                content TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mtproto_subs (
                user_id TEXT PRIMARY KEY REFERENCES users(id),
                content TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    logger.info("Database initialized: %s", DB_PATH)


@contextmanager
def get_db():
    """Контекстный менеджер для получения соединения с БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(password: str) -> str:
    """Хеширует пароль через bcrypt (соль генерируется автоматически)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hash_: str) -> bool:
    """Проверяет пароль против bcrypt-хеша."""
    return bcrypt.checkpw(password.encode(), hash_.encode())


# ─── Pydantic модели ───────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateSubRequest(BaseModel):
    content: str


# ─── FastAPI приложение ────────────────────────────────────────
app = FastAPI(title="arqSubServer", docs_url=None, redoc_url=None)


@app.get("/health")
def health_check():
    """Проверка работоспособности сервера."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/api/register")
def register(req: RegisterRequest):
    """Регистрация нового пользователя."""
    username = req.username.strip()
    password = req.password

    # Валидация
    if len(username) < 3 or len(username) > 32:
        raise HTTPException(400, "Имя от 3 до 32 символов")
    if not username.isalnum() and '_' not in username and '-' not in username:
        raise HTTPException(400, "Имя может содержать только буквы, цифры, _ и -")
    if len(password) < 6:
        raise HTTPException(400, "Пароль минимум 6 символов")

    password_hash = hash_password(password)
    user_id = str(uuid.uuid4())
    token = secrets.token_hex(32)

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, salt, token) VALUES (?, ?, ?, '', ?)",
                (user_id, username, password_hash, token),
            )
            conn.execute(
                "INSERT INTO subscriptions (user_id) VALUES (?)",
                (user_id,),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Имя уже занято")

    logger.info("Новый пользователь: %s (id=%s)", username, user_id)
    return {
        "user_id": user_id,
        "token": token,
        "username": username,
        "sub_url": f"https://194.87.54.75:{PORT}/api/sub/{user_id}",
    }


@app.post("/api/login")
def login(req: LoginRequest):
    """Вход в аккаунт."""
    username = req.username.strip()
    password = req.password

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, password_hash, salt, token FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if not row:
        raise HTTPException(401, "Неверное имя пользователя или пароль")

    if not verify_password(password, row["password_hash"]):
        raise HTTPException(401, "Неверное имя пользователя или пароль")

    # Обновляем токен при каждом входе
    new_token = secrets.token_hex(32)
    with get_db() as conn:
        conn.execute("UPDATE users SET token = ? WHERE id = ?", (new_token, row["id"]))

    logger.info("Вход: %s", username)
    return {
        "user_id": row["id"],
        "token": new_token,
        "username": username,
        "sub_url": f"https://194.87.54.75:{PORT}/api/sub/{row['id']}",
    }


@app.get("/api/sub/{user_id}", response_class=PlainTextResponse)
def get_subscription(user_id: str):
    """Получить подписку пользователя (публичный эндпоинт)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT s.content, u.username FROM subscriptions s JOIN users u ON s.user_id = u.id WHERE s.user_id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        raise HTTPException(404, "Подписка не найдена")

    if not row["content"].strip():
        return PlainTextResponse("# Подписка пуста — запустите тест в arqParse\n")

    return PlainTextResponse(row["content"])


@app.post("/api/sub/{user_id}")
def update_subscription(user_id: str, req: UpdateSubRequest, authorization: str = Header(None)):
    """Обновить подписку (требуется токен)."""
    # Проверка токена
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Требуется авторизация")

    token = authorization.replace("Bearer ", "").strip()

    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE id = ? AND token = ?", (user_id, token)
        ).fetchone()

    if not row:
        raise HTTPException(403, "Неверный токен")

    content = req.content
    now = datetime.now().isoformat()

    with get_db() as conn:
        conn.execute(
            "UPDATE subscriptions SET content = ?, updated_at = ? WHERE user_id = ?",
            (content, now, user_id),
        )

    logger.info("Подписка обновлена: user_id=%s (%d байт)", user_id, len(content))
    return {"status": "ok", "updated_at": now}


# ─── MTProto эндпоинты ──────────────────────────────────────

@app.get("/api/mtproto/{user_id}", response_class=PlainTextResponse)
def get_mtproto(user_id: str):
    """Получить MTProto конфиги пользователя (публичный эндпоинт)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT content FROM mtproto_subs WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        raise HTTPException(404, "MTProto подписка не найдена")

    if not row["content"].strip():
        return PlainTextResponse("# MTProto подписка пуста\n")

    return PlainTextResponse(row["content"])


@app.post("/api/mtproto/{user_id}")
def update_mtproto(user_id: str, req: UpdateSubRequest, authorization: str = Header(None)):
    """Обновить MTProto подписку (требуется токен)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Требуется авторизация")

    token = authorization.replace("Bearer ", "").strip()

    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE id = ? AND token = ?", (user_id, token)
        ).fetchone()

    if not row:
        raise HTTPException(403, "Неверный токен")

    # Проверяем что у пользователя уже есть запись в mtproto_subs
    with get_db() as conn:
        existing = conn.execute(
            "SELECT user_id FROM mtproto_subs WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    content = req.content
    now = datetime.now().isoformat()

    with get_db() as conn:
        if existing:
            conn.execute(
                "UPDATE mtproto_subs SET content = ?, updated_at = ? WHERE user_id = ?",
                (content, now, user_id),
            )
        else:
            conn.execute(
                "INSERT INTO mtproto_subs (user_id, content, updated_at) VALUES (?, ?, ?)",
                (user_id, content, now),
            )

    logger.info("MTProto обновлена: user_id=%s (%d байт)", user_id, len(content))
    return {"status": "ok", "updated_at": now}


# ─── Запуск ────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    logger.info("Запуск arqSubServer на https://0.0.0.0:%d", PORT)

    ssl_cert_exists = os.path.exists(CERT_PATH)
    ssl_key_exists = os.path.exists(KEY_PATH)

    if ssl_cert_exists and ssl_key_exists:
        uvicorn.run(
            "server:app",
            host="0.0.0.0",
            port=PORT,
            ssl_certfile=CERT_PATH,
            ssl_keyfile=KEY_PATH,
        )
    else:
        logger.warning("SSL-сертификаты не найдены, запуск без HTTPS")
        uvicorn.run("server:app", host="0.0.0.0", port=PORT)

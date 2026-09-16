import hashlib
import html
import json
import secrets
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "guestboard.json"


# ---------- 데이터 저장/조회 ----------

def load_entries() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_entries(entries: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def next_id(entries: list[dict]) -> int:
    return max((e["id"] for e in entries), default=0) + 1


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------- 템플릿 ----------

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>방명록</title>
<style>
    :root {{
        --green-900: #1b4332;
        --green-700: #2d6a4f;
        --green-600: #40916c;
        --green-500: #52b788;
        --green-300: #95d5b2;
        --green-100: #d8f3dc;
        --bg: #f4fbf6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0;
        font-family: "Segoe UI", "Malgun Gothic", sans-serif;
        background: var(--bg);
        color: #1b3a2a;
    }}
    .hero {{
        background: linear-gradient(135deg, var(--green-700), var(--green-500));
        color: white;
        padding: 48px 20px 36px;
        text-align: center;
    }}
    .hero h1 {{
        margin: 0 0 8px;
        font-size: 2.2em;
    }}
    .hero p {{
        margin: 0;
        opacity: 0.9;
    }}
    .container {{
        max-width: 640px;
        margin: -28px auto 60px;
        padding: 0 16px;
    }}
    .card {{
        background: white;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(27, 67, 50, 0.12);
        padding: 24px;
        margin-bottom: 24px;
    }}
    .form-card h2 {{
        margin-top: 0;
        color: var(--green-900);
        font-size: 1.2em;
    }}
    .form-row {{
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
    }}
    .form-row input {{
        flex: 1;
    }}
    input, textarea {{
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--green-300);
        border-radius: 8px;
        font-size: 1em;
        font-family: inherit;
        background: var(--green-100);
        color: #1b3a2a;
    }}
    input:focus, textarea:focus {{
        outline: none;
        border-color: var(--green-600);
        background: white;
    }}
    textarea {{
        resize: vertical;
        min-height: 90px;
        margin-bottom: 10px;
    }}
    button {{
        background: var(--green-600);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 18px;
        font-size: 1em;
        cursor: pointer;
        transition: background 0.15s ease;
    }}
    button:hover {{
        background: var(--green-700);
    }}
    .submit-btn {{
        width: 100%;
        padding: 12px;
        font-size: 1.05em;
    }}
    .flash {{
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 0.95em;
    }}
    .flash.success {{
        background: var(--green-100);
        color: var(--green-900);
        border: 1px solid var(--green-300);
    }}
    .flash.error {{
        background: #fdecea;
        color: #b3261e;
        border: 1px solid #f3c1bd;
    }}
    .count {{
        color: var(--green-700);
        font-weight: 600;
        margin: 0 4px 16px;
    }}
    .entry {{
        border-left: 4px solid var(--green-500);
        padding: 14px 18px;
        border-radius: 0 12px 12px 0;
        background: var(--green-100);
        margin-bottom: 14px;
    }}
    .entry-head {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 6px;
    }}
    .entry-name {{
        font-weight: 700;
        color: var(--green-900);
    }}
    .entry-date {{
        font-size: 0.8em;
        color: var(--green-700);
        opacity: 0.8;
    }}
    .entry-message {{
        white-space: pre-wrap;
        line-height: 1.5;
        margin-bottom: 10px;
    }}
    .entry-delete {{
        display: flex;
        gap: 8px;
    }}
    .entry-delete input {{
        background: white;
    }}
    .entry-delete button {{
        background: var(--green-500);
        white-space: nowrap;
    }}
    .empty {{
        text-align: center;
        color: var(--green-700);
        opacity: 0.7;
        padding: 24px 0;
    }}
</style>
</head>
<body>
    <div class="hero">
        <h1>🌿 방명록</h1>
        <p>다녀가신 흔적을 남겨주세요</p>
    </div>
    <div class="container">
        {flash}
        <div class="card form-card">
            <h2>글 남기기</h2>
            <form method="post" action="/write">
                <div class="form-row">
                    <input type="text" name="name" placeholder="이름" maxlength="30" required>
                    <input type="password" name="password" placeholder="비밀번호 (삭제 시 필요)" maxlength="50" required>
                </div>
                <textarea name="message" placeholder="방명록에 남길 메시지를 입력하세요" maxlength="1000" required></textarea>
                <button type="submit" class="submit-btn">방명록 남기기</button>
            </form>
        </div>
        <div class="card">
            <p class="count">총 {count}개의 글</p>
            {entries}
        </div>
    </div>
</body>
</html>
"""

ENTRY_TEMPLATE = """
<div class="entry">
    <div class="entry-head">
        <span class="entry-name">{name}</span>
        <span class="entry-date">{created_at}</span>
    </div>
    <div class="entry-message">{message}</div>
    <form class="entry-delete" method="post" action="/delete/{id}">
        <input type="password" name="password" placeholder="비밀번호 입력 후 삭제" required>
        <button type="submit">삭제</button>
    </form>
</div>
"""


def render_entries(entries: list[dict]) -> str:
    if not entries:
        return '<p class="empty">아직 작성된 글이 없습니다. 첫 방문자가 되어보세요!</p>'

    parts = []
    for entry in reversed(entries):
        parts.append(
            ENTRY_TEMPLATE.format(
                id=entry["id"],
                name=html.escape(entry["name"]),
                created_at=entry["created_at"],
                message=html.escape(entry["message"]).replace("\n", "<br>"),
            )
        )
    return "".join(parts)


def render_flash(request: Request) -> str:
    msg = request.query_params.get("msg")
    kind = request.query_params.get("type", "success")
    if not msg:
        return ""
    return f'<div class="flash {html.escape(kind)}">{html.escape(msg)}</div>'


# ---------- 라우트 ----------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    entries = load_entries()
    return PAGE_TEMPLATE.format(
        flash=render_flash(request),
        count=len(entries),
        entries=render_entries(entries),
    )


@app.post("/write")
def write(request: Request, name: str = Form(...), password: str = Form(...), message: str = Form(...)):
    name = name.strip()
    message = message.strip()

    if not name or not password or not message:
        return redirect_with_flash("입력값을 모두 채워주세요.", "error")

    entries = load_entries()
    salt = secrets.token_hex(8)

    entries.append(
        {
            "id": next_id(entries),
            "name": name,
            "password_hash": hash_password(password, salt),
            "password_salt": salt,
            "message": message,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ip": get_client_ip(request),
        }
    )
    save_entries(entries)
    return redirect_with_flash("방명록에 글이 등록되었습니다.", "success")


@app.post("/delete/{entry_id}")
def delete(entry_id: int, password: str = Form(...)):
    entries = load_entries()
    target = next((e for e in entries if e["id"] == entry_id), None)

    if target is None:
        return redirect_with_flash("이미 삭제된 글입니다.", "error")

    if hash_password(password, target["password_salt"]) != target["password_hash"]:
        return redirect_with_flash("비밀번호가 일치하지 않습니다.", "error")

    entries.remove(target)
    save_entries(entries)
    return redirect_with_flash("글이 삭제되었습니다.", "success")


def redirect_with_flash(msg: str, kind: str) -> RedirectResponse:
    query = urlencode({"msg": msg, "type": kind}, quote_via=quote)
    return RedirectResponse(f"/?{query}", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

import random

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="number-game-secret-key")

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>숫자 맞히기 게임</title>
    <style>
        body {{ font-family: sans-serif; max-width: 480px; margin: 60px auto; text-align: center; }}
        input {{ font-size: 1.2em; padding: 6px; width: 100px; text-align: center; }}
        button {{ font-size: 1.2em; padding: 6px 16px; }}
        .message {{ font-size: 1.3em; margin: 20px 0; }}
        .success {{ color: green; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>1~100 숫자 맞히기</h1>
    <p class="message">{message}</p>
    <form method="post" action="/guess">
        <input type="number" name="guess" min="1" max="100" required autofocus>
        <button type="submit">확인</button>
    </form>
    <form method="post" action="/reset">
        <button type="submit">새 게임</button>
    </form>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    message = request.session.pop("last_message", None)

    if "answer" not in request.session:
        request.session["answer"] = random.randint(1, 100)
        request.session["attempts"] = 0

    if message is None:
        message = "1부터 100 사이의 숫자를 맞혀보세요!"

    return PAGE_TEMPLATE.format(message=message)


@app.post("/guess", response_class=HTMLResponse)
def guess(request: Request, guess: int = Form(...)):
    if "answer" not in request.session:
        return RedirectResponse("/", status_code=303)

    request.session["attempts"] += 1
    answer = request.session["answer"]
    attempts = request.session["attempts"]

    if guess < answer:
        message = "더 큰 값입니다."
    elif guess > answer:
        message = "더 작은 값입니다."
    else:
        message = f'<span class="success">정답입니다! {attempts}번 만에 맞히셨습니다. 축하합니다!</span>'
        del request.session["answer"]
        del request.session["attempts"]

    request.session["last_message"] = message
    return RedirectResponse("/", status_code=303)


@app.post("/reset")
def reset(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

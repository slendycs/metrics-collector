from fastapi import FastAPI

app = FastAPI()

@app.get('/healt')
def healh() -> int:
    return 200

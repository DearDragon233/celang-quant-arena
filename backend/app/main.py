from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import models
from .database import engine
from .routers import admin, advisor, analysis, auth, competition, contests, market, news, npc, quant, trade

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="策澜量化竞技场", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=800)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"服务器内部错误: {exc}"})


app.include_router(auth.router)
app.include_router(market.router)
app.include_router(trade.router)
app.include_router(quant.router)
app.include_router(admin.router)
app.include_router(advisor.router)
app.include_router(competition.router)
app.include_router(npc.router)
app.include_router(contests.router)
app.include_router(analysis.router)
app.include_router(contests.admin_router)
app.include_router(news.router)

# 生产模式：托管前端构建产物，未命中路径回退 index.html 支持 SPA 路由
import os


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        if path.replace("\\", "/").lstrip("/").startswith("api/"):
            raise StarletteHTTPException(status_code=404)
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/", SPAStaticFiles(directory=_dist, html=True), name="frontend")

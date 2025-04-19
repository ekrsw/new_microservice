import time
import uuid
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import app_logger, get_request_logger
from app.db.init import Database
from app.db.session import AsyncSessionLocal
from app.crud.user import user
from app.schemas.user import AdminUserCreate, UserSearchParams
from app.messaging.rabbitmq import rabbitmq_client

# ログディレクトリの作成（ファイルログが有効な場合）
if settings.LOG_TO_FILE:
    log_dir = os.path.dirname(settings.LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクルを管理します"""
    # 起動時の処理
    try:
        # データベース初期化
        db = Database()
        await db.init()
        app_logger.info("Database initialized successfully")
        
        # RabbitMQ接続の初期化
        await rabbitmq_client.initialize()
        app_logger.info("RabbitMQ connection initialized")
        
        # RabbitMQの設定情報をログに出力（トラブルシューティング用）
        app_logger.debug(f"RabbitMQ設定: HOST={settings.RABBITMQ_HOST}, "
                         f"EXCHANGE={settings.USER_SYNC_EXCHANGE}, "
                         f"ROUTING_KEY={settings.USER_SYNC_ROUTING_KEY}")
        
        # 初期管理者ユーザーの作成
        try:
            async with AsyncSessionLocal() as db:
                # 管理者ユーザーが存在するか確認
                admin_users = await user.search_users(db, params=UserSearchParams(is_admin=True))
                
                if not admin_users:
                    # 管理者ユーザーが存在しない場合は作成
                    admin_user_data = AdminUserCreate(
                        username="admin",
                        fullname="System Administrator",
                        is_admin=True
                    )
                    
                    # ユーザー作成
                    new_admin = await user.create(db, obj_in=admin_user_data)
                    await db.commit()
                    app_logger.info(f"初期管理者ユーザーを作成しました: ID={new_admin.id}")
                    
                    # RabbitMQにユーザー作成イベントを発行
                    user_data = {
                        "id": str(new_admin.id),
                        "username": new_admin.username,
                        "fullname": new_admin.fullname,
                        "is_admin": new_admin.is_admin,
                        "is_active": new_admin.is_active
                    }
                    
                    event_published = await rabbitmq_client.publish_user_created_event(user_data)
                    if event_published:
                        app_logger.info("初期管理者ユーザー作成イベントを発行しました")
                    else:
                        app_logger.warning("初期管理者ユーザー作成イベントの発行に失敗しました")
                else:
                    app_logger.info("管理者ユーザーが既に存在するため、初期管理者ユーザーの作成をスキップします")
        except Exception as e:
            app_logger.error(f"初期管理者ユーザーの作成中にエラーが発生しました: {e}", exc_info=True)
        
        # RabbitMQメッセージ受信開始（ユーザー作成処理の後に実行）
        try:
            await rabbitmq_client.start_consuming()
            app_logger.info("RabbitMQ message consumption started")
        except Exception as e:
            app_logger.error(f"RabbitMQメッセージ受信開始エラー: {e}", exc_info=True)
        
    except Exception as e:
        app_logger.error(f"Error initializing application: {e}")
        raise
    
    yield  # アプリケーションの実行中
    
    # 終了時の処理
    app_logger.info("Shutting down application")
    await rabbitmq_client.close()


# FastAPIアプリケーションの作成
app = FastAPI(
    title="ユーザー管理サービス",
    description="ユーザープロファイルの管理を行うマイクロサービス",
    version="1.0.0",
    lifespan=lifespan
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンのみを許可するように変更する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエストIDとロギングミドルウェア
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    # リクエストIDの生成と設定
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # リクエストロガーの取得
    logger = get_request_logger(request)

    # リクエスト情報のロギング
    logger.info(
        f"Request started: {request.method} {request.url.path} "
        f"(Client: {request.client.host if request.client else 'unknown'})"
    )
    
    # 処理時間の計測
    start_time = time.time()
    
    try:
        # リクエスト処理
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # レスポンスヘッダーの設定
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # レスポンス情報のロギング
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Process time: {process_time:.3f}s"
        )
        
        return response
    except Exception as e:
        # 例外発生時のロギング
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} "
            f"Error: {str(e)} "
            f"Process time: {process_time:.3f}s",
            exc_info=True
        )
        raise

# バリデーションエラーハンドラー
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # リクエストロガーの取得
    logger = get_request_logger(request)
    
    # エラー情報の処理（ValueErrorオブジェクトを文字列に変換）
    errors = []
    for error in exc.errors():
        # エラーのコピーを作成
        processed_error = error.copy()
        # ctx内のValueErrorオブジェクトを文字列に変換
        if 'ctx' in processed_error and 'error' in processed_error['ctx']:
            if isinstance(processed_error['ctx']['error'], ValueError):
                processed_error['ctx']['error'] = str(processed_error['ctx']['error'])
        errors.append(processed_error)
    
    # バリデーションエラーのロギング
    logger.warning(
        f"Validation error: {request.method} {request.url.path} "
        f"Errors: {errors}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors, "body": exc.body},
    )

# APIルーターの登録
app.include_router(api_router, prefix="/api/v1")

# ルートエンドポイント
@app.get("/")
async def root():
    return {
        "message": "ユーザー管理サービスAPI",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    
    # アプリケーション起動時のログ
    app_logger.info(
        f"Starting user-service in {settings.ENVIRONMENT} mode "
        f"(Log level: {settings.LOG_LEVEL})"
    )
    
    uvicorn.run(app, host="0.0.0.0", port=8081)

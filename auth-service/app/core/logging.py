import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
from fastapi import Request

from app.core.config import settings


class RequestIdFilter(logging.Filter):
    """リクエストIDをログに追加するフィルター"""
    
    def filter(self, record):
        record.request_id = getattr(record, "request_id", "no-request-id")
        return True


class CustomJsonFormatter(logging.Formatter):
    """JSON形式でログを出力するフォーマッター"""
    
    def format(self, record):
        log_record: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": getattr(record, "request_id", "no-request-id"),
        }
        
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得する
    
    Args:
        name: ロガー名（通常はモジュール名）
    
    Returns:
        設定済みのロガーインスタンス
    """
    logger = logging.getLogger(name)
    
    # 既に設定済みの場合は再設定しない
    if logger.handlers:
        return logger
    
    # ログレベルの設定
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # リクエストIDフィルターの追加
    request_id_filter = RequestIdFilter()
    logger.addFilter(request_id_filter)
    
    # コンソールハンドラーの設定
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # 開発環境ではシンプルなフォーマット、本番環境ではJSON形式
    if settings.ENVIRONMENT == "development":
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(request_id)s] %(message)s"
        )
    else:
        formatter = CustomJsonFormatter()
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルへのログ出力が有効な場合
    if settings.LOG_TO_FILE:
        file_handler = RotatingFileHandler(
            settings.LOG_FILE_PATH,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_request_logger(request: Request) -> logging.LoggerAdapter:
    """
    リクエスト情報を含むロガーアダプターを取得する
    
    Args:
        request: FastAPIのリクエストオブジェクト
    
    Returns:
        リクエスト情報を含むロガーアダプター
    """
    logger = get_logger("app.api")

    # 親ロガーへの伝播を無効化する
    logger.propagate = False

    # リクエストIDの取得
    request_id = getattr(request.state, "request_id", "no-request-id")
    
    # ロガーアダプターを使用してリクエストIDを追加
    extra = {"request_id": request_id}
    
    return logging.LoggerAdapter(logger, extra)


# アプリケーション全体で使用するロガー
app_logger = get_logger("app")

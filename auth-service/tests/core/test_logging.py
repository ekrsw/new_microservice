import pytest
import logging
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from fastapi import Request

from app.core.logging import (
    RequestIdFilter,
    CustomJsonFormatter,
    get_logger,
    get_request_logger,
    app_logger
)


class TestLogging:
    def test_request_id_filter(self):
        """RequestIdFilterのテスト"""
        # フィルターの作成
        filter_instance = RequestIdFilter()
        
        # ログレコードのモック
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="テストメッセージ",
            args=(),
            exc_info=None
        )
        
        # フィルター適用
        result = filter_instance.filter(record)
        
        # 検証
        assert result is True
        assert hasattr(record, "request_id")
        assert record.request_id == "no-request-id"
        
        # 既にrequest_idが設定されている場合
        record.request_id = "test-request-id"
        filter_instance.filter(record)
        assert record.request_id == "test-request-id"  # 変更されないことを確認
    
    def test_custom_json_formatter(self):
        """CustomJsonFormatterのテスト"""
        # フォーマッターの作成
        formatter = CustomJsonFormatter()
        
        # ログレコードのモック
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_logging.py",
            lineno=123,
            msg="テストメッセージ",
            args=(),
            exc_info=None
        )
        record.request_id = "test-request-id"
        
        # フォーマット適用
        formatted = formatter.format(record)
        
        # JSON形式であることを確認
        log_dict = json.loads(formatted)
        
        # 検証
        assert log_dict["level"] == "INFO"
        assert log_dict["message"] == "テストメッセージ"
        assert log_dict["module"] == "test_logging"  # このファイル名になる
        assert log_dict["line"] == 123
        assert log_dict["request_id"] == "test-request-id"
        assert "timestamp" in log_dict
        
        # user_idが含まれる場合
        record.user_id = "test-user-id"
        formatted = formatter.format(record)
        log_dict = json.loads(formatted)
        assert log_dict["user_id"] == "test-user-id"
        
        # 例外情報が含まれる場合
        try:
            raise ValueError("テスト例外")
        except ValueError:
            record.exc_info = logging.sys.exc_info()
            formatted = formatter.format(record)
            log_dict = json.loads(formatted)
            assert "exception" in log_dict
            assert "ValueError: テスト例外" in log_dict["exception"]
    
    def test_get_logger(self):
        """get_logger関数のテスト"""
        # 環境設定のモック
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.ENVIRONMENT = "development"
            mock_settings.LOG_TO_FILE = False
            
            # ロガー取得
            logger = get_logger("test_logger")
            
            # 検証
            assert logger.name == "test_logger"
            assert logger.level == logging.INFO
            
            # ハンドラーが追加されていることを確認
            assert len(logger.handlers) > 0
            assert isinstance(logger.handlers[0], logging.StreamHandler)
            
            # フィルターが追加されていることを確認
            filters = logger.filters
            assert any(isinstance(f, RequestIdFilter) for f in filters)
            
            # 本番環境設定でのテスト
            mock_settings.ENVIRONMENT = "production"
            logger = get_logger("test_logger_prod")
            
            # JSONフォーマッターが使用されていることを確認
            assert isinstance(logger.handlers[0].formatter, CustomJsonFormatter)
            
            # ファイルログが有効な場合
            mock_settings.LOG_TO_FILE = True
            mock_settings.LOG_FILE_PATH = "test.log"
            
            with patch("app.core.logging.RotatingFileHandler") as mock_file_handler:
                mock_file_handler.return_value = logging.FileHandler("test.log")
                logger = get_logger("test_logger_file")
                
                # ファイルハンドラーが追加されていることを確認
                handlers = logger.handlers
                assert any(isinstance(h, logging.FileHandler) for h in handlers)
    
    def test_get_request_logger(self):
        """get_request_logger関数のテスト"""
        # リクエストのモック
        mock_request = MagicMock(spec=Request)
        mock_request.state.request_id = "test-request-id"
        
        # ロガーのモック
        with patch("app.core.logging.get_logger") as mock_get_logger:
            mock_logger = logging.getLogger("mock_logger")
            mock_get_logger.return_value = mock_logger
            
            # リクエストロガーの取得
            logger_adapter = get_request_logger(mock_request)
            
            # 検証
            assert isinstance(logger_adapter, logging.LoggerAdapter)
            assert logger_adapter.extra["request_id"] == "test-request-id"
            
            # リクエストIDがない場合
            mock_request = MagicMock(spec=Request)
            mock_request.state = MagicMock()
            delattr(mock_request.state, "request_id")
            
            logger_adapter = get_request_logger(mock_request)
            assert logger_adapter.extra["request_id"] == "no-request-id"
    
    def test_app_logger(self):
        """app_loggerの検証"""
        # app_loggerがLoggerインスタンスであることを確認
        assert isinstance(app_logger, logging.Logger)
        assert app_logger.name == "app"

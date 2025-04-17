import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType

from app.core.config import settings
from app.core.logging import app_logger


class RabbitMQClient:
    """RabbitMQのクライアントクラス"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.logger = app_logger
        self.is_initialized = False
    
    async def initialize(self):
        """RabbitMQへの接続を初期化"""
        if self.is_initialized:
            return
        
        try:
            # RabbitMQ接続文字列の構築
            rabbitmq_url = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/{settings.RABBITMQ_VHOST}"
            
            # 接続の確立
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            
            # チャネルの開設
            self.channel = await self.connection.channel()
            
            # exchangeの宣言
            self.exchange = await self.channel.declare_exchange(
                settings.USER_SYNC_EXCHANGE,
                ExchangeType.TOPIC,
                durable=True
            )
            
            self.is_initialized = True
            self.logger.info("RabbitMQ接続が確立されました")
        except Exception as e:
            self.logger.error(f"RabbitMQ接続エラー: {str(e)}", exc_info=True)
            raise
    
    async def close(self):
        """接続のクローズ"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            self.is_initialized = False
            self.logger.info("RabbitMQ接続がクローズされました")
    
    async def publish_user_event(self, event_type: str, user_data: Dict[str, Any]):
        """ユーザーイベントの発行"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # メッセージのJSONシリアライズ
            message_body = {
                "event_type": event_type,
                "user_data": self._serialize_user_data(user_data)
            }
            
            # メッセージの発行
            await self.exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message_body).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=settings.USER_SYNC_ROUTING_KEY
            )
            
            self.logger.info(f"ユーザーイベントを発行しました: {event_type}, ユーザーID={user_data.get('id', 'unknown')}")
        except Exception as e:
            self.logger.error(f"メッセージ発行エラー: {str(e)}", exc_info=True)
            # エラーはログに記録するが例外は再送出しない
            # メッセージングがサービスの主要機能を妨げるべきではない
    
    def _serialize_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """ユーザーデータのシリアライズ"""
        serialized = {}
        for key, value in user_data.items():
            if isinstance(value, UUID):
                serialized[key] = str(value)
            else:
                serialized[key] = value
        return serialized


# シングルトンインスタンス
rabbitmq_client = RabbitMQClient()


# ユーザーイベントタイプの定義
class UserEventTypes:
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    PASSWORD_CHANGED = "user.password_changed"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"


# ヘルパー関数
async def publish_user_created(user_data: Dict[str, Any]):
    """ユーザー作成イベントの発行"""
    await rabbitmq_client.publish_user_event(UserEventTypes.USER_CREATED, user_data)


async def publish_user_updated(user_data: Dict[str, Any]):
    """ユーザー更新イベントの発行"""
    await rabbitmq_client.publish_user_event(UserEventTypes.USER_UPDATED, user_data)


async def publish_user_deleted(user_data: Dict[str, Any]):
    """ユーザー削除イベントの発行"""
    await rabbitmq_client.publish_user_event(UserEventTypes.USER_DELETED, user_data)


async def publish_password_changed(user_data: Dict[str, Any]):
    """パスワード変更イベントの発行"""
    await rabbitmq_client.publish_user_event(UserEventTypes.PASSWORD_CHANGED, user_data)


async def publish_user_status_changed(user_data: Dict[str, Any], is_active: bool):
    """ユーザーステータス変更イベントの発行"""
    event_type = UserEventTypes.USER_ACTIVATED if is_active else UserEventTypes.USER_DEACTIVATED
    await rabbitmq_client.publish_user_event(event_type, user_data)

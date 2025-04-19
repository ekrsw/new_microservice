import json
import logging
from typing import Dict, Any, Optional, Callable
from uuid import UUID

import aio_pika
import uuid
from aio_pika import ExchangeType, IncomingMessage

from app.core.config import settings
from app.core.logging import app_logger
from app.crud.user import user
from app.db.session import AsyncSessionLocal

class RabbitMQClient:
    """RabbitMQのクライアントクラス"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.queue = None
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
            
            # キューの宣言
            self.queue = await self.channel.declare_queue(
                settings.USER_SYNC_QUEUE,
                durable=True
            )
            
            # キューをexchangeにバインド
            await self.queue.bind(
                self.exchange,
                routing_key=settings.USER_SYNC_ROUTING_KEY
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
    
    async def start_consuming(self):
        """メッセージの受信を開始"""
        if not self.is_initialized:
            await self.initialize()
        
        # メッセージハンドラの設定
        await self.queue.consume(self._process_message)
        self.logger.info(f"キュー '{settings.USER_SYNC_QUEUE}' からのメッセージ受信を開始しました")
    
    async def _process_message(self, message: IncomingMessage):
        """
        受信したメッセージを処理する
        """
        async with message.process():
            try:
                # メッセージのデコード
                message_body = json.loads(message.body.decode())
                event_type = message_body.get("event_type")
                user_data = message_body.get("user_data", {})
                
                self.logger.info(f"メッセージを受信しました: {event_type}")
                
                # イベントタイプに応じた処理
                if event_type == "user.created":
                    await self._handle_user_created(user_data)
                elif event_type == "user.updated":
                    await self._handle_user_updated(user_data)
                elif event_type == "user.deleted":
                    await self._handle_user_deleted(user_data)
                else:
                    self.logger.warning(f"未知のイベントタイプ: {event_type}")
            except json.JSONDecodeError:
                self.logger.error("JSONデコードエラー", exc_info=True)
            except Exception as e:
                self.logger.error(f"メッセージ処理エラー: {str(e)}", exc_info=True)
    
    async def _handle_user_created(self, user_data: Dict[str, Any]):
        """ユーザー作成イベントの処理"""
        try:
            # 必要なデータの取得
            user_id = UUID(user_data.get("id"))
            username = user_data.get("username")
            is_admin = user_data.get("is_admin", False)
            is_active = user_data.get("is_active", True)
            
            self.logger.info(f"ユーザー作成イベント処理: ID={user_id}, ユーザー名={username}")
            
            # データベースセッションの作成
            async with AsyncSessionLocal() as db:
                # ユーザーの同期
                synced_user = await user.sync_user(
                    db=db,
                    user_id=user_id,
                    username=username,
                    is_admin=is_admin,
                    is_active=is_active
                )
                await db.commit()
                
                self.logger.info(f"ユーザー同期成功: ID={synced_user.id}, ユーザー名={username}")
        except Exception as e:
            self.logger.error(f"ユーザー作成イベント処理エラー: {str(e)}", exc_info=True)
    
    async def _handle_user_updated(self, user_data: Dict[str, Any]):
        """ユーザー更新イベントの処理"""
        try:
            # 必要なデータの取得
            user_id = UUID(user_data.get("id"))
            username = user_data.get("username")
            is_admin = user_data.get("is_admin", False)
            is_active = user_data.get("is_active", True)
            
            self.logger.info(f"ユーザー更新イベント処理: ID={user_id}, ユーザー名={username}")
            
            # データベースセッションの作成
            async with AsyncSessionLocal() as db:
                # ユーザーの同期
                synced_user = await user.sync_user(
                    db=db,
                    user_id=user_id,
                    username=username,
                    is_admin=is_admin,
                    is_active=is_active
                )
                await db.commit()
                
                self.logger.info(f"ユーザー同期成功: ID={synced_user.id}, フルネーム={synced_user.fullname}")
        except Exception as e:
            self.logger.error(f"ユーザー更新イベント処理エラー: {str(e)}", exc_info=True)
    
    async def _handle_user_deleted(self, user_data: Dict[str, Any]):
        """ユーザー削除イベントの処理"""
        try:
            # 必要なデータの取得
            user_id = UUID(user_data.get("id"))
            
            self.logger.info(f"ユーザー削除イベント処理: ID={user_id}")
            
            # データベースセッションの作成
            async with AsyncSessionLocal() as db:
                # ユーザーの取得
                db_user = await user.get_by_user_id(db, user_id)
                if db_user:
                    # ユーザーの削除
                    await user.delete(db, db_user)
                    await db.commit()
                    self.logger.info(f"ユーザー削除成功: ID={user_id}")
                else:
                    self.logger.warning(f"ユーザー削除失敗: ユーザーID '{user_id}' が存在しません")
        except Exception as e:
            self.logger.error(f"ユーザー削除イベント処理エラー: {str(e)}", exc_info=True)
            
    async def publish_user_created_event(self, user_data: Dict[str, Any]):
        """ユーザー作成イベントを発行する"""
        self.logger.debug(f"ユーザー作成イベント発行開始: {user_data}")
        
        if not self.is_initialized:
            self.logger.debug("RabbitMQクライアントが初期化されていないため初期化します")
            await self.initialize()
            
        try:
            message_body = {
                "event_type": "user.created",
                "user_data": user_data
            }
            
            # メッセージIDの生成
            message_id = str(uuid.uuid4())
            
            # ログにメッセージ内容を出力
            self.logger.debug(f"送信メッセージ: {json.dumps(message_body)}")
            self.logger.debug(f"ルーティングキー: {settings.USER_SYNC_ROUTING_KEY}")
            
            # メッセージの作成と送信
            message = aio_pika.Message(
                body=json.dumps(message_body).encode(),
                content_type="application/json",
                message_id=message_id,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            
            # メッセージの送信
            await self.exchange.publish(
                message,
                routing_key=settings.USER_SYNC_ROUTING_KEY
            )
            
            self.logger.info(f"ユーザー作成イベントを発行しました: user_id={user_data.get('id')}, message_id={message_id}")
            return True
        except Exception as e:
            self.logger.error(f"ユーザー作成イベント発行エラー: {str(e)}", exc_info=True)
            # 詳細なエラー情報を提供
            if self.exchange is None:
                self.logger.error("エラー詳細: exchangeがNoneです")
            elif self.connection is None or self.connection.is_closed:
                self.logger.error("エラー詳細: RabbitMQ接続が閉じられているか存在しません")
            return False


# シングルトンインスタンス
rabbitmq_client = RabbitMQClient()

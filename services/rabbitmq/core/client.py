import asyncio
import contextlib
import json
import logging
import uuid
from typing import Any, Dict, Optional

import aio_pika

from .config import Settings

logger = logging.getLogger(__name__)


class RabbitMQClient:
    def __init__(self, settings: Settings = Settings()):
        logger.info("RabbitMQClient instance created")
        self.settings = settings or Settings()
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self.futures: Dict[str, asyncio.Future] = {}
        self.connection_url = (
            self.settings.RABBITMQ_URL
            if self.settings.RABBITMQ_URL
            else f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASSWORD}@{self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT}/{self.settings.RABBITMQ_VHOST}"
        )

    async def connect(self):
        logger.info(
            f"[RabbitMQClient] connect() called. Callback queue: {getattr(self.callback_queue, 'name', None)}"
        )
        try:
            # Close existing connection if any
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                
            self.connection = await aio_pika.connect_robust(
                self.connection_url,
                # Add reconnect settings
                reconnect_interval=1.0,
                fail_fast=False,
            )
            self.channel = await self.connection.channel()
            
            # Set prefetch to avoid message buildup
            await self.channel.set_qos(prefetch_count=10)
            
            self.callback_queue = await self.channel.declare_queue(
                name="",  # Empty name means server will generate a unique name
                exclusive=True,
                auto_delete=True,
                arguments={
                    "x-expires": 60000,  # Queue expires after 60 seconds of no use
                }
            )
            logger.info(
                f"[RabbitMQClient] Callback queue declared: {self.callback_queue.name}"
            )
            await self.callback_queue.consume(self._on_response)
            logger.info(
                f"[RabbitMQClient] Consumer started on callback queue: {self.callback_queue.name}"
            )
            return True
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {str(e)}")
            return False

    async def _on_response(self, message: aio_pika.IncomingMessage):
        logger.info(
            f"[RabbitMQClient] _on_response: correlation_id={message.correlation_id}, reply_to={message.reply_to}"
        )
        async with message.process():
            if message.correlation_id is None:
                logger.warning("[RabbitMQClient] Received message with no correlation_id")
                return
            
            # Log all pending futures for debugging
            logger.info(f"[RabbitMQClient] Current futures when receiving {message.correlation_id}: {list(self.futures.keys())}")
            
            future = self.futures.pop(message.correlation_id, None)
            if future is not None and not future.done():
                try:
                    response_data = json.loads(message.body.decode())
                    future.set_result(response_data)
                    logger.info(
                        f"[RabbitMQClient] Future resolved and removed: {message.correlation_id}"
                    )
                except Exception as e:
                    logger.error(f"[RabbitMQClient] Error processing response: {e}")
                    future.set_exception(e)
            else:
                if future and future.done():
                    logger.info(
                        f"[RabbitMQClient] Future already done for correlation_id: {message.correlation_id}"
                    )
                else:
                    logger.warning(
                        f"[RabbitMQClient] No future found for correlation_id: {message.correlation_id} "
                        f"(likely cancelled due to disconnect)"
                    )

    async def publish_and_wait(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any],
        correlation_id: Optional[str] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        # Ensure connection and callback queue are ready
        if not self.is_connected():
            logger.info("[RabbitMQClient] Not connected, reconnecting...")
            connected = await self.connect()
            if not connected:
                raise Exception("Failed to connect to RabbitMQ")
        
        # Double-check callback queue exists and is active
        if not self.callback_queue or self.callback_queue.channel.is_closed:
            logger.warning("[RabbitMQClient] Callback queue not ready, reconnecting...")
            await self.connect()
            
        if not self.callback_queue:
            raise Exception("No callback queue available after reconnection")
            
        correlation_id = correlation_id or str(uuid.uuid4())
        future = asyncio.Future()
        self.futures[correlation_id] = future
        
        logger.info(
            f"[RabbitMQClient] publish_and_wait: callback queue: {self.callback_queue.name}, correlation_id: {correlation_id}"
        )
        logger.info(
            f"[RabbitMQClient] Futures state before publish: {list(self.futures.keys())}"
        )
        
        message_body = aio_pika.Message(
            body=json.dumps(message).encode(),
            correlation_id=correlation_id,
            reply_to=self.callback_queue.name,  # Use the persistent callback queue
        )
        
        if exchange:
            logger.info(
                f"[RabbitMQClient] Publishing message to exchange: {exchange}"
            )
            exchange_obj = await self.channel.get_exchange(
                exchange, ensure=False
            )
            await exchange_obj.publish(message_body, routing_key=routing_key)
        else:
            logger.info(
                "[RabbitMQClient] Publishing message to default exchange"
            )
            await self.channel.default_exchange.publish(
                message_body, routing_key=routing_key
            )
        
        logger.info("[RabbitMQClient] Message published, waiting for response")
        
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.error(
                f"[RabbitMQClient] Request timed out after {timeout} seconds. "
                f"Correlation ID: {correlation_id}, Callback queue: {self.callback_queue.name}"
            )
            # Clean up any stale futures older than timeout
            self._cleanup_stale_futures(timeout)
            raise TimeoutError(f"Request timed out after {timeout} seconds")
        finally:
            self.futures.pop(correlation_id, None)
            logger.info(
                f"[RabbitMQClient] Futures state after cleanup: {list(self.futures.keys())}"
            )

    async def close(self):
        logger.info("[RabbitMQClient] close() called")
        if self.connection:
            await self.connection.close()
            logger.info("[RabbitMQClient] connection closed")
            self.connection = None
            self.channel = None
            self.callback_queue = None
            self.futures.clear()

    def is_connected(self):
        """Check if connected to RabbitMQ"""
        return self.connection is not None and not self.connection.is_closed
    
    def _cleanup_stale_futures(self, max_age_seconds: float):
        """Clean up futures that have been waiting too long"""
        stale_count = 0
        for correlation_id in list(self.futures.keys()):
            future = self.futures.get(correlation_id)
            if future and not future.done():
                # Cancel and remove stale futures
                future.cancel()
                self.futures.pop(correlation_id, None)
                stale_count += 1
        if stale_count > 0:
            logger.warning(f"[RabbitMQClient] Cleaned up {stale_count} stale futures")

    async def publish_message(
        self,
        exchange: str,
        routing_key: str,
        message: str,
        correlation_id: str = None,
        reply_to: str = None,
    ):
        logger.info(
            f"[RabbitMQClient] publish_message: exchange={exchange}, routing_key={routing_key}, correlation_id={correlation_id}, reply_to={reply_to}, message={message}"
        )
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Create a message with the string body and optional properties
        message_kwargs = {"body": message.encode("utf-8")}
        if correlation_id is not None:
            message_kwargs["correlation_id"] = correlation_id
        if reply_to is not None:
            message_kwargs["reply_to"] = reply_to
        message_body = aio_pika.Message(**message_kwargs)

        # Publish the message
        if exchange:
            # Get the exchange by name or declare it if it doesn't exist
            try:
                exchange_obj = await self.channel.get_exchange(
                    exchange, ensure=False
                )
            except Exception:
                # Exchange doesn't exist, this shouldn't happen but let's handle it
                logger.warning(
                    f"Exchange {exchange} not found, using default exchange"
                )
                exchange_obj = self.channel.default_exchange
            # Publish to the named exchange
            await exchange_obj.publish(message_body, routing_key=routing_key)
            logger.debug(
                f"Published message to exchange {exchange} with routing key {routing_key}"
            )
        else:
            # Use default exchange if no exchange name is provided
            await self.channel.default_exchange.publish(
                message_body, routing_key=routing_key
            )
            logger.debug(
                f"Published message to default exchange with routing key {routing_key}"
            )

    async def declare_queue(self, queue_name: str, durable: bool = True):
        """Declare a queue"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Declare the queue using aio_pika
        await self.channel.declare_queue(name=queue_name, durable=durable)

    async def declare_exchange(
        self, exchange_name: str, exchange_type: str = "direct"
    ):
        """Declare an exchange"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Map exchange type strings to aio_pika ExchangeType enum
        exchange_type_map = {
            "direct": aio_pika.ExchangeType.DIRECT,
            "fanout": aio_pika.ExchangeType.FANOUT,
            "topic": aio_pika.ExchangeType.TOPIC,
            "headers": aio_pika.ExchangeType.HEADERS,
        }

        # Get the exchange type or default to DIRECT
        exchange_type_enum = exchange_type_map.get(
            exchange_type.lower(), aio_pika.ExchangeType.DIRECT
        )

        # Declare the exchange
        await self.channel.declare_exchange(
            name=exchange_name, type=exchange_type_enum, durable=True
        )

    async def bind_queue(
        self, queue_name: str, exchange_name: str, routing_key: str
    ):
        """Bind a queue to an exchange with a routing key"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Get the queue - declare it if it doesn't exist
        try:
            queue = await self.channel.get_queue(queue_name, ensure=False)
        except Exception:
            # Queue doesn't exist, declare it
            queue = await self.channel.declare_queue(
                name=queue_name, durable=True
            )

        # Get the exchange
        exchange = await self.channel.get_exchange(exchange_name, ensure=False)

        # Bind the queue to the exchange with the routing key
        await queue.bind(exchange=exchange, routing_key=routing_key)
        logger.info(
            f"Bound queue {queue_name} to exchange {exchange_name} with routing key {routing_key}"
        )

    async def consume(self, queue_name: str, callback):
        """Start consuming messages from a queue"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Get the queue
        queue = await self.channel.get_queue(queue_name)

        # Start consuming
        await queue.consume(callback)

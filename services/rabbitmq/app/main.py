from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ..core.config import Settings
from ..core.client import RabbitMQClient

app = FastAPI(title="RabbitMQ Service")
settings = Settings()
rabbitmq_client = RabbitMQClient(settings=settings)


class MessageRequest(BaseModel):
    exchange: str
    routing_key: str
    message: str


class QueueRequest(BaseModel):
    queue_name: str
    durable: bool = True


class ExchangeRequest(BaseModel):
    exchange_name: str
    exchange_type: str = 'direct'


@app.on_event("startup")
async def startup_event():
    await rabbitmq_client.connect()


@app.on_event("shutdown")
async def shutdown_event():
    await rabbitmq_client.close()


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "rabbitmq_connected": rabbitmq_client.is_connected()
    }


@app.post("/publish")
async def publish_message(message_request: MessageRequest):
    try:
        await rabbitmq_client.publish_message(
            message_request.exchange,
            message_request.routing_key,
            message_request.message
        )
        return {
            "status": "success",
            "message": "Message published successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/queues")
async def create_queue(queue_request: QueueRequest):
    try:
        await rabbitmq_client.declare_queue(
            queue_request.queue_name,
            queue_request.durable
        )
        return {
            "status": "success",
            "message": (
                f"Queue {queue_request.queue_name} declared successfully"
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/exchanges")
async def create_exchange(exchange_request: ExchangeRequest):
    try:
        await rabbitmq_client.declare_exchange(
            exchange_request.exchange_name,
            exchange_request.exchange_type
        )
        return {
            "status": "success",
            "message": (
                f"Exchange {exchange_request.exchange_name} declared successfully"
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""WebSocket endpoint streaming task progress."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from ..task_hub import hub

router = APIRouter()


@router.websocket("/ws/tasks/{task_id}")
async def task_stream(ws: WebSocket, task_id: str):
    await ws.accept()
    try:
        async for msg in hub.subscribe(task_id):
            await ws.send_json(msg)
    except WebSocketDisconnect:
        logger.info(f"WS client disconnected: {task_id}")
    except Exception as e:
        logger.exception(f"WS error for task {task_id}")
        await ws.send_json({"error": str(e)})
    finally:
        try:
            await ws.close()
        except Exception:
            pass

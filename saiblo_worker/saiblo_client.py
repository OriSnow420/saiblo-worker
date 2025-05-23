"""The implementation of the Saiblo client."""

import asyncio
import json
import logging

import websockets.asyncio.client
from websockets import ClientConnection, ConnectionClosed

from saiblo_worker.base_saiblo_client import BaseSaibloClient
from saiblo_worker.base_task_scheduler import BaseTaskScheduler
from saiblo_worker.build_task import BuildTaskFactory
from saiblo_worker.judge_task import JudgeTask, JudgeTaskFactory

_CHECK_TASK_SCHEDULER_IDLE_INTERVAL = 1
_SEND_HEART_BEAT_INTERVAL = 3


class SaibloClient(BaseSaibloClient):
    """The Saiblo client."""

    _build_task_factory: BuildTaskFactory
    _judge_task_factory: JudgeTaskFactory
    _name: str
    _request_judge_task_condition: asyncio.Condition = asyncio.Condition()
    _task_scheduler: BaseTaskScheduler
    _websocket_url: str

    def __init__(
        self,
        name: str,
        websocket_url: str,
        task_scheduler: BaseTaskScheduler,
        build_task_factory: BuildTaskFactory,
        judge_task_factory: JudgeTaskFactory,
    ):
        self._name = name
        self._websocket_url = websocket_url
        self._task_scheduler = task_scheduler
        self._build_task_factory = build_task_factory
        self._judge_task_factory = judge_task_factory

    async def start(self) -> None:
        async for connection in websockets.asyncio.client.connect(self._websocket_url):
            try:
                logging.info("Connected to %s as %s", self._websocket_url, self._name)

                await connection.send(
                    json.dumps(
                        {
                            "type": "init",
                            "data": {
                                "description": self._name,
                                "address": "",
                            },
                        }
                    )
                )

                await asyncio.gather(
                    self._keep_finish_judge_task(connection),
                    self._keep_heart_beat(connection),
                    self._keep_receive_message(connection),
                    self._keep_request_judge_task(connection),
                )

            except ConnectionClosed as e:
                logging.error("Connection closed: %s", e)
                logging.debug("Reconnecting to %s", self._websocket_url)
                continue

    async def _keep_finish_judge_task(self, connection: ClientConnection) -> None:
        while True:
            done_task = await self._task_scheduler.pop_done_task()

            if isinstance(done_task, JudgeTask):
                await connection.send(
                    json.dumps(
                        {
                            "type": "finish_judge_task",
                            "data": {
                                "match_id": int(done_task.match_id),
                            },
                        }
                    )
                )

    async def _keep_heart_beat(self, connection: ClientConnection) -> None:
        while True:
            await connection.send(
                json.dumps(
                    {
                        "type": "heart_beat",
                    }
                )
            )

            await asyncio.sleep(_SEND_HEART_BEAT_INTERVAL)

    async def _keep_receive_message(self, connection: ClientConnection) -> None:
        while True:
            message = json.loads(await connection.recv())

            match message["type"]:
                case "compilation_task":
                    task = self._build_task_factory.create(message["data"]["code_id"])

                    await self._task_scheduler.schedule(task)

                case "judge_task":
                    task = self._judge_task_factory.create(
                        str(message["data"]["match_id"]),
                        [x["code_id"] for x in message["data"]["players"]],
                    )

                    await self._task_scheduler.schedule(task)

                    async with self._request_judge_task_condition:
                        self._request_judge_task_condition.notify()

    async def _keep_request_judge_task(self, connection: ClientConnection) -> None:
        while True:
            if not self._task_scheduler.idle:
                await asyncio.sleep(_CHECK_TASK_SCHEDULER_IDLE_INTERVAL)
                continue

            await connection.send(
                json.dumps(
                    {
                        "type": "request_judge_task",
                        "data": {
                            "queue": 0,
                        },
                    }
                )
            )

            async with self._request_judge_task_condition:
                await self._request_judge_task_condition.wait()

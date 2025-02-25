"""Contains the task for judging matches."""

import asyncio
from dataclasses import dataclass
from typing import List, Optional

from base_agent_code_fetcher import BaseAgentCodeFetcher
from base_docker_image_builder import BaseDockerImageBuilder
from base_match_judger import BaseMatchJudger
from base_match_result_reporter import BaseMatchResultReporter
from base_task import BaseTask
from build_task import BuildTask
from match_result import MatchResult


@dataclass
class JudgeTask(BaseTask):
    """Task for judging a match."""

    _build_tasks: List[BuildTask]
    _game_host_image_tag: str
    _judger: BaseMatchJudger
    _match_id: str
    _reporter: BaseMatchResultReporter
    _result: Optional[MatchResult] = None

    def __init__(
        self,
        match_id: str,
        player_code_ids: List[str],
        game_host_image_tag: str,
        fetcher: BaseAgentCodeFetcher,
        builder: BaseDockerImageBuilder,
        judger: BaseMatchJudger,
        reporter: BaseMatchResultReporter,
    ):
        self._match_id = match_id
        self._game_host_image_tag = game_host_image_tag

        self._judger = judger
        self._reporter = reporter

        self._build_tasks = [
            BuildTask(code_id, fetcher, builder) for code_id in player_code_ids
        ]

    async def execute(self) -> MatchResult:
        """Runs the task.

        Returns:
            The match judge result
        """

        agent_image_tags = await asyncio.gather(
            *[t.execute() for t in self._build_tasks]
        )

        for tag in agent_image_tags:
            if tag.split(":")[0] == "E":
                match_result = MatchResult(
                    self._match_id, scores=[0, 0], record_file_path=""
                )
                await self._reporter.report(match_result)
                return match_result

        match_result = await self._judger.judge(
            self._match_id, self._game_host_image_tag, agent_image_tags
        )
        await self._reporter.report(match_result)
        self._result = match_result
        return match_result

    @property
    def result(self) -> Optional[MatchResult]:
        """The match judge result"""
        return self._result

"""Tests for the agent_code_fetcher module."""

import shutil
from pathlib import Path
from unittest import IsolatedAsyncioTestCase

import aiohttp

import agent_code_fetcher

CODE_ID = "a09f660a-e0e6-41ac-b721-f8ece8e71f33"
HTTP_BASE_URL = "https://api.dev.saiblo.net"


class TestAgentCodeFetcher(IsolatedAsyncioTestCase):
    """Tests for the AgentCodeFetcher class."""

    _session: aiohttp.ClientSession

    async def asyncSetUp(self) -> None:
        shutil.rmtree(
            Path("data"),
            ignore_errors=True,
        )

        self._session = aiohttp.ClientSession(HTTP_BASE_URL)

    async def asyncTearDown(self) -> None:
        shutil.rmtree(
            Path("data"),
            ignore_errors=True,
        )

        await self._session.close()

    async def test_clean_file_exists(self):
        """Test clean() when target file exists."""
        # Arrange.
        path = Path(f"data/agent_code/{CODE_ID}.tar")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        fetcher = agent_code_fetcher.AgentCodeFetcher(self._session)

        # Act.
        await fetcher.clean()

        # Assert.
        self.assertFalse(Path("data/agent_code").exists())

    async def test_clean_no_dir(self):
        """Test clean() when directory does not exist."""
        # Arrange.
        fetcher = agent_code_fetcher.AgentCodeFetcher(self._session)

        # Act.
        await fetcher.clean()

        # Assert.
        self.assertFalse(Path("data/agent_code").exists())

    async def test_fetch_file_exists(self):
        """Test fetch() when target file already exists."""
        # Arrange.
        path = Path(f"data/agent_code/{CODE_ID}.tar")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        fetcher = agent_code_fetcher.AgentCodeFetcher(self._session)

        # Act.
        result = await fetcher.fetch(CODE_ID)

        # Assert.
        self.assertEqual(path, result)

    async def test_fetch_no_file(self):
        """Test fetch() when file needs to be downloaded."""
        # Arrange.
        path = Path(f"data/agent_code/{CODE_ID}.tar")
        fetcher = agent_code_fetcher.AgentCodeFetcher(self._session)

        # Act.
        result = await fetcher.fetch(CODE_ID)

        # Assert.
        self.assertEqual(path, result)
        self.assertTrue(path.is_file())
        self.assertTrue(path.stat().st_size > 0)

    async def test_list(self):
        """Test list() returns correct dictionary of code IDs and paths."""
        # Arrange.
        Path("data/agent_code").mkdir(parents=True, exist_ok=True)
        path = Path(f"data/agent_code/{CODE_ID}.tar")
        path.touch()
        fetcher = agent_code_fetcher.AgentCodeFetcher(self._session)

        # Act.
        result = await fetcher.list()

        # Assert.
        self.assertEqual(
            {
                CODE_ID: path,
            },
            result,
        )

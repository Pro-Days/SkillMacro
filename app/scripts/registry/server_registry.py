from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.scripts.registry.resource_registry import convert_resource_path
from app.scripts.registry.skill_registry import SkillRegistry


@dataclass(frozen=True)
class ServerSpec:
    """서버 정보 클래스"""

    id: str
    usable_skill_count: int
    max_skill_level: int
    skill_registry: SkillRegistry


@dataclass
class ServerRegistry:
    """서버 정보를 등록하고 조회하는 레지스트리 클래스"""

    # 싱글톤 인스턴스
    # 프로그램 전체에서 단 하나의 상태 객체만 존재하도록 보장
    _instance: ServerRegistry | None = None

    # 초기화 여부
    _initialized: bool = False

    SERVERS: dict[str, ServerSpec] = field(default_factory=dict)

    def __new__(cls) -> ServerRegistry:
        if cls._instance is None:
            cls._instance = super(ServerRegistry, cls).__new__(cls)
        return cls._instance

    def _ensure_initialized(self) -> None:
        """초기화 여부 확인 및 초기화 작업 수행"""

        if not self._initialized:
            self.initialize()
            self._initialized = True

    def initialize(self) -> None:
        """JSON 파일을 읽어와 레지스트리를 초기화하는 메서드"""

        path: str = convert_resource_path("resources\\data\\skill_data.json")
        with open(path, "r", encoding="utf-8") as f:
            skill_data: dict[str, Any] = json.load(f)

        self.SERVERS["한월 RPG"] = ServerSpec(
            id="한월 RPG",
            usable_skill_count=6,
            max_skill_level=30,
            skill_registry=SkillRegistry.from_skill_data(skill_data, "한월 RPG"),
        )

    def get(self, name: str) -> ServerSpec:
        self._ensure_initialized()

        return self.SERVERS.get(name, self.SERVERS["한월 RPG"])

    def get_all_servers(self) -> list[ServerSpec]:
        self._ensure_initialized()

        return list(self.SERVERS.values())


server_registry = ServerRegistry()

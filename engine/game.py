"""Composition root: lắp mọi service vào một đối tượng Game duy nhất."""
from __future__ import annotations

import random
from collections import defaultdict

from core.bus import EventBus
from core.clock import Clock
from engine.economy import EconomyService, InventoryService
from engine.encounters import EncounterService, ExplorationService
from engine.events import EventService
from engine.ghosts import GhostService
from engine.orgs import OrgService
from engine.players import PlayerService
from engine.progress import ProgressService, QuestService
from engine.world import WorldService


class Game:
    def __init__(self, db, clock=None, rng=None):
        self.db = db
        self.clock = clock or Clock()
        self.rng = rng or random.Random()
        self.bus = EventBus()
        self._notices = defaultdict(list)
        self.players = PlayerService(self)
        self.inv = InventoryService(self)
        self.econ = EconomyService(self)
        self.world = WorldService(self)
        self.ghosts = GhostService(self)
        self.enc = EncounterService(self)
        self.explore = ExplorationService(self)
        self.events = EventService(self)
        self.orgs = OrgService(self)
        self.progress = ProgressService(self)
        self.quests = QuestService(self)
        self.bus.subscribe(self.progress.on_event)
        self.bus.subscribe(self.quests.on_event)

    def notify(self, uid, text):
        self._notices[uid].append(text)

    def drain_notices(self, uid) -> list[str]:
        return self._notices.pop(uid, [])

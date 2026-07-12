from __future__ import annotations

import random


class Deck:
    def __init__(self) -> None:
        self.cards = [f"{rank}{suit}" for suit in "CDHS" for rank in ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")]
        random.SystemRandom().shuffle(self.cards)

    def draw(self) -> str:
        if not self.cards:
            raise RuntimeError("deck exhausted")
        return self.cards.pop()

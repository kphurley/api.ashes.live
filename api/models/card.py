from enum import Enum
from typing import List, Optional

from api import db

from .release import Release


class DiceFlags(Enum):
    basic = 0
    ceremonial = 1
    charm = 2
    illusion = 4
    natural = 8
    divine = 16
    sympathy = 32
    time = 64


CARD_TYPE_ORDER = [
    "Phoenixborn",
    "Ready Spell",
    "Ally",
    "Alteration Spell",
    "Action Spell",
    "Reaction Spell",
    "Conjuration",
    "Conjured Alteration Spell",
]


class CardConjuration(db.AlchemyBase):
    __tablename__ = "card_conjuration"
    card_id = db.Column(
        db.Integer,
        db.ForeignKey("card.id"),
        nullable=False,
        primary_key=True,
    )
    conjuration_id = db.Column(
        db.Integer,
        db.ForeignKey("card.id"),
        nullable=False,
        primary_key=True,
    )


class Card(db.AlchemyBase):
    __tablename__ = "card"
    __table_args__ = (
        db.UniqueConstraint("name", "is_legacy"),
        db.UniqueConstraint("stub", "is_legacy"),
        # There is an additional index defined by the migrations that looks something like this:
        #     db.Index(
        #         "ix_card_text_tsv",
        #         db.func.to_tsvector(cls.search_text),
        #         postgresql_using="gin",
        #     ),
        # It is not included here because it kills the test suite (not compatible with create_all
        # evidently) and because alembic ignores it, anyway.
    )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_id = db.Column(db.Integer, nullable=False, index=True, unique=True)
    name = db.Column(db.String(30), nullable=False)
    stub = db.Column(db.String(30), nullable=False)
    phoenixborn = db.Column(db.String(25), nullable=True, index=True)
    release_id = db.Column(
        db.Integer, db.ForeignKey(Release.id), nullable=False, index=True, default=0
    )
    # This gets incremented when a card's text is updated due to errata
    version = db.Column(db.Integer, nullable=False, default=1)
    card_type = db.Column(db.String(25), nullable=False, index=True)
    is_summon_spell = db.Column(db.Boolean, nullable=False, default=False)
    is_legacy = db.Column(db.Boolean, nullable=False, default=False, index=True)
    cost_weight = db.Column(db.Integer, nullable=False, index=True, default=0)
    dice_flags = db.Column(db.Integer, nullable=False, index=True, default=0)
    alt_dice_flags = db.Column(db.Integer, nullable=False, index=True, default=0)
    copies = db.Column(db.SmallInteger, nullable=True, default=None)
    json = db.Column(db.JSONB)
    search_text = db.Column(db.Text)
    # These fields are specifically for Project Phoenix-designed cards
    artist_name = db.Column(db.String(100), nullable=True)
    artist_url = db.Column(db.String(255), nullable=True)

    # These fields are used for the traditional Chinese translation
    name_zh = db.Column(db.String(30), nullable=True)
    stub_zh = db.Column(db.String(30), nullable=True, index=True)
    json_zh = db.Column(db.JSONB, nullable=True)
    # TODO: figure out if I can actually support this, because I'm not so sure I can out of the box
    search_text_zh = db.Column(db.Text)
    # TODO: how the heck am I supposed to sort alphabetically by title for traditional Chinese?

    conjurations = db.relationship(
        "Card",
        secondary=CardConjuration.__table__,
        primaryjoin="Card.id == CardConjuration.card_id",
        secondaryjoin="Card.id == CardConjuration.conjuration_id",
        backref="summons",
    )
    release = db.relationship(Release)

    @db.hybrid_property
    def dice_weight(self):
        return self.dice_flags | self.alt_dice_flags

    @dice_weight.expression
    def dice_weight(cls):
        return cls.dice_flags.op("|")(cls.alt_dice_flags)

    @db.hybrid_property
    def type_weight(self):
        return CARD_TYPE_ORDER.index(self.card_type)

    @type_weight.expression
    def type_weight(cls):
        return db.case(
            [
                (cls.card_type == value, index)
                for index, value in enumerate(CARD_TYPE_ORDER)
            ],
            else_=len(CARD_TYPE_ORDER),
        )

    @staticmethod
    def dice_to_flags(dice_list: Optional[List[str]]) -> int:
        """Converts from a list of dice names to an integer flag; basic == 0"""
        flags = 0
        if not dice_list:
            return flags
        for die in dice_list:
            flags = flags | DiceFlags[die].value
        return flags

    @staticmethod
    def flags_to_dice(flags_int: int) -> Optional[List[str]]:
        """Converts from a dice flag to a list of dice names; always excludes basic dice"""
        dice = [
            die.name
            for die in DiceFlags
            if die.value and die.value & flags_int == die.value
        ]
        return dice if dice else None

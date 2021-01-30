import random
import string
import uuid
from datetime import timedelta
from typing import Optional, Tuple

from api import db, models
from api.environment import settings
from api.services.card import create_card
from api.services.user import create_user
from api.utils.auth import create_access_token


def monkeypatch_settings(monkeypatch, new_settings: dict):
    """Patches the given setting for a single test"""
    for key, value in new_settings.items():
        monkeypatch.setattr(settings, key, value)


def create_user_password(session: db.Session) -> Tuple[models.User, str]:
    """Returns a new user, and their plaintext password"""
    email = generate_random_email()
    password = generate_random_chars(16)
    user = create_user(session, email=email, password=password)
    return user, password


def create_user_token(
    session: db.Session, user: Optional["models.User"] = None
) -> Tuple[models.User, str]:
    """Returns a new user, and their associated bearer token"""
    if not user:
        user, _ = create_user_password(session)
    token = create_access_token(
        data={"sub": user.badge, "jti": uuid.uuid4().hex},
        expires_delta=timedelta(minutes=15),
    )
    return user, token


def create_admin_token(session: db.Session) -> Tuple[models.User, str]:
    user, token = create_user_token(session)
    user.is_admin = True
    session.commit()
    return user, token


def generate_random_email() -> str:
    """Returns a random email-like string"""
    return f"{generate_random_chars(4)}@{generate_random_chars(6)}.fake".lower()


def generate_random_chars(length=10) -> str:
    """Returns a random alphanumeric string of the given length"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def create_card_database(session: db.Session, is_legacy=False):
    """Populates database with a minimum viable list of one of each card type"""
    # First create our two releases
    master_set = models.Release("Master Set")
    master_set.is_legacy = is_legacy
    master_set.is_public = True
    expansion = models.Release("First Expansion")
    expansion.is_legacy = is_legacy
    expansion.is_public = True
    session.add(master_set)
    session.add(expansion)
    session.commit()
    # Then create one of every type of card, with a mixture of all the different things that can be
    #  included to ensure that the automatic dice sorting and so forth works properly
    card_dicts = [
        {
            "name": "Example Conjuration",
            "card_type": "Conjuration",
            "placement": "Battlefield",
            "release": master_set,
            "attack": 0,
            "life": 2,
            "recover": 0,
            "copies": 3,
        },
        {
            "name": "Example Conjured Alteration",
            "card_type": "Conjured Alteration Spell",
            "placement": "Unit",
            "phoenixborn": "Example Phoenixborn",
            "release": master_set,
            "text": "Whoops: 1 [[basic]] - 1 [[discard]]: Discard this spell.",
            "effect_magic_cost": "1 [[basic]]",
            "attack": "-2",
            "copies": 2,
        },
        {
            "name": "Example Phoenixborn",
            "card_type": "Phoenixborn",
            "release": master_set,
            "text": "Mess With Them: [[main]] - 1 [[illusion:class]]: Place a [[Example Conjured Alteration]] conjured alteration spell on opponent's unit.",
            "effect_magic_cost": "1 [[illusion:class]]",
            "battlefield": 5,
            "life": 16,
            "spellboard": 4,
            "can_effect_repeat": True,
        },
        {
            "name": "Summon Example Conjuration",
            "card_type": "Ready Spell",
            "placement": "Spellboard",
            "release": master_set,
            "cost": "[[main]] - 1 [[basic]] - [[side]] / 1 [[discard]]",
            "text": "1 [[charm:class]]: Place a [[Example Conjuration]] conjuration on your battlefield.",
            "effect_magic_cost": ["1 [[charm:class]]"],
        },
        {
            "name": "Example Ally",
            "card_type": "Ally",
            "placement": "Battlefield",
            "phoenixborn": "Example Phoenixborn",
            "release": master_set,
            "cost": ["[[main]]", ["1 [[natural:power", "1 [[illusion:power]]"]],
            "text": "Stuffiness: [[main]] - [[exhaust]] - 1 [[natural:class]] / 1 [[illusion:class]]: Do stuff.",
            "effect_magic_cost": "1 [[natural:class]] / 1 [[illusion:class]]",
            "attack": 2,
            "life": 1,
            "recover": 1,
        },
        {
            "name": "Example Alteration",
            "card_type": "Alteration Spell",
            "placement": "Unit",
            "release": master_set,
            "cost": "[[side]] - 1 [[basic]] - 1 [[discard]]",
            "attack": "+2",
            "recover": "-1",
        },
        {
            "name": "Example Ready Spell",
            "card_type": "Ready Spell",
            "placement": "Spellboard",
            "release": expansion,
            "cost": "[[side]]",
            "text": "[[main]] - [[exhaust]]: Do more things.",
        },
        {
            "name": "Example Action",
            "card_type": "Action Spell",
            "placement": "Discard",
            "release": expansion,
            "cost": "[[main]] - 1 [[time:power]] - 1 [[basic]]",
            "text": "If you spent a [[sympathy:power]] to pay for this card, do more stuff.",
            "alt_dice": ["sympathy"],
        },
        {
            "name": "Example Reaction",
            "card_type": "Reaction Spell",
            "placement": "Discard",
            "release": expansion,
            "cost": "1 [[divine:class]] / 1 [[ceremonial:class]]",
            "text": "Do a happy dance.",
        },
    ]
    cards = []
    # Create our cards
    for card_dict in card_dicts:
        cards.append(create_card(session, **card_dict))
    if is_legacy:
        for card in cards:
            card.is_legacy = True
        session.commit()

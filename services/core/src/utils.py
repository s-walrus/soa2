import random
import string


def make_player_token() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=16))


def make_session_id() -> str:
    return "".join(random.choices(string.ascii_uppercase, k=4)) + "".join(
        random.choices(string.digits, k=2)
    )


def validate_player_name(name: str) -> bool:
    return bool(name)

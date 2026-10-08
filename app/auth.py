from dataclasses import dataclass
import hashlib
import hmac
import json

from app.database import settings


class AccessConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AccessIdentity:
    role: str
    company_id: int | None = None


@dataclass(frozen=True)
class ConfiguredIdentity:
    token_sha256: str
    identity: AccessIdentity


def _invalid_config() -> AccessConfigurationError:
    return AccessConfigurationError("Invalid access identity configuration")


def parse_access_identities(raw: str) -> tuple[ConfiguredIdentity, ...]:
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise _invalid_config() from exc

    if not isinstance(payload, list):
        raise _invalid_config()

    identities: list[ConfiguredIdentity] = []
    seen_hashes: set[str] = set()

    for item in payload:
        if not isinstance(item, dict):
            raise _invalid_config()

        token_sha256 = item.get("token_sha256")
        role = item.get("role")
        company_id = item.get("company_id")

        if (
            not isinstance(token_sha256, str)
            or len(token_sha256) != 64
            or any(char not in "0123456789abcdefABCDEF" for char in token_sha256)
        ):
            raise _invalid_config()

        normalized_hash = token_sha256.lower()
        if normalized_hash in seen_hashes:
            raise _invalid_config()
        seen_hashes.add(normalized_hash)

        if role == "operator":
            if (
                not isinstance(company_id, int)
                or isinstance(company_id, bool)
                or company_id <= 0
            ):
                raise _invalid_config()
            identity = AccessIdentity(
                role="operator",
                company_id=company_id,
            )
        elif role == "admin":
            if company_id is not None:
                raise _invalid_config()
            identity = AccessIdentity(role="admin")
        else:
            raise _invalid_config()

        identities.append(
            ConfiguredIdentity(
                token_sha256=normalized_hash,
                identity=identity,
            )
        )

    return tuple(identities)


def authenticate_bearer_token(token: str) -> AccessIdentity | None:
    token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()

    for configured in parse_access_identities(settings.access_identities_json):
        if hmac.compare_digest(configured.token_sha256, token_digest):
            return configured.identity

    return None

from __future__ import annotations

from config import Settings


def tags_to_dict(tags: list[dict[str, str]] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for tag in tags or []:
        key = tag.get("Key")
        value = tag.get("Value")
        if key and value:
            normalized[key] = value
    return normalized


def first_tag_value(tags: dict[str, str], keys: tuple[str, ...]) -> str | None:
    lower_lookup = {key.lower(): value for key, value in tags.items()}
    for key in keys:
        value = tags.get(key) or lower_lookup.get(key.lower())
        if value:
            return value
    return None


def ownership_metadata(tags: dict[str, str], settings: Settings) -> dict[str, str]:
    owner = first_tag_value(tags, settings.owner_tag_keys)
    environment = first_tag_value(tags, settings.environment_tag_keys) or settings.default_environment
    owner_email = resolve_owner_email(owner, environment, settings)

    metadata: dict[str, str] = {}
    if owner:
        metadata["owner"] = owner
    if owner_email:
        metadata["owner_email"] = owner_email
    if environment:
        metadata["environment"] = environment
    return metadata


def resolve_owner_email(owner: str | None, environment: str | None, settings: Settings) -> str | None:
    candidates = [owner, environment]
    if owner and environment:
        candidates.insert(0, f"{environment}:{owner}")
        candidates.insert(1, f"{owner}:{environment}")

    for candidate in candidates:
        if not candidate:
            continue
        mapped = settings.owner_email_map.get(candidate) or settings.owner_email_map.get(candidate.lower())
        if mapped:
            return mapped
        if "@" in candidate:
            return candidate
    return settings.default_owner_email or settings.gmail_recipient

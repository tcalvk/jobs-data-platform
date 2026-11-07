"""Fail-closed loading of the versioned structural landing contract."""

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


class _UniqueKeysLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError("Duplicate contract key")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueKeysLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


@dataclass(frozen=True)
class Contract:
    version: int
    columns: tuple[str, ...]


def load_contract(path: Path | None = None) -> Contract:
    path = path or Path(__file__).with_name("contracts.yml")
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeysLoader)
        if set(data) != {"active_contract_version", "contracts"}:
            raise ValueError()
        version = data["active_contract_version"]
        if type(version) is not int or version < 1 or version not in data["contracts"]:
            raise ValueError()
        for number, entry in data["contracts"].items():
            if type(number) is not int or number < 1 or set(entry) != {"source", "validation"}:
                raise ValueError()
            source = entry["source"]
            if set(source) != {"encoding", "delimiter", "header", "quoting", "columns"}:
                raise ValueError()
            if (source["encoding"], source["delimiter"], source["header"], source["quoting"]) != ("utf-8", "\t", False, "literal") or source["header"] is not False:
                raise ValueError()
            columns = source["columns"]
            if not isinstance(columns, list) or len(columns) != 27:
                raise ValueError()
            for col in columns:
                if set(col) != {"field", "+type"} or col["+type"] != "string" or not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", col["field"]):
                    raise ValueError()
            if len({c["field"] for c in columns}) != 27:
                raise ValueError()
            if entry["validation"] != {"invalid_file_action": "reject_entire_file", "rules": []}:
                raise ValueError()
        return Contract(version, tuple(c["field"] for c in data["contracts"][version]["source"]["columns"]))
    except (TypeError, KeyError, ValueError, AttributeError, yaml.YAMLError) as exc:
        raise ValueError("Invalid or unsupported GKG contract configuration") from exc

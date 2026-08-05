from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any


REG_SUFFIX_RE = re.compile(r"^(?P<name>.+) Regulator (?P<kind>Enabled|Setpoint|Hysteresis|Mode|Output|Permit Input|Invert)$")
DIFF_PREFIX = "Differential Regulator "
DIFF_DUMP_PREFIX = "Differential Dump "
COUNTER_RE = re.compile(r"^P(?P<port>\d+) Counter$")
COUNTER_RESET_RE = re.compile(r"^P(?P<port>\d+) Counter Reset$")
PORT_RE = re.compile(r"^P(?P<port>\d+)$")
IP_RE = re.compile(r"(?P<ip>\d+_\d+_\d+_\d+)")
HIDDEN_STATES = {"unknown", "unavailable", "none", "null", ""}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def common_prefix(values: list[str]) -> str:
    if not values:
        return "megaesp"
    prefix = values[0]
    for value in values[1:]:
        while not value.startswith(prefix) and prefix:
            prefix = prefix[:-1]
    return prefix.rstrip("_") or "megaesp"


def detect_device_label(object_ids: list[str]) -> str:
    counts: dict[str, int] = {}
    for object_id in object_ids:
        match = IP_RE.search(object_id)
        if not match:
            continue
        ip = match.group("ip")
        counts[ip] = counts.get(ip, 0) + 1
    if counts:
        ip = max(counts, key=counts.get)
        return f"MegaESP {ip.replace('_', '.')}"
    prefix = common_prefix(object_ids)
    return prefix.replace("_", " ").title()


def detect_device_path(object_ids: list[str]) -> str:
    counts: dict[str, int] = {}
    for object_id in object_ids:
        match = IP_RE.search(object_id)
        if not match:
            continue
        ip = match.group("ip")
        counts[ip] = counts.get(ip, 0) + 1
    if counts:
        return f"megaesp_{max(counts, key=counts.get)}"
    return slug(common_prefix(object_ids)) or "controller"


def detect_device_ip(object_ids: list[str]) -> str | None:
    counts: dict[str, int] = {}
    for object_id in object_ids:
        match = IP_RE.search(object_id)
        if not match:
            continue
        ip = match.group("ip").replace("_", ".")
        counts[ip] = counts.get(ip, 0) + 1
    if counts:
        return max(counts, key=counts.get)
    return None


def should_keep_entity(entity: dict[str, Any], states: dict[str, str], config: dict[str, Any]) -> bool:
    entity_id = entity["entity_id"]
    original_name = entity.get("original_name") or ""
    if entity_id in set(config.get("hidden_entities", [])):
        return False
    if original_name in set(config.get("hidden_original_names", [])):
        return False
    domain = entity_id.split(".", 1)[0]
    if domain == "switch":
        return True
    state = states.get(entity_id)
    # Keep configured input ports and counters visible even if HA hasn't populated
    # their state yet during early startup regeneration.
    if domain == "binary_sensor" and PORT_RE.match(original_name):
        return True if state is None else state.strip().lower() not in HIDDEN_STATES
    if domain == "sensor" and COUNTER_RE.match(original_name):
        return True if state is None else state.strip().lower() not in HIDDEN_STATES
    if state is None:
        return False
    return state.strip().lower() not in HIDDEN_STATES


def group_by_device(entities: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entity in entities:
        grouped[entity.get("device_id") or entity["entity_id"]].append(entity)
    return grouped


def find_regulator_value_entity(base_name: str, entities: list[dict[str, Any]]) -> str | None:
    candidates: list[tuple[int, str]] = []
    base_norm = base_name.strip().lower()
    base_slug = slug(base_name)
    for entity in entities:
        entity_id = entity["entity_id"]
        if not entity_id.startswith("sensor."):
            continue
        original_name = (entity.get("original_name") or "").strip()
        original_norm = original_name.lower()
        entity_slug = slug(original_name)
        score = None
        if original_norm == base_norm:
            score = 100
        elif entity_slug == base_slug:
            score = 95
        elif original_norm.startswith(base_norm + " "):
            score = 80
        elif base_norm and base_norm in original_norm:
            score = 60
        elif base_slug and base_slug in entity_slug:
            score = 50
        if score is not None:
            candidates.append((score, entity_id))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][1]


def build_regulators(
    entities: list[dict[str, Any]], config: dict[str, Any]
) -> tuple[list[dict[str, Any]], set[str]]:
    regulators: dict[str, dict[str, Any]] = {}
    used_sensor_entities: set[str] = set()
    sensor_by_original = {
        e.get("original_name"): e["entity_id"]
        for e in entities
        if e["entity_id"].startswith("sensor.")
    }
    for entity in entities:
        original_name = entity.get("original_name") or ""
        match = REG_SUFFIX_RE.match(original_name)
        if not match:
            continue
        base_name = match.group("name")
        kind = match.group("kind")
        item = regulators.setdefault(base_name, {"name": base_name, "entities": []})
        if kind == "Enabled":
            sensor_entity = sensor_by_original.get(base_name) or find_regulator_value_entity(base_name, entities)
            if sensor_entity:
                item["entities"].append({"entity": sensor_entity, "name": "Current value"})
                used_sensor_entities.add(sensor_entity)
        row_name = {
            "Enabled": "Regulator enabled",
            "Setpoint": "Setpoint",
            "Hysteresis": "Hysteresis",
            "Mode": "Mode",
            "Output": "Output port",
            "Permit Input": "Permit input",
            "Invert": "Invert output",
        }[kind]
        item["entities"].append({"entity": entity["entity_id"], "name": row_name})

    diff_rows = {
        "Differential Regulator Hot Sensor": "Hot sensor",
        "Differential Regulator Tank Sensor": "Tank sensor",
        "Differential Regulator Pump Output": "Pump output",
        "Differential Regulator Permit Input": "Permit input",
        "Differential Regulator Invert": "Invert output",
        "Differential Regulator Delta On": "Delta on",
        "Differential Regulator Delta Off": "Delta off",
        "Differential Regulator Tank Minimum": "Tank minimum",
        "Differential Regulator Overheat": "Overheat",
        "Differential Regulator Overheat Hysteresis": "Overheat hysteresis",
        "Differential Regulator Freeze On": "Freeze on",
        "Differential Regulator Freeze Off": "Freeze off",
        "Differential Regulator Freeze Tank Minimum": "Freeze tank minimum",
        "Differential Hot Sensor": "Hot sensor",
        "Differential Tank Sensor": "Tank sensor",
        "Differential Pump Output": "Pump output",
        "Differential Delta On": "Delta on",
        "Differential Delta Off": "Delta off",
        "Differential Tank Minimum": "Tank minimum",
        "Differential Overheat": "Overheat",
        "Differential Overheat Hysteresis": "Overheat hysteresis",
        "Differential Freeze On": "Freeze on",
        "Differential Freeze Off": "Freeze off",
        "Differential Freeze Tank Minimum": "Freeze tank minimum",
        "Differential Regulator Enabled": "Regulator enabled",
        "Differential Pump Active": "Pump active",
        "Differential Overheat Active": "Overheat active",
        "Differential Freeze Active": "Freeze active",
    }
    for entity in entities:
        original_name = entity.get("original_name") or ""
        if original_name == "Differential Hot Temperature":
            item = regulators.setdefault("Differential", {"name": "Differential", "entities": []})
            item["entities"].append({"entity": entity["entity_id"], "name": "Hot temperature"})
            used_sensor_entities.add(entity["entity_id"])
        elif original_name == "Differential Tank Temperature":
            item = regulators.setdefault("Differential", {"name": "Differential", "entities": []})
            item["entities"].append({"entity": entity["entity_id"], "name": "Tank temperature"})
            used_sensor_entities.add(entity["entity_id"])
        elif original_name == "Differential Delta":
            item = regulators.setdefault("Differential", {"name": "Differential", "entities": []})
            item["entities"].append({"entity": entity["entity_id"], "name": "Current delta"})
            used_sensor_entities.add(entity["entity_id"])
        elif original_name in diff_rows:
            item = regulators.setdefault("Differential", {"name": "Differential", "entities": []})
            if not any(row["entity"] == entity["entity_id"] for row in item["entities"]):
                item["entities"].append({"entity": entity["entity_id"], "name": diff_rows[original_name]})
        elif original_name.startswith(DIFF_DUMP_PREFIX):
            item = regulators.setdefault("Differential", {"name": "Differential", "entities": []})
            if not any(row["entity"] == entity["entity_id"] for row in item["entities"]):
                item["entities"].append(
                    {"entity": entity["entity_id"], "name": f"Dump {original_name[len(DIFF_DUMP_PREFIX):]}"}
                )

    for item in regulators.values():
        item["name"] = config.get("rename_original_names", {}).get(item["name"], item["name"])

    return sorted(regulators.values(), key=lambda item: item["name"].lower()), used_sensor_entities


def build_sensor_control_cards(
    entities: list[dict[str, Any]], controller_path: str, config: dict[str, Any]
) -> tuple[list[dict[str, Any]], set[str]]:
    sensor_by_original = {
        entity.get("original_name"): entity["entity_id"]
        for entity in entities
        if entity["entity_id"].startswith("sensor.")
    }
    regulator_rows: dict[str, dict[str, str]] = {}
    used_entities: set[str] = set()

    for entity in entities:
        original_name = entity.get("original_name") or ""
        match = REG_SUFFIX_RE.match(original_name)
        if not match:
            continue
        regulator_rows.setdefault(match.group("name"), {})[match.group("kind")] = entity["entity_id"]

    cards: list[dict[str, Any]] = []
    for base_name in sorted(regulator_rows):
        if base_name in {"Pressure", "Differential"}:
            continue
        rows = regulator_rows[base_name]
        sensor_entity = sensor_by_original.get(base_name) or find_regulator_value_entity(base_name, entities)
        enabled_entity = rows.get("Enabled")
        if not enabled_entity:
            continue

        used_entities.add(enabled_entity)
        if sensor_entity:
            used_entities.add(sensor_entity)
        for kind in ("Setpoint", "Hysteresis", "Mode", "Output", "Permit Input", "Invert"):
            entity_id = rows.get(kind)
            if entity_id:
                used_entities.add(entity_id)

        cards.append(
            {
                "type": "custom:mushroom-template-card",
                "entity": sensor_entity or enabled_entity,
                "primary": config.get("rename_original_names", {}).get(base_name, base_name),
                "secondary": (
                    "{{ states(entity) }}" if sensor_entity else "{{ 'Enabled' if is_state(entity, 'on') else 'Disabled' }}"
                ),
                "icon": "mdi:thermometer",
                "icon_color": "{{ 'orange' if is_state('" + enabled_entity + "', 'on') else 'disabled' }}",
                "layout": "horizontal",
                "multiline_primary": False,
                "multiline_secondary": False,
                "tap_action": {
                    "action": "navigate",
                    "navigation_path": f"/megaesp-panel/{controller_path}_{slug(base_name)}",
                },
            }
        )

    return cards, used_entities


def build_sensor_regulator_subviews(
    entities: list[dict[str, Any]], controller_path: str, config: dict[str, Any]
) -> tuple[list[dict[str, Any]], set[str]]:
    sensor_by_original = {
        entity.get("original_name"): entity["entity_id"]
        for entity in entities
        if entity["entity_id"].startswith("sensor.")
    }
    regulator_rows: dict[str, dict[str, str]] = {}
    used_entities: set[str] = set()

    for entity in entities:
        original_name = entity.get("original_name") or ""
        match = REG_SUFFIX_RE.match(original_name)
        if not match:
            continue
        regulator_rows.setdefault(match.group("name"), {})[match.group("kind")] = entity["entity_id"]

    subviews: list[dict[str, Any]] = []
    for base_name in sorted(regulator_rows):
        if base_name in {"Pressure", "Differential"}:
            continue
        rows = regulator_rows[base_name]
        sensor_entity = sensor_by_original.get(base_name) or find_regulator_value_entity(base_name, entities)
        enabled_entity = rows.get("Enabled")
        if not enabled_entity:
            continue

        used_entities.add(enabled_entity)
        if sensor_entity:
            used_entities.add(sensor_entity)
        entities_list = []
        if sensor_entity:
            entities_list.append({"entity": sensor_entity, "name": "Value"})
        entities_list.append({"entity": enabled_entity, "name": "Regulator"})
        for kind, row_name in (("Setpoint", "Setpoint"), ("Hysteresis", "Hysteresis"), ("Mode", "Mode"), ("Output", "Output port"), ("Permit Input", "Permit input"), ("Invert", "Invert output")):
            entity_id = rows.get(kind)
            if entity_id:
                used_entities.add(entity_id)
                entities_list.append({"entity": entity_id, "name": row_name})

        subviews.append(
            {
                "title": f"{config.get('rename_original_names', {}).get(base_name, base_name)} Settings",
                "path": f"{controller_path}_{slug(base_name)}",
                "subview": True,
                "cards": [
                    {
                        "type": "entities",
                        "title": config.get("rename_original_names", {}).get(base_name, base_name),
                        "show_header_toggle": False,
                        "entities": entities_list,
                    }
                ],
            }
        )

    return subviews, used_entities


def build_special_regulator_cards_and_subviews(
    entities: list[dict[str, Any]], controller_path: str, config: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    original_to_entity = {
        entity.get("original_name"): entity["entity_id"]
        for entity in entities
        if entity.get("original_name")
    }
    cards: list[dict[str, Any]] = []
    subviews: list[dict[str, Any]] = []
    used_entities: set[str] = set()

    pressure_enabled = original_to_entity.get("Pressure Regulator Enabled")
    pressure_value = original_to_entity.get("Pressure")
    pressure_setpoint = original_to_entity.get("Pressure Regulator Setpoint")
    pressure_hyst = original_to_entity.get("Pressure Regulator Hysteresis")
    pressure_output = original_to_entity.get("Pressure Regulator Output")
    pressure_permit = original_to_entity.get("Pressure Regulator Permit Input")
    pressure_invert = original_to_entity.get("Pressure Regulator Invert")
    if pressure_enabled:
        used_entities.add(pressure_enabled)
        for entity_id in (pressure_value, pressure_setpoint, pressure_hyst, pressure_output, pressure_permit, pressure_invert):
            if entity_id:
                used_entities.add(entity_id)
        cards.append(
            {
                "type": "custom:mushroom-template-card",
                "entity": pressure_value or pressure_enabled,
                "primary": config.get("rename_original_names", {}).get("Pressure", "Pressure"),
                "secondary": (
                    "{{ states(entity) ~ ' bar' if states(entity) not in ['unknown', 'unavailable', 'None', 'none'] else ('Enabled' if is_state('" + pressure_enabled + "', 'on') else 'Disabled') }}"
                    if pressure_value
                    else "{{ 'Enabled' if is_state(entity, 'on') else 'Disabled' }}"
                ),
                "icon": "mdi:gauge",
                "icon_color": "{{ 'orange' if is_state('" + pressure_enabled + "', 'on') else 'disabled' }}",
                "layout": "horizontal",
                "multiline_primary": False,
                "multiline_secondary": False,
                "tap_action": {"action": "navigate", "navigation_path": f"/megaesp-panel/{controller_path}_pressure"},
            }
        )
        subview_entities = []
        if pressure_value:
            subview_entities.append({"entity": pressure_value, "name": "Value"})
        subview_entities.append({"entity": pressure_enabled, "name": "Regulator"})
        if pressure_setpoint:
            subview_entities.append({"entity": pressure_setpoint, "name": "Setpoint"})
        if pressure_hyst:
            subview_entities.append({"entity": pressure_hyst, "name": "Hysteresis"})
        if pressure_output:
            subview_entities.append({"entity": pressure_output, "name": "Output"})
        if pressure_permit:
            subview_entities.append({"entity": pressure_permit, "name": "Permit input"})
        if pressure_invert:
            subview_entities.append({"entity": pressure_invert, "name": "Invert output"})
        subviews.append(
            {
                "title": f"{config.get('rename_original_names', {}).get('Pressure', 'Pressure')} Settings",
                "path": f"{controller_path}_pressure",
                "subview": True,
                "cards": [
                    {
                        "type": "entities",
                        "title": config.get("rename_original_names", {}).get("Pressure", "Pressure"),
                        "show_header_toggle": False,
                        "entities": subview_entities,
                    }
                ],
            }
        )

    diff_enabled = original_to_entity.get("Differential Regulator Enabled")
    if diff_enabled:
        diff_delta = original_to_entity.get("Differential Delta")
        used_entities.add(diff_enabled)
        if diff_delta:
            used_entities.add(diff_delta)
        diff_fields = (
            ("Differential Regulator Tank Minimum", "Tank minimum"),
            ("Differential Regulator Delta On", "Delta on"),
            ("Differential Regulator Delta Off", "Delta off"),
            ("Differential Regulator Overheat", "Overheat"),
            ("Differential Regulator Overheat Hysteresis", "Overheat hysteresis"),
            ("Differential Regulator Freeze On", "Freeze on"),
            ("Differential Regulator Freeze Off", "Freeze off"),
            ("Differential Regulator Freeze Tank Minimum", "Freeze tank minimum"),
            ("Differential Regulator Hot Sensor", "Hot sensor"),
            ("Differential Regulator Tank Sensor", "Tank sensor"),
            ("Differential Regulator Pump Output", "Pump output"),
            ("Differential Regulator Permit Input", "Permit input"),
            ("Differential Regulator Invert", "Invert output"),
            ("Differential Hot Temperature", "Hot temperature"),
            ("Differential Tank Temperature", "Tank temperature"),
            ("Differential Pump Active", "Pump active"),
            ("Differential Overheat Active", "Overheat active"),
            ("Differential Freeze Active", "Freeze active"),
        )
        for original_name, _ in diff_fields:
            entity_id = original_to_entity.get(original_name)
            if entity_id:
                used_entities.add(entity_id)
        dump_switches = sorted(
            (
                entity["entity_id"],
                entity.get("original_name") or entity["entity_id"].split(".")[-1],
            )
            for entity in entities
            if (entity.get("original_name") or "").startswith("Differential Dump ")
        )
        for entity_id, _ in dump_switches:
            used_entities.add(entity_id)
        cards.append(
            {
                "type": "custom:mushroom-template-card",
                "entity": diff_delta or diff_enabled,
                "primary": config.get("rename_original_names", {}).get("Differential", "Differential"),
                "secondary": "{{ states(entity) ~ ' °C' if states(entity) not in ['unknown', 'unavailable', 'None', 'none'] else ('Enabled' if is_state('" + diff_enabled + "', 'on') else 'Disabled') }}",
                "icon": "mdi:delta",
                "icon_color": "{{ 'orange' if is_state('" + diff_enabled + "', 'on') else 'disabled' }}",
                "layout": "horizontal",
                "multiline_primary": False,
                "multiline_secondary": False,
                "tap_action": {"action": "navigate", "navigation_path": f"/megaesp-panel/{controller_path}_differential"},
            }
        )
        subview_entities = []
        if diff_delta:
            subview_entities.append({"entity": diff_delta, "name": "Value"})
        subview_entities.append({"entity": diff_enabled, "name": "Regulator"})
        if diff_delta:
            subview_entities.append({"entity": diff_delta, "name": "Current delta"})
        for original_name, label in diff_fields:
            entity_id = original_to_entity.get(original_name)
            if entity_id:
                subview_entities.append({"entity": entity_id, "name": label})
        for entity_id, original_name in dump_switches:
            subview_entities.append({"entity": entity_id, "name": original_name.replace("Differential Dump ", "Dump ")})
        subviews.append(
            {
                "title": f"{config.get('rename_original_names', {}).get('Differential', 'Differential')} Settings",
                "path": f"{controller_path}_differential",
                "subview": True,
                "cards": [
                    {
                        "type": "entities",
                        "title": config.get("rename_original_names", {}).get("Differential", "Differential"),
                        "show_header_toggle": False,
                        "entities": subview_entities,
                    }
                ],
            }
        )

    return cards, subviews, used_entities


def section_card(title: str) -> dict[str, Any]:
    return {"type": "markdown", "content": f"## {title}"}


def build_cards(
    entities: list[dict[str, Any]], controller_path: str, config: dict[str, Any], states: dict[str, str], device_id: str | None = None, device_ip: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cards: list[dict[str, Any]] = []
    control_cards: list[dict[str, Any]] = []
    regulator_cards: list[dict[str, Any]] = []
    input_cards: list[dict[str, Any]] = []
    sensor_cards: list[dict[str, Any]] = []
    service_cards: list[dict[str, Any]] = []
    special_regulator_cards, special_regulator_subviews, used_special_regulator_entities = build_special_regulator_cards_and_subviews(
        entities, controller_path, config
    )
    sensor_control_cards, used_sensor_control_entities = build_sensor_control_cards(entities, controller_path, config)
    sensor_subviews, used_sensor_subview_entities = build_sensor_regulator_subviews(entities, controller_path, config)

    links_cards: list[dict[str, Any]] = []
    if device_id or device_ip:
        buttons: list[dict[str, Any]] = []
        if device_id:
            buttons.append(
                {
                    "type": "button",
                    "name": "HA",
                    "icon": "mdi:home-assistant",
                    "tap_action": {
                        "action": "navigate",
                        "navigation_path": f"/config/devices/device/{device_id}",
                    },
                }
            )
        if device_ip:
            buttons.append(
                {
                    "type": "button",
                    "name": "Web",
                    "icon": "mdi:web",
                    "tap_action": {
                        "action": "url",
                        "url_path": f"http://{device_ip}/",
                    },
                }
            )
        if buttons:
            links_cards.append({"type": "grid", "columns": 2, "square": False, "cards": buttons})

    outputs = [
        {"entity": e["entity_id"]}
        for e in sorted(entities, key=lambda item: item["entity_id"])
        if e["entity_id"].startswith("switch.")
        and "regulator_enabled" not in e["entity_id"]
        and "regulator_invert" not in e["entity_id"]
        and "pressure_regulator_invert" not in e["entity_id"]
        and "differential_regulator_invert" not in e["entity_id"]
        and "differential_dump_" not in e["entity_id"]
    ]
    if outputs:
        control_cards.append(
            {
                "type": "entities",
                "title": config.get("section_titles", {}).get("controls_outputs", "Outputs"),
                "show_header_toggle": False,
                "entities": outputs,
            }
        )

    if special_regulator_cards:
        regulator_cards.append({"type": "grid", "columns": 2, "square": False, "cards": special_regulator_cards})

    regulators, used_sensor_entities = build_regulators(entities, config)
    sensor_original_names = {entity.get("original_name") for entity in entities if entity["entity_id"].startswith("sensor.")}
    for regulator in regulators:
        if regulator["name"] in {"Pressure", "Differential"}:
            continue
        if regulator["name"] in sensor_original_names:
            continue
        regulator_entity_ids = {row.get("entity") for row in regulator["entities"] if row.get("entity")}
        if regulator_entity_ids & used_sensor_control_entities:
            continue
        regulator_cards.append(
            {
                "type": "entities",
                "title": f"{regulator['name']} Regulator",
                "show_header_toggle": False,
                "entities": regulator["entities"],
            }
        )

    input_ports: dict[int, list[dict[str, Any]]] = defaultdict(list)
    counter_resets: list[dict[str, Any]] = []
    other_sensors: list[dict[str, Any]] = []
    meta_sensors: list[dict[str, Any]] = []

    for entity in sorted(entities, key=lambda item: item["entity_id"]):
        entity_id = entity["entity_id"]
        original_name = entity.get("original_name") or ""

        if REG_SUFFIX_RE.match(original_name) or original_name.startswith(DIFF_PREFIX) or original_name.startswith(DIFF_DUMP_PREFIX) or original_name in {
            "Differential Hot Temperature",
            "Differential Tank Temperature",
            "Differential Delta",
        }:
            continue
        if entity_id.startswith("switch.") and "regulator_enabled" not in entity_id and "differential_dump_" not in entity_id:
            continue

        counter_match = COUNTER_RE.match(original_name)
        if counter_match and entity_id.startswith("sensor."):
            state = states.get(entity_id, "").strip().lower()
            if state in HIDDEN_STATES:
                continue
            input_ports[int(counter_match.group("port"))].append({"entity": entity_id})
            continue

        reset_match = COUNTER_RESET_RE.match(original_name)
        if reset_match and entity_id.startswith("button."):
            counter_resets.append({"entity": entity_id})
            continue

        port_match = PORT_RE.match(original_name)
        if port_match and entity_id.startswith("binary_sensor."):
            state = states.get(entity_id, "").strip().lower()
            if state in HIDDEN_STATES:
                continue
            input_ports[int(port_match.group("port"))].append({"entity": entity_id})
            continue

        if original_name in {"RTC time"} or entity_id.endswith("_analog"):
            meta_sensors.append({"entity": entity_id})
            continue

        if entity_id.startswith("sensor."):
            if entity_id in used_sensor_entities or entity_id in used_sensor_control_entities or entity_id in used_sensor_subview_entities or entity_id in used_special_regulator_entities:
                continue
            other_sensors.append({"entity": entity_id})
            continue

        if entity_id in used_sensor_control_entities or entity_id in used_special_regulator_entities:
            continue

    if input_ports or meta_sensors:
        input_entities: list[dict[str, Any]] = []
        for port in sorted(input_ports):
            input_entities.extend(sorted(input_ports[port], key=lambda item: item["entity"]))
        if input_entities:
            input_cards.append(
                {
                    "type": "entities",
                    "title": config.get("section_titles", {}).get("inputs_list", "Inputs"),
                    "show_header_toggle": False,
                    "entities": input_entities,
                }
            )
        if meta_sensors:
            service_cards.append(
                {
                    "type": "entities",
                    "title": config.get("section_titles", {}).get("device_status", "Device Status"),
                    "show_header_toggle": False,
                    "entities": meta_sensors,
                }
            )

    if counter_resets:
        service_cards.append(
            {
                "type": "entities",
                "title": config.get("section_titles", {}).get("counter_reset", "Counter Reset"),
                "show_header_toggle": False,
                "entities": counter_resets,
            }
        )

    if sensor_control_cards:
        sensor_cards.append({"type": "grid", "columns": 2, "square": False, "cards": sensor_control_cards})
    if other_sensors:
        sensor_cards.append(
            {
                "type": "entities",
                "title": config.get("section_titles", {}).get("other_sensors", "Other Sensors"),
                "show_header_toggle": False,
                "entities": other_sensors,
            }
        )

    hidden_sections = set(config.get("hidden_sections", []))
    section_titles = config.get("section_titles", {})

    if links_cards:
        cards.append(section_card(section_titles.get("links", "Links")))
        cards.extend(links_cards)

    if control_cards and "controls" not in hidden_sections:
        cards.append(section_card(section_titles.get("controls", "Controls")))
        cards.extend(control_cards)
    if regulator_cards and "regulators" not in hidden_sections:
        cards.append(section_card(section_titles.get("regulators", "Regulators")))
        cards.extend(regulator_cards)
    if input_cards and "inputs" not in hidden_sections:
        cards.append(section_card(section_titles.get("inputs", "Inputs")))
        cards.extend(input_cards)
    if sensor_cards and "sensors" not in hidden_sections:
        cards.append(section_card(section_titles.get("sensors", "Sensors")))
        cards.extend(sensor_cards)
    if service_cards and "service" not in hidden_sections:
        cards.append(section_card(section_titles.get("service", "Service")))
        cards.extend(service_cards)

    return cards, [*sensor_subviews, *special_regulator_subviews]


def build_dashboard(
    entities: list[dict[str, Any]], states: dict[str, str], config: dict[str, Any]
) -> dict[str, Any]:
    entities = [entity for entity in entities if should_keep_entity(entity, states, config)]
    grouped = group_by_device(entities)
    controller_views = []
    overview_links: list[str] = []
    for _, device_entities in sorted(grouped.items(), key=lambda item: common_prefix([e["entity_id"].split(".", 1)[1] for e in item[1]])):
        device_id = device_entities[0].get("device_id")
        object_ids = [e["entity_id"].split(".", 1)[1] for e in device_entities]
        title = detect_device_label(object_ids)
        path = detect_device_path(object_ids)
        ip = detect_device_ip(object_ids)
        overview_links.append(f"- [{title}](/megaesp-panel/{path})")
        cards, subviews = build_cards(device_entities, path, config, states, device_id, ip)
        controller_views.append({"title": title, "path": path, "icon": "mdi:chip", "cards": cards})
        controller_views.extend(subviews)

    views = [
        {
            "title": "Overview",
            "path": "overview",
            "icon": "mdi:view-dashboard",
            "cards": [
                {
                    "type": "markdown",
                    "title": "Controllers",
                    "content": "\n".join(["## MegaESP", "", *overview_links]) or "No controllers found.",
                }
            ],
        },
        {
            "title": "Panel Config",
            "path": "panel-config",
            "icon": "mdi:file-edit-outline",
            "cards": [
                {
                    "type": "markdown",
                    "content": (
                        "## Panel Config\n\n"
                        "Open Home Assistant config directly in `code-server`."
                    ),
                },
                {
                    "type": "button",
                    "name": "Open Code Editor",
                    "icon": "mdi:microsoft-visual-studio-code",
                    "tap_action": {
                        "action": "url",
                        "url_path": "http://192.168.0.201:8443/?folder=/config",
                    },
                },
                {
                    "type": "markdown",
                    "content": (
                        "Open these files in the left tree:\n\n"
                        "- `/config/megaesp-dashboard-config.json`\n"
                        "- `/config/megaesp-dashboard.yaml`"
                    ),
                },
            ],
        },
    ]
    views.extend(controller_views)
    return {"title": "MegaESP", "views": views}


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if re.fullmatch(r"[A-Za-z0-9_./:-]+", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def dump_yaml(data: Any, indent: int = 0) -> list[str]:
    pad = "  " * indent
    if isinstance(data, dict):
        lines: list[str] = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(dump_yaml(value, indent + 1))
            else:
                lines.append(f"{pad}{key}: {yaml_scalar(value)}")
        return lines
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, dict):
                first = True
                for key, value in item.items():
                    if first:
                        if isinstance(value, (dict, list)):
                            lines.append(f"{pad}- {key}:")
                            lines.extend(dump_yaml(value, indent + 1))
                        else:
                            lines.append(f"{pad}- {key}: {yaml_scalar(value)}")
                        first = False
                    else:
                        if isinstance(value, (dict, list)):
                            lines.append(f"{pad}  {key}:")
                            lines.extend(dump_yaml(value, indent + 2))
                        else:
                            lines.append(f"{pad}  {key}: {yaml_scalar(value)}")
            elif isinstance(item, list):
                lines.append(f"{pad}-")
                lines.extend(dump_yaml(item, indent + 1))
            else:
                lines.append(f"{pad}- {yaml_scalar(item)}")
        return lines
    return [f"{pad}{yaml_scalar(data)}"]

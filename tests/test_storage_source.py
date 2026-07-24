"""Regression checks for the Home Assistant Store migration API contract."""

import ast
from pathlib import Path

SOURCE = Path("custom_components/vehicle_maintenance/manager.py").read_text()
TREE = ast.parse(SOURCE)


def test_store_constructor_has_no_unsupported_migration_keyword():
    calls = [node for node in ast.walk(TREE) if isinstance(node, ast.Call)]
    store_calls = [
        node
        for node in calls
        if isinstance(node.func, ast.Name)
        and node.func.id == "VehicleMaintenanceStore"
    ]
    assert store_calls
    assert all(
        keyword.arg != "async_migrate_func"
        for call in store_calls
        for keyword in call.keywords
    )


def test_store_subclass_overrides_supported_migration_hook():
    classes = {
        node.name: node for node in TREE.body if isinstance(node, ast.ClassDef)
    }
    store = classes["VehicleMaintenanceStore"]
    methods = {
        node.name: node
        for node in store.body
        if isinstance(node, ast.AsyncFunctionDef)
    }
    migration = methods["_async_migrate_func"]
    assert [argument.arg for argument in migration.args.args] == [
        "self",
        "old_major_version",
        "old_minor_version",
        "old_data",
    ]

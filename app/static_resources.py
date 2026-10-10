"""Serve the public Python plugin resources with and without a proxy prefix."""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def install_static_resources(app: FastAPI, service_path: str, plugin: str = 'Python', root_alias: bool = True) -> None:
    directory = os.path.join(os.getenv("RESOURCE_DIR", "/app/resources"), f"plugins/{plugin}")
    # Container resources may not exist yet when the application is imported.
    prefixes = ("", service_path.rstrip("/")) if root_alias else (service_path.rstrip("/"),)
    for index, prefix in enumerate(dict.fromkeys(prefixes)):
        app.mount(
            f"{prefix}/static",
            StaticFiles(directory=directory, check_dir=False),
            name=f"{plugin.lower()}-static-{index}",
        )

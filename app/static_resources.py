"""Serve the public Python plugin resources with and without a proxy prefix."""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def install_static_resources(app: FastAPI, service_path: str) -> None:
    directory = os.path.join(os.getenv("RESOURCE_DIR", "/app/resources"), "plugins/Python")
    # Container resources may not exist yet when the application is imported.
    for index, prefix in enumerate(dict.fromkeys(("", service_path.rstrip("/")))):
        app.mount(
            f"{prefix}/static",
            StaticFiles(directory=directory, check_dir=False),
            name=f"python-static-{index}",
        )

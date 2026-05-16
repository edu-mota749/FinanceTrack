"""Vercel entrypoint for the Flask app.

This module resolves the application from common project layouts so the
deployment does not depend on a single hard-coded filename.
"""

from importlib import import_module


_MODULE_CANDIDATES = ("app", "main", "wsgi", "server", "application")
_APP_ATTR_CANDIDATES = ("app", "application")
_FACTORY_ATTR_CANDIDATES = ("create_app", "get_app")


def _load_app():
    last_error = None

    for module_name in _MODULE_CANDIDATES:
        try:
            module = import_module(module_name)
        except Exception as exc:  # pragma: no cover - startup fallback only
            last_error = exc
            continue

        for attribute_name in _APP_ATTR_CANDIDATES:
            app = getattr(module, attribute_name, None)
            if app is not None:
                return app

        for factory_name in _FACTORY_ATTR_CANDIDATES:
            factory = getattr(module, factory_name, None)
            if callable(factory):
                try:
                    app = factory()
                except TypeError:
                    continue
                if app is not None:
                    return app

    raise RuntimeError("Could not locate a Flask app for Vercel deployment") from last_error


app = _load_app()


@app.route("/favicon.ico")
def favicon():
    return "", 204
from app import app


application = app

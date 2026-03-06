"""
UI Blueprint – serves HTML templates.
"""

from __future__ import annotations

from flask import Blueprint, render_template

ui_bp = Blueprint(
    "ui",
    __name__,
    template_folder="../../templates",
    static_folder="../../static",
)


@ui_bp.route("/")
def home() -> str:
    return render_template("index.html")


@ui_bp.route("/dashboard")
def dashboard() -> str:
    return render_template("dashboard.html")

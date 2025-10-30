# app.py

from flask import Flask, render_template, redirect, url_for, send_from_directory
from agent import agent
import os

app = Flask(__name__)

LATEST_SUMMARY = None

@app.route("/")
def dashboard():
    global LATEST_SUMMARY

    screenshots = []
    for name in ["calendar_today.png", "inbox_unread.png", "weather.png"]:
        path = os.path.join("screenshots", name)
        if os.path.exists(path):
            screenshots.append(name)

    return render_template(
        "dashboard.html",
        summary=LATEST_SUMMARY,
        screenshots=screenshots
    )

@app.route("/run")
def run_agent():
    global LATEST_SUMMARY

    # UPDATED LINE HERE:
    final_summary, _ = agent.run_day_plan()

    LATEST_SUMMARY = final_summary
    return redirect(url_for("dashboard"))

@app.route("/screenshots/<path:filename>")
def serve_screenshot(filename):
    return send_from_directory("screenshots", filename)

if __name__ == "__main__":
    os.makedirs("screenshots", exist_ok=True)
    # NOTE: you're on mac and port 5000 is taken -> use 5001 or 5050
    app.run(host="0.0.0.0", port=5001, debug=True)

# agent.py

from web_automation import WebAutomation

def summarize_with_llm(raw_text: str) -> str:
    """
    Build a daily briefing for TODAY.
    - Collect all meetings scraped from Calendar
    - Collect all unread emails scraped from Inbox
    - Capture today's weather
    - Produce a short action plan at the bottom
    """

    lines = raw_text.splitlines()

    calendar_meetings = []
    unread_emails = []
    weather_line = None

    section = None

    for line in lines:
        stripped = line.strip()

        # figure out which block we're parsing
        if stripped.startswith("CALENDAR"):
            section = "cal"
            continue
        if stripped.startswith("INBOX"):
            section = "inbox"
            continue
        if stripped.startswith("WEATHER"):
            section = "weather"
            continue

        # collect calendar events
        # our capture code adds lines like "- 9:30 AM – Standup ..."
        if section == "cal" and stripped.startswith("- "):
            calendar_meetings.append(stripped[2:])  # drop "- "

        # collect unread emails (sender: subject)
        if section == "inbox" and stripped.startswith("- "):
            unread_emails.append(stripped[2:])  # drop "- "

        # collect weather
        if section == "weather" and stripped.startswith("- "):
            weather_line = stripped[2:]

    # fallbacks for safety
    if not calendar_meetings:
        calendar_meetings = ["(No meetings detected today — see calendar_today.png)"]

    if not unread_emails:
        unread_emails = ["(No unread emails detected — see inbox_unread.png)"]

    if not weather_line:
        weather_line = "(No weather data — see weather.png)"

    # try to guess priority for action plan
    first_meeting = calendar_meetings[0] if calendar_meetings else "No meetings"

    urgent_like = []
    for subj in unread_emails:
        lower = subj.lower()
        if any(word in lower for word in ["urgent", "asap", "today", "approval", "invoice", "security", "deadline"]):
            urgent_like.append(subj)

    # compose final output
    out = []

    out.append("Here's your day (today):\n")

    # meetings section
    out.append("MEETINGS TODAY:")
    for m in calendar_meetings:
        out.append(f"  • {m}")
    out.append("")

    # unread email section
    out.append("UNREAD EMAILS:")
    for e in unread_emails:
        out.append(f"  • {e}")
    out.append("")

    # weather section
    out.append("WEATHER:")
    out.append(f"  • {weather_line}")
    out.append("")

    # action plan section
    out.append("ACTION PLAN:")
    out.append(f"  • First meeting: {first_meeting}")
    if urgent_like:
        out.append("  • Emails to handle first:")
        for u in urgent_like:
            out.append(f"    - {u}")
    else:
        out.append("  • No urgent-looking emails flagged.")
    out.append("  • Prep, join first meeting on time, then clear priority emails.")
    out.append("")

    out.append("Screenshots are below for full context (Calendar, Inbox, Weather).")

    return "\n".join(out)


class DayPlannerAgent:
    def run_day_plan(self):
        wa = WebAutomation()
        raw_report = wa.plan_day_capture()  # browser scrape: calendar, inbox, weather
        final_summary = summarize_with_llm(raw_report)
        return final_summary, raw_report


agent = DayPlannerAgent()

import os
import time
from playwright.sync_api import sync_playwright
from urllib.parse import quote


class WebAutomation:
    def __init__(self):
        self.playwright = None
        self.context = None   # persistent browser context
        self.page = None      # single tab we keep reusing

    def open_browser(self):
        """
        Launch (or reuse) a persistent Chrome session.
        This keeps you logged into Gmail / Calendar between runs.
        """
        # Start Playwright
        if self.playwright is None:
            self.playwright = sync_playwright().start()

        # Launch a persistent Chrome profile (saves cookies, login, etc.)
        if self.context is None:
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir="chrome-profile",  # folder saved locally
                headless=False,                  # we WANT to see Chrome
                channel="chrome",                # use system Chrome, not stock Chromium
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            )

        # Reuse a single tab/page
        if self.page is None:
            self.page = self.context.new_page()

        return "Browser opened with persistent Chrome profile."

    def close_browser(self):
        """
        We intentionally do NOT close the browser after each run.
        Leaving Chrome open keeps you logged in.
        """
        # If you ever want to cleanly shut it down each run, uncomment below:
        #
        # try:
        #     if self.context:
        #         self.context.close()
        # except:
        #     pass
        # try:
        #     if self.playwright:
        #         self.playwright.stop()
        # except:
        #     pass
        #
        # self.context = None
        # self.page = None
        # self.playwright = None

        return "Browser left open (not closed)."

    # ---------------------------------
    # utilities
    # ---------------------------------

    def _ensure_screenshots_dir(self):
        os.makedirs("screenshots", exist_ok=True)

    def _shot(self, filename: str):
        """
        Screenshot the current page to screenshots/<filename>.
        """
        self._ensure_screenshots_dir()
        path = os.path.join("screenshots", filename)

        if self.page is None:
            raise RuntimeError("Tried to screenshot but self.page is None")

        self.page.screenshot(path=path, full_page=True)
        return path

    # ---------------------------------
    # calendar capture (UPDATED)
    # ---------------------------------

    def capture_calendar(self) -> str:
        """
        Open Google Calendar in *Day view*, screenshot it,
        and extract each real event (time + title) for TODAY.

        We ignore junk calendars like "Birthdays", "Tasks",
        "Holidays in Australia".

        Returns a block like:

        CALENDAR (today)
        - 9:30am – AI Standup – ConnectOnion Agent
        - 4:00pm – Product Review: Personal Day Assistant demo
        """

        # Make sure browser/page exist
        self.open_browser()

        # Force Calendar into day view for today's date
        # /r/day loads "today" for the active account
        self.page.goto("https://calendar.google.com/calendar/u/0/r/day", timeout=60000)
        time.sleep(2)

        # Screenshot the calendar for the dashboard grid
        self._shot("calendar_today.png")

        # Now pull each event block.
        # In Calendar day view, actual events are buttons with data-eventid.
        event_locators = self.page.locator('[role="button"][data-eventid]')

        events = []
        count = event_locators.count()

        for i in range(count):
            try:
                raw_text = event_locators.nth(i).inner_text(timeout=2000).strip()
            except Exception:
                continue

            # raw_text often looks like:
            # "9:30am\nAI Standup – ConnectOnion Agent\nNo location"
            # We'll clean it into "9:30am – AI Standup – ConnectOnion Agent"

            lines = [x.strip() for x in raw_text.splitlines() if x.strip()]
            # lines might be:
            # ["9:30am", "AI Standup – ConnectOnion Agent", "No location"]

            if len(lines) >= 2:
                time_candidate = lines[0]
                title_candidate = lines[1]

                junk_titles = [
                    "birthdays",
                    "holidays in australia",
                    "tasks",
                    "reminders",
                    "to-do",
                ]

                # Skip pure junk calendars
                if title_candidate.lower() in junk_titles:
                    continue

                pretty = f"{time_candidate} – {title_candidate}"
                events.append(pretty)
            else:
                # fallback: collapse whatever we got
                joined = " ".join(lines)
                if joined:
                    low = joined.lower()
                    if low not in ["birthdays", "holidays in australia", "tasks", "reminders", "to-do"]:
                        events.append(joined)

        # Deduplicate in case Calendar repeated an element
        deduped = []
        seen = set()
        for ev in events:
            key = ev.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(ev)

        if not deduped:
            deduped = ["(No meetings detected today — see screenshot calendar_today.png)"]

        # Build output block in the exact format summarize_with_llm() expects
        cal_lines = ["CALENDAR (today)"]
        for ev in deduped:
            cal_lines.append(f"- {ev}")

        return "\n".join(cal_lines)

    # ---------------------------------
    # inbox capture (unchanged logic, but good already)
    # ---------------------------------

    def capture_inbox(self) -> str:
        """
        Go to Gmail inbox, screenshot it,
        and pull the top unread emails (sender + subject).
        """

        self.open_browser()

        # Go to unread inbox view of account #0
        self.page.goto("https://mail.google.com/mail/u/0/#inbox", timeout=60000)
        time.sleep(4)

        # Screenshot Gmail for dashboard display
        self._shot("inbox_unread.png")

        unread_lines = []
        try:
            # Gmail marks unread rows with class 'zA zE'
            rows = self.page.locator('tr.zA.zE').all()
            for row in rows[:5]:  # grab first ~5 unread
                sender = ""
                subject = ""
                try:
                    # sender name
                    sender = row.locator("span.zF, span.yX.xY").first.inner_text().strip()
                except:
                    pass
                try:
                    # subject line
                    subject = row.locator("span.bog").first.inner_text().strip()
                except:
                    pass

                if sender or subject:
                    unread_lines.append(f"{sender}: {subject}")
        except:
            pass

        if not unread_lines:
            unread_lines = ["(No unread email text captured — see screenshot inbox_unread.png)"]

        out_lines = ["INBOX"]
        for line in unread_lines:
            out_lines.append(f"- {line}")

        return "\n".join(out_lines)

    # ---------------------------------
    # weather capture (unchanged logic, but solid)
    # ---------------------------------

    def capture_weather(self) -> str:
        """
        Google 'weather today', screenshot it,
        and pull today's temp + condition.
        """

        self.open_browser()

        query = quote("weather today")
        self.page.goto(f"https://www.google.com/search?q={query}", timeout=60000)
        time.sleep(3)

        self._shot("weather.png")

        temp_text = ""
        cond_text = ""
        try:
            temp_node = self.page.locator("span#wob_tm").first
            cond_node = self.page.locator("span#wob_dc").first
            temp_text = temp_node.inner_text().strip()
            cond_text = cond_node.inner_text().strip()
        except:
            pass

        if temp_text or cond_text:
            wsummary = f"{temp_text}°C, {cond_text}"
        else:
            wsummary = "(Weather parse failed — see screenshot weather.png)"

        return "WEATHER\n- " + wsummary

    # ---------------------------------
    # high level capture (unchanged shape)
    # ---------------------------------

    def plan_day_capture(self) -> str:
        """
        1. Calendar (today's meetings)
        2. Inbox (unread emails now)
        3. Weather (today)
        Returns a combined text report the agent will summarize.
        Browser stays open (= stays logged in).
        """

        cal_block = self.capture_calendar()
        inbox_block = self.capture_inbox()
        weather_block = self.capture_weather()

        combined = f"{cal_block}\n\n{inbox_block}\n\n{weather_block}\n"
        return combined

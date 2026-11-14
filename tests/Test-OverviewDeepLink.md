# Test: Overview card deep links

Clicking a detector card on the Overview page opens that detector on the Smoke Detectors page:

| Card | Link | Result |
|------|------|--------|
| normal | `/gateway/smoke-detectors?details=<id>` | Device Details dialog |
| alarming | `/gateway/smoke-detectors?alarmlog=<id>` | Alarm Log dialog |

The parameter is removed from the URL right after the dialog opens. Non-admin users see plain, non-clickable cards.

## Automated (no hardware needed)

The test drives the production UI build against a small mock backend that serves
`tests/test-data-overview-card-states.json` (covers healthy, warning, and alarming cards).

```bash
cd interface && npm install --no-package-lock && npm run build && cd ..
node tests/mock-ui-server.mjs interface/build tests/test-data-overview-card-states.json 4173 &
pip install playwright            # needs a Chrome/Chromium; set GG_CHROME=/path/to/chrome if not bundled
python3 tests/test_overview_deeplink.py   # GG_UI_URL overrides http://localhost:4173
```

Covered: link targets per card state, details/alarm-log dialogs open for the clicked detector,
exactly one dialog opens, the parameter is stripped, reload and back do not reopen it, unknown id
and alarm-log-without-alarms fall back sensibly, plain visits open nothing, non-admin cards are
not links, mobile viewport.

## Manual (real device)

1. Open the Overview with at least one healthy and one alarming (or test-imported) detector.
2. Click a healthy card: the Smoke Detectors list opens with the **Device Details** dialog of exactly that detector.
3. Close the dialog and reload the page: no dialog reopens, the URL has no `?details=`.
4. Click the alarming card: the **Alarm Log** of that detector opens.
5. Log in as a non-admin user: cards are shown but are not clickable.

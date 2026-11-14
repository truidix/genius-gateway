"""Browser tests for the Overview card deep links (?details=<id> / ?alarmlog=<id>).

See tests/Test-OverviewDeepLink.md for how to run them against tests/mock-ui-server.mjs.
"""
import os, sys
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('GG_UI_URL', 'http://localhost:4173')
CHROME = os.environ.get('GG_CHROME')  # optional path to a Chrome/Chromium binary
HEALTHY, ALARMING, NO_ALARMS_ID = 1700000001, 1700000006, 1700000002
def login(ctx, admin=True):
    ctx.add_init_script("localStorage.setItem('user', JSON.stringify({bearer_token:'t', username:'u', admin:%s}))" % ('true' if admin else 'false'))

results = []
def check(name, fn):
    try: fn(); results.append((name, True, ''))
    except Exception as e: results.append((name, False, str(e).splitlines()[0][:200]))

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])

    def new_page(admin=True):
        ctx = b.new_context(viewport={'width':1280,'height':900}); login(ctx, admin)
        pg = ctx.new_page(); return ctx, pg

    def t_card_links():
        ctx, pg = new_page(); pg.goto(BASE + '/'); pg.wait_for_selector('a[href*="smoke-detectors?"]')
        hrefs = sorted(a.get_attribute('href') for a in pg.query_selector_all('a[href*="smoke-detectors?"]'))
        assert len(hrefs) == 6, hrefs
        assert f'/gateway/smoke-detectors?alarmlog={ALARMING}' in hrefs
        assert f'/gateway/smoke-detectors?details={HEALTHY}' in hrefs
        assert sum('alarmlog' in h for h in hrefs) == 1, 'only the alarming card may use alarmlog'
        ctx.close()
    check('overview: normal cards -> details, alarming card -> alarmlog', t_card_links)

    def t_click_details():
        ctx, pg = new_page(); pg.goto(BASE + '/'); pg.wait_for_selector('a[href*="smoke-detectors?"]')
        pg.click(f'a[href$="details={HEALTHY}"]')
        expect(pg.get_by_text('Device Details').first).to_be_visible(timeout=8000)
        expect(pg.get_by_text('Test 1 - Healthy').locator('visible=true').first).to_be_visible()
        assert 'details=' not in pg.url and pg.url.endswith('/gateway/smoke-detectors'), pg.url
        ctx.close()
    check('click normal card -> Device Details dialog of that detector, param stripped', t_click_details)

    def t_click_alarm():
        ctx, pg = new_page(); pg.goto(BASE + '/'); pg.wait_for_selector('a[href*="smoke-detectors?"]')
        pg.click(f'a[href$="alarmlog={ALARMING}"]')
        expect(pg.get_by_text('Alarms log').first).to_be_visible(timeout=8000)
        assert 'alarmlog=' not in pg.url, pg.url
        ctx.close()
    check('click alarming card -> Alarm Log dialog', t_click_alarm)

    def t_reload_and_back():
        ctx, pg = new_page(); pg.goto(BASE + '/'); pg.wait_for_selector('a[href*="smoke-detectors?"]')
        pg.click(f'a[href$="details={HEALTHY}"]'); expect(pg.get_by_text('Device Details').first).to_be_visible(timeout=8000)
        pg.reload(); expect(pg.get_by_text('Test 1 - Healthy').locator('visible=true').first).to_be_visible(timeout=8000)
        assert pg.get_by_text('Device Details').count() == 0, 'dialog reopened after reload'
        ctx.close()
    check('reload does not reopen the dialog', t_reload_and_back)

    def t_unknown_id():
        ctx, pg = new_page(); pg.goto(BASE + '/gateway/smoke-detectors?details=999'); expect(pg.get_by_text('Test 1 - Healthy').locator('visible=true').first).to_be_visible(timeout=8000)
        assert pg.get_by_text('Device Details').count() == 0
        assert 'details=' not in pg.url, pg.url
        ctx.close()
    check('unknown id -> plain list, param stripped, no dialog', t_unknown_id)

    def t_alarmlog_without_alarms():
        ctx, pg = new_page(); pg.goto(BASE + f'/gateway/smoke-detectors?alarmlog={NO_ALARMS_ID}')
        expect(pg.get_by_text('Device Details').first).to_be_visible(timeout=8000)
        ctx.close()
    check('alarmlog for device without alarms falls back to Device Details', t_alarmlog_without_alarms)

    def t_plain_visit():
        ctx, pg = new_page(); pg.goto(BASE + '/gateway/smoke-detectors'); expect(pg.get_by_text('Test 1 - Healthy').locator('visible=true').first).to_be_visible(timeout=8000)
        assert pg.get_by_text('Device Details').count() == 0 and pg.get_by_text('Alarms log').count() == 0
        ctx.close()
    check('plain visit to list opens no dialog (regression)', t_plain_visit)

    def t_non_admin():
        ctx, pg = new_page(admin=False); pg.goto(BASE + '/'); expect(pg.get_by_text('Test 1 - Healthy').locator('visible=true').first).to_be_visible(timeout=8000)
        assert len(pg.query_selector_all('a[href*="smoke-detectors?"]')) == 0, 'non-admin cards must not be links'
        ctx.close()
    check('non-admin: cards are not links', t_non_admin)

    def t_mobile():
        ctx = b.new_context(viewport={'width':390,'height':800}); login(ctx)
        pg = ctx.new_page(); pg.goto(BASE + '/'); pg.wait_for_selector('a[href*="smoke-detectors?"]')
        pg.click(f'a[href$="details={HEALTHY}"]'); expect(pg.get_by_text('Device Details').first).to_be_visible(timeout=8000)
        ctx.close()
    check('mobile viewport: card click opens details', t_mobile)

    def t_single_dialog_and_back():
        ctx, pg = new_page(); pg.goto(BASE + '/'); pg.wait_for_selector('a[href*="smoke-detectors?"]')
        pg.click(f'a[href$="details={HEALTHY}"]'); expect(pg.get_by_text('Device Details').first).to_be_visible(timeout=8000)
        pg.wait_for_timeout(1500)
        assert pg.get_by_text('Device Details').count() == 1, f'expected exactly one dialog, got {pg.get_by_text("Device Details").count()}'
        pg.locator('button:visible', has_text='Close').first.click(timeout=5000); expect(pg.get_by_text('Device Details')).to_have_count(0, timeout=5000)
        pg.go_back(); pg.wait_for_timeout(1500); assert pg.url.rstrip('/') == BASE, pg.url
        assert pg.get_by_text('Device Details').count() == 0, 'back navigation reopened a dialog'
        ctx.close()
    check('exactly one dialog opens; back button does not reopen it', t_single_dialog_and_back)

    b.close()

for n, ok, msg in results: print(('PASS ' if ok else 'FAIL ') + n + (('  -> ' + msg) if msg else ''))
sys.exit(0 if all(ok for _, ok, _ in results) else 1)

"""Browser demo: receptionist onboarding followed by patient portal login.

Run from the ``phase2`` directory after starting Django, for example:

    python manage.py runserver 127.0.0.1:8000
    python playwright_bd_patient_workflow.py

Install the Python browser dependency once if needed:
    pip install playwright
    playwright install chromium

Set ``EYESPHERE_BASE_URL`` to test a deployed site. The script uses a unique
mobile number on every run and prints the generated Patient ID and password.
Set ``EYESPHERE_TYPE_DELAY_MS`` or ``EYESPHERE_SLOW_MO_MS`` to adjust the demo speed.
"""

import os
import re
import time
from playwright.sync_api import Page, expect, sync_playwright


BASE_URL = os.getenv("EYESPHERE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TYPE_DELAY_MS = int(os.getenv("EYESPHERE_TYPE_DELAY_MS", "120"))
SLOW_MO_MS = int(os.getenv("EYESPHERE_SLOW_MO_MS", "450"))


def type_text(page: Page, selector: str, value: str) -> None:
    """Type into a field slowly enough for a live client demonstration."""
    page.locator(selector).press_sequentially(value, delay=TYPE_DELAY_MS)


def choose_risk_answers(page: Page) -> None:
    page.locator('input[name="age"][value="a35"]').check()
    for question in ("htn", "thyroid", "fh", "steroid", "checkup", "smoke", "alcohol"):
        page.locator(f'input[name="{question}"][value="0"]').check()
    page.locator('input[name="dm"][value="6"]').check()
    page.locator('input[name="dm5"][value="0"]').check()
    page.locator('input[name="specs"][value="2"]').check()
    page.locator('input[name="specspow"][value="0"]').check()
    page.locator('input[name="hba1c"][value="no"]').check()
    page.locator('input[name="blur"][value="both"]').check()
    page.locator('input[name="screen"][value="h48"]').check()
    page.locator('input[name="activity"][value="yes"]').check()


def main() -> None:
    suffix = str(int(time.time() * 1000))[-8:]
    patient = {
        "name": f"Playwright Demo Patient {suffix}",
        "mobile": f"9{suffix}",
        "email": f"playwright.{suffix}@example.test",
        "location": "Metro City Center",
        "address": "789 Healthcare Avenue, Metro City",
        "booking_code": f"PW-{suffix}",
        "booking_date": "2026-09-02",
        "booking_time": "11:30",
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=SLOW_MO_MS)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            # Receptionist enters the BD onboarding form.
            page.goto(f"{BASE_URL}/patient/onboard/")
            type_text(page, "#p_name", patient["name"])
            type_text(page, "#p_mobile", patient["mobile"])
            type_text(page, "#p_email", patient["email"])
            page.locator("#p_loc").select_option("other")
            type_text(page, "#p_loc_other", patient["location"])
            choose_risk_answers(page)

            # Choose a screening and complete the booking details.
            page.locator('.tab[data-p="book"]').click()
            expect(page.locator("#p_book")).to_be_visible()
            page.locator("#pkgpick input, #testlist input").first.check()
            page.locator('.tab[data-p="booking"]').click()
            type_text(page, "#bk_name", patient["name"])
            type_text(page, "#bk_phone", patient["mobile"])
            type_text(page, "#bk_age", "42")
            type_text(page, "#bk_addr", patient["address"])
            page.locator("#bk_date").fill(patient["booking_date"])
            page.locator("#bk_time").fill(patient["booking_time"])
            page.locator("#bk_consent").check()
            type_text(page, "#bk_total", "1999")
            generated_booking_code = page.locator("#bk_code").input_value()
            assert generated_booking_code

            page.locator('.tab[data-p="book"]').click()
            page.get_by_role("button", name=re.compile(r"Save\s*&\s*book")).click()
            modal = page.locator("#onboard_success_modal")
            expect(modal).to_be_visible()

            credentials_text = modal.text_content() or ""
            patient_id_match = re.search(r"Patient ID:\s*(ES-\d+)", credentials_text)
            password_match = re.search(r"System Generated Password:\s*(ES@[A-Za-z0-9]{10,})", credentials_text)
            patient_id = patient_id_match.group(1) if patient_id_match else None
            password = password_match.group(1) if password_match else None
            assert patient_id and patient_id.startswith("ES-")
            assert password and re.fullmatch(r"ES@[A-Za-z0-9]{10,}", password)

            print(f"Generated Patient ID: {patient_id}")
            print(f"Generated Password: {password}")

            # Patient uses the generated Patient ID and password to sign in.
            page.goto(f"{BASE_URL}/patient/api/login/")
            type_text(page, "#phone_number", patient_id)
            type_text(page, "#password", password)
            page.locator("#loginBtn").click()
            page.wait_for_url(re.compile(r"/patient/?$"))

            expect(page.locator("body")).to_contain_text(patient["name"])
            page.locator('[data-tab="patient"]').click()
            summary = page.locator('[data-testid="bd-onboarding-summary"]')
            expect(summary).to_be_visible()

            # Confirm the persisted BD details are visible to the patient.
            expect(summary.locator('[data-testid="patient-location"]')).to_have_text(patient["location"])
            expect(summary.locator('[data-testid="risk-band"]')).to_contain_text("risk")
            expect(summary.locator('[data-testid="factor-diabetes"]')).to_have_text("Yes")
            expect(summary.locator('[data-testid="factor-hypertension"]')).to_have_text("No")
            expect(summary.locator('[data-testid="factor-blurred-vision"]')).to_have_text("both")
            expect(summary.locator('[data-testid="factor-screen-time"]')).to_have_text("h48")
            expect(summary.locator('[data-testid="booking-code"]')).to_have_text(generated_booking_code)
            expect(summary.locator('[data-testid="booking-slot"]')).to_contain_text(patient["booking_date"])
            expect(summary.locator('[data-testid="selected-tests"]')).not_to_have_text("Not provided")
            expect(summary.locator('[data-testid="payable-amount"]')).to_contain_text("1999")
            print("PASS: onboarding details and generated credentials were verified in the patient dashboard.")
        finally:
            page.wait_for_timeout(1500)
            browser.close()


if __name__ == "__main__":
    main()
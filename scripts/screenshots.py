"""
Captura screenshots das principais telas do Cuidar+.

Uso:
    python scripts/screenshots.py

Requer:
    pip install playwright
    playwright install chromium

A aplicação deve estar rodando em http://127.0.0.1:5000 com DEBUG=true.
"""

import os
import time

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots")
VIEWPORT = {"width": 1440, "height": 900}


def wait_stable(page, timeout=3000):
    """Aguarda a rede ficar ociosa e um pequeno delay para animações."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    page.wait_for_timeout(400)


def shoot(page, filename, full_page=True):
    path = os.path.join(OUT_DIR, filename)
    wait_stable(page)
    page.screenshot(path=path, full_page=full_page)
    print(f"  ✓  {filename}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"\nSalvando screenshots em: {os.path.abspath(OUT_DIR)}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()

        # ── 1. Login ─────────────────────────────────────────────────────────
        page.goto(f"{BASE_URL}/login")
        wait_stable(page)
        shoot(page, "01_login.png")

        # ── 2. Dashboard (admin via dev-login) ────────────────────────────────
        page.goto(f"{BASE_URL}/dev-login")
        wait_stable(page)
        shoot(page, "02_dashboard_admin.png")

        # ── 3. Gestão de Voluntários ──────────────────────────────────────────
        page.goto(f"{BASE_URL}/users")
        wait_stable(page)
        shoot(page, "03_usuarios.png")

        # ── 4. Controle de Ponto ─────────────────────────────────────────────
        page.goto(f"{BASE_URL}/clock-entries")
        wait_stable(page)
        shoot(page, "04_controle_ponto.png")

        # ── 5. Atividades ─────────────────────────────────────────────────────
        page.goto(f"{BASE_URL}/activities")
        wait_stable(page)
        shoot(page, "05_atividades.png")

        # ── 6. Avisos ─────────────────────────────────────────────────────────
        page.goto(f"{BASE_URL}/announcements")
        wait_stable(page)
        shoot(page, "06_avisos.png")

        # ── 7. Eventos ────────────────────────────────────────────────────────
        page.goto(f"{BASE_URL}/events")
        wait_stable(page)
        shoot(page, "07_eventos.png")

        # ── 8. Candidatos (intenções) ─────────────────────────────────────────
        page.goto(f"{BASE_URL}/intencoes")
        wait_stable(page)
        shoot(page, "08_candidatos.png")

        # ── 9. Escalas ───────────────────────────────────────────────────────
        page.goto(f"{BASE_URL}/schedules")
        wait_stable(page)
        shoot(page, "09_escalas.png")

        # ── 10. Relatórios ────────────────────────────────────────────────────
        page.goto(f"{BASE_URL}/reports")
        wait_stable(page)
        shoot(page, "10_relatorios.png")

        # ── 11. Formulário Público de Intenção ───────────────────────────────
        # Acessa sem sessão para ver a tela pública
        ctx2 = browser.new_context(viewport=VIEWPORT)
        page2 = ctx2.new_page()
        page2.goto(f"{BASE_URL}/intencao")
        wait_stable(page2)
        shoot(page2, "11_intencao_publica.png")
        ctx2.close()

        # ── 12. Dashboard Voluntário (view do voluntário) ─────────────────────
        ctx3 = browser.new_context(viewport=VIEWPORT)
        page3 = ctx3.new_page()
        # login como voluntário
        page3.goto(f"{BASE_URL}/login")
        wait_stable(page3)
        page3.fill('input[name="username"]', 'maria.silva')
        page3.fill('input[name="password"]', 'vol123')
        page3.click('button[type="submit"]')
        wait_stable(page3)
        shoot(page3, "12_dashboard_voluntario.png")
        ctx3.close()

        browser.close()

    print("\n✓ Screenshots concluídos!\n")


if __name__ == "__main__":
    main()

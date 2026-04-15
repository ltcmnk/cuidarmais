"""
Simple smoke test that creates the Flask app in development mode, uses the
dev-login helper to authenticate as admin, and checks that /schedules returns 200
and contains the page title.

Run with the virtualenv Python in the repo root:
    ./.venv/bin/python scripts/smoke_test_schedules.py
"""
from app import create_app


def run():
    app = create_app({'ENV': 'development', 'TESTING': True})
    client = app.test_client()

    # Dev-login is only available in development mode; it will set session as admin
    rv = client.get('/dev-login', follow_redirects=True)
    assert rv.status_code in (200, 302)

    rv = client.get('/schedules')
    if rv.status_code != 200:
        print('FAIL: /schedules returned', rv.status_code)
        print(rv.data.decode('utf-8')[:2000])
        return 2

    body = rv.data.decode('utf-8')
    if 'Escalas' not in body:
        print('FAIL: page did not contain expected title')
        print(body[:2000])
        return 3

    print('OK: /schedules loaded and contains Escalas')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())

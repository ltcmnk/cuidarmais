import os
from app import create_app


if __name__ == '__main__':
    app = create_app()
    # Allow overriding port/host/debug via environment for flexibility in dev
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    debug_env = os.environ.get('DEBUG', None)
    debug = True if debug_env is None else (str(debug_env).lower() in ('1', 'true', 'yes'))
    app.run(debug=debug, host=host, port=port)

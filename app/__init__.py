from flask import Flask
import os

from .models.storage import init_data
from .utils import register_filters


def create_app(config=None):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'), template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))

    # sensible default secret; recommend overriding via env var in deployments
    # If the environment variable exists but is empty, fall back to a safe default.
    default_secret = os.environ.get('SECRET_KEY') or 'trocar-por-variavel-de-ambiente'
    app.config.setdefault('SECRET_KEY', default_secret)
    # MQTT configuration defaults (can be overridden via environment or passed config)
    app.config.setdefault('MQTT_BROKER', os.environ.get('MQTT_BROKER', 'broker.hivemq.com'))
    try:
        app.config.setdefault('MQTT_PORT', int(os.environ.get('MQTT_PORT', '1883')))
    except Exception:
        app.config.setdefault('MQTT_PORT', 1883)
    app.config.setdefault('MQTT_TOPIC', os.environ.get('MQTT_TOPIC', 'hospital/cajuru/ponto'))
    app.config.setdefault('START_MQTT', os.environ.get('START_MQTT', 'True').lower() in ('1', 'true', 'yes'))
    if config:
        app.config.update(config)

    # Ensure the Flask app instance has a secret key for session support.
    # Use config value when present and non-empty; otherwise fallback to a
    # safe default so the session machinery is available in development.
    app.secret_key = app.config.get('SECRET_KEY') or 'trocar-por-variavel-de-ambiente'

    # ensure data file exists
    init_data()

    # register jinja filters/helpers
    register_filters(app)
    # register context processors (session/user helpers used in templates)
    from .utils import register_context_processors
    register_context_processors(app)

    # register blueprints lazily to avoid circular imports here (controllers import storage/utils)
    from .controllers.auth import auth_bp
    from .controllers.users import users_bp
    from .controllers.clock import clock_bp
    from .controllers.activities import activities_bp
    from .controllers.events import events_bp
    from .controllers.announcements import announcements_bp
    from .controllers.reports import reports_bp
    from .controllers.intents import intents_bp
    from .controllers.main import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(clock_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(intents_bp)
    app.register_blueprint(main_bp)

    # Create aliases for legacy endpoints used across templates (avoid changing templates now).
    # For each blueprint, map `<bpname>.<endpoint>` -> `<endpoint>` for a few well-known handlers.
    blueprint_aliases = {
        auth_bp: ['login', 'logout', 'profile', 'register'],
        users_bp: ['users', 'check_username', 'add_user', 'edit_user', 'delete_user', 'export_users', 'register_badge']
    }

    # add clock blueprint aliases
    blueprint_aliases[clock_bp] = ['clock_entries', 'my_clock_entries', 'add_clock_entry', 'toggle_clock_entry']
    # add activities blueprint aliases
    blueprint_aliases[activities_bp] = ['activities', 'add_activity', 'edit_activity', 'delete_activity', 'toggle_activity_completion']
    blueprint_aliases[events_bp] = ['events', 'add_event', 'edit_event']
    blueprint_aliases[announcements_bp] = ['announcements', 'add_announcement', 'delete_announcement', 'edit_announcement']
    blueprint_aliases[reports_bp] = ['reports_index', 'api_dashboard_hours', 'report_hours', 'report_activity_completions', 'export_users']
    blueprint_aliases[intents_bp] = ['submit_intention', 'intents', 'approve_intent', 'delete_intent']
    blueprint_aliases[main_bp] = ['index', 'home', 'dashboard']

    for bp, names in blueprint_aliases.items():
        for name in names:
            bp_endpoint = f"{bp.name}.{name}"
            if bp_endpoint in app.view_functions and name not in app.view_functions:
                for rule in list(app.url_map.iter_rules()):
                    if rule.endpoint == bp_endpoint:
                        view_func = app.view_functions[bp_endpoint]
                        try:
                            app.add_url_rule(rule.rule, endpoint=name, view_func=view_func, methods=rule.methods)
                        except Exception:
                            pass

    # Optionally start MQTT service (if configured)
    try:
        from .services.mqtt_service import MQTTService
        if app.config.get('START_MQTT', True):
            mqtt_svc = MQTTService(app)
            app.extensions = getattr(app, 'extensions', {})
            app.extensions['mqtt_service'] = mqtt_svc
            # start in background
            try:
                mqtt_svc.start()
            except Exception:
                app.logger.exception('Failed to start mqtt service')
    except Exception:
        # If paho-mqtt isn't available or any other error happens, continue without failing app creation
        app.logger.debug('MQTT service not started: %s', True)

    return app

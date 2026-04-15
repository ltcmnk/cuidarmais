import os
import re
import unicodedata
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, abort
from flask import request
from app.models.storage import load_data, ensure_data_keys, activity_assignments


def generate_username(first_name, last_name='', existing_usernames=None):
    if not first_name:
        first_token = 'user'
    else:
        # normalize and strip non-ascii for the first_name field
        fn_norm = unicodedata.normalize('NFKD', first_name).encode('ascii', 'ignore').decode('ascii')
        fn_norm = re.sub(r"[^a-zA-Z0-9 ]+", '', fn_norm).strip().lower()
        first_token = fn_norm.split()[0] if fn_norm.split() else 'user'

    # handle last_name: prefer explicit last_name, otherwise try to infer from first_name
    surname_token = ''
    PREPOSITIONS = {'da', 'de', 'do', 'das', 'dos'}
    if last_name:
        ln_norm = unicodedata.normalize('NFKD', last_name).encode('ascii', 'ignore').decode('ascii')
        ln_norm = re.sub(r"[^a-zA-Z0-9 ]+", '', ln_norm).strip().lower()
        ln_parts = ln_norm.split() if ln_norm else []
        if ln_parts:
            # if the first token is a common Portuguese preposition (e.g. 'da', 'de', 'do'),
            # prefer the last token as the surname (e.g. 'da Silva' -> use 'silva')
            if ln_parts[0] in PREPOSITIONS and len(ln_parts) > 1:
                surname_token = ln_parts[-1]
            else:
                # otherwise use the first token of the provided surname
                surname_token = ln_parts[0]
    else:
        # if first_name contained multiple tokens, use its last token as surname
        if first_name and len(first_name.split()) > 1:
            parts = unicodedata.normalize('NFKD', first_name).encode('ascii', 'ignore').decode('ascii')
            parts = re.sub(r"[^a-zA-Z0-9 ]+", '', parts).strip().lower().split()
            if len(parts) > 1:
                # take the last token as surname
                surname_token = parts[-1]

    if existing_usernames is None:
        existing_usernames = set()

    base = f"{first_token}.{surname_token}" if surname_token else first_token
    candidate = base
    suffix = 0
    while candidate in existing_usernames:
        suffix += 1
        candidate = f"{base}{suffix}"

    return candidate


def default_password_from_cpf(cpf: str) -> str:
    if not cpf:
        return ''
    digits = re.sub(r'\D', '', cpf)
    if len(digits) >= 4:
        return digits[-4:]
    return digits


def log_action(user_id, action, details=None):
    try:
        entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': action,
            'details': details or {}
        }
        with open('audit.log', 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def format_date_time(value):
    if not value:
        return ''
    try:
        if 'T' in value:
            dt = datetime.fromisoformat(value)
            return dt.strftime('%d/%m/%Y %H:%M')
        else:
            dt = datetime.fromisoformat(value)
            return dt.strftime('%d/%m/%Y')
    except Exception:
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
        except Exception:
            return value


def format_date_only(value):
    if not value:
        return ''
    try:
        if 'T' in value:
            dt = datetime.fromisoformat(value)
            return dt.strftime('%d/%m/%Y')
        else:
            dt = datetime.fromisoformat(value)
            return dt.strftime('%d/%m/%Y')
    except Exception:
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
        except Exception:
            return value


def format_time_only(value):
    if not value:
        return ''
    try:
        if 'T' in value:
            dt = datetime.fromisoformat(value)
            return dt.strftime('%H:%M')
        else:
            return ''
    except Exception:
        return ''


def register_filters(app):
    app.jinja_env.filters['shortdate'] = format_date_time
    app.jinja_env.filters['dateonly'] = format_date_only
    app.jinja_env.filters['timeonly'] = format_time_only


def register_context_processors(app):
    """Register context processors used by templates (user/session helpers and utility functions)."""
    @app.context_processor
    def inject_user():
        return dict(
            current_user_role=session.get('user_role'),
            current_user_name=session.get('user_name'),
            user_name=session.get('user_name'),
            request_path=request.path,
            is_admin=(session.get('user_role') == 'admin')
        )

    @app.context_processor
    def utility_helpers():
        def get_user_by_id(uid):
            try:
                data = load_data()
                return next((u for u in data.get('users', []) if u.get('id') == uid), None)
            except Exception:
                return None

        def get_user_activities():
            try:
                data = load_data()
                ensure_data_keys(data)
                uid = session.get('user_id')
                acts = []
                for a in data.get('activities', []) or []:
                    ac = a.copy()
                    try:
                        activity_assignments(ac)
                    except Exception:
                        pass
                    assigned_ids = [o.get('user_id') for o in ac.get('assigned_to', []) if not o.get('removed_at')]
                    if uid in assigned_ids:
                        acts.append(ac)
                today = datetime.now().date().isoformat()
                comps = data.get('activity_completions', [])
                for a in acts:
                    a['completed_today'] = any(c for c in comps if c.get('activity_id') == a.get('id') and c.get('user_id') == uid and c.get('date') == today)
                return acts
            except Exception:
                return []

        return dict(get_user_by_id=get_user_by_id, get_user_activities=get_user_activities)


def compute_user_week_seconds(user_id, data=None):
    """Compute total worked seconds for the ISO week containing now for a given user.

    Pairs 'in'/'out' entries are summed. If an 'in' is not closed by an 'out'
    within the week, the open interval is ignored for safety (so users can't
    bypass the weekly cap by leaving an open 'in').
    """
    try:
        from datetime import datetime
        if data is None:
            from app.models.storage import load_data
            data = load_data()

        now = datetime.now()
        this_year, this_week, _ = now.isocalendar()

        entries = [e for e in (data.get('clock_entries') or []) if str(e.get('userId')) == str(user_id)]
        # keep only entries that belong to the same ISO week/year as now
        def in_this_week(ts):
            try:
                dt = datetime.fromisoformat(ts)
                y,w,_ = dt.isocalendar()
                return (y == this_year) and (w == this_week)
            except Exception:
                return False

        entries = [e for e in entries if in_this_week(e.get('timestamp',''))]
        entries = sorted(entries, key=lambda e: e.get('timestamp',''))

        total = 0
        i = 0
        while i < len(entries):
            e = entries[i]
            if e.get('type') == 'in':
                j = i + 1
                while j < len(entries) and entries[j].get('type') != 'out':
                    j += 1
                if j < len(entries):
                    try:
                        t_in = datetime.fromisoformat(e.get('timestamp'))
                        t_out = datetime.fromisoformat(entries[j].get('timestamp'))
                        delta = (t_out - t_in).total_seconds()
                        if delta > 0:
                            total += delta
                    except Exception:
                        pass
                    i = j + 1
                else:
                    # open 'in' without matching 'out' inside the week -- ignore
                    break
            else:
                i += 1
        return int(total)
    except Exception:
        return 0


def login_required(f):
    """Decorator to require a logged-in user (looks for 'user_id' in session).

    Redirects to the legacy 'login' endpoint to preserve compatibility with existing templates.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role; aborts with 403 when unauthorized."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


def is_admin():
    """Convenience helper to check admin role in code/templates."""
    return session.get('user_role') == 'admin'

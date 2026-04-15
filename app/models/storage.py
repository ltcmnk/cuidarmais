import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash

DATA_FILE = os.environ.get('DATA_FILE', os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data.json'))


def init_data():
    # create a default data.json when missing
    if not os.path.exists(DATA_FILE):
        data = {
            'users': [
                {
                    'id': '1',
                    'username': 'admin',
                    'password': generate_password_hash('adm123'),
                    'nome': 'Administrador',
                    'sobrenome': '',
                    'nome_completo': 'Administrador',
                    'email': 'admin@example.com',
                    'role': 'admin',
                    'phone': '',
                    'data_nascimento': '',
                    'createdAt': datetime.now().isoformat()
                }
            ],
            'clock_entries': [],
            'announcements': [],
            'events': [],
            'activities': [],
            'activity_completions': []
        }
        save_data(data)


def load_data():
    if not os.path.exists(DATA_FILE):
        init_data()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    # simple save (note: not safe for concurrent multi-process writes)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_data_keys(data):
    data.setdefault('activities', [])
    data.setdefault('activity_completions', [])
    if not data.get('activities'):
        default_titles = [
            'Atendimento Telefônico',
            'Acolhida no Internamento',
            'Acompanhamento Solidário',
            'Visita Solidária',
            'Acolhimento Espiritual',
            'Acolhimento Familiar - UTIs - HSMC',
            'Acolhimento Familiar - UTIs - HUC',
            'Anjos Solidários'
        ]
        acts = []
        for i, t in enumerate(default_titles, start=1):
            acts.append({'id': f'act_{i}', 'title': t, 'description': '', 'assigned_to': [], 'location': '', 'createdAt': datetime.now().isoformat(), 'default_hours': 1.0, 'hourly_cost': 0.0})
        data['activities'] = acts
        try:
            save_data(data)
        except Exception:
            pass


def activity_assignments(activity):
    if 'assigned_to' not in activity or activity.get('assigned_to') is None:
        activity['assigned_to'] = []
        return activity

    at = activity.get('assigned_to')
    if isinstance(at, list) and at and isinstance(at[0], dict) and at[0].get('user_id'):
        return activity

    new = []
    created = activity.get('createdAt') or datetime.now().isoformat()
    for uid in at:
        new.append({'user_id': uid, 'assigned_at': created, 'removed_at': None})
    activity['assigned_to'] = new
    return activity

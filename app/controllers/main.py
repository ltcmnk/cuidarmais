from flask import Blueprint, redirect, url_for, render_template, session, request, flash
from datetime import datetime, timedelta

from app.models.storage import load_data, ensure_data_keys, activity_assignments
from app.utils import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('login'))


@main_bp.route('/dashboard')
@main_bp.route('/home', endpoint='home')
@login_required
def dashboard():
    data = load_data()
    ensure_data_keys(data)
    total_users = len(data.get('users', []))

    today = datetime.now().date()
    today_entries = [e for e in data.get('clock_entries', []) if datetime.fromisoformat(e.get('timestamp')).date() == today]
    today_in = sum(1 for e in today_entries if e.get('type') == 'in')
    today_out = sum(1 for e in today_entries if e.get('type') == 'out')

    # Announcements
    raw_ann = sorted(data.get('announcements', []), key=lambda a: a.get('createdAt',''), reverse=True)
    announcements = []
    now_dt = datetime.now()
    users_by_id = {u['id']: u for u in data.get('users', [])}
    for a in raw_ann:
        is_new = False
        ca = a.get('createdAt')
        if ca:
            try:
                ca_dt = datetime.fromisoformat(ca)
                if (now_dt - ca_dt).total_seconds() <= 24 * 3600:
                    is_new = True
            except Exception:
                pass
        ann_copy = dict(a)
        ann_copy['is_new'] = is_new
        author_id = a.get('authorId')
        if author_id and author_id in users_by_id:
            u = users_by_id[author_id]
            ann_copy['authorName'] = u.get('nome_completo') or 'Sistema'
        else:
            ann_copy['authorName'] = 'Sistema'
        announcements.append(ann_copy)

    # If there are many announcements, only show a small number on the dashboard
    ANNOUNCEMENTS_DASH_LIMIT = 3
    announcements_total = len(announcements)
    announcements_more = announcements_total > ANNOUNCEMENTS_DASH_LIMIT
    announcements = announcements[:ANNOUNCEMENTS_DASH_LIMIT]

    # Birthdays: compute weekly and today's birthdays (only active users)
    birthdays_week = []
    birthdays_today = []
    # define week range: Monday..Sunday containing today
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    for u in [x for x in data.get('users', []) if x.get('estado_user', 1) != 0]:
        bd = u.get('data_nascimento')
        if bd:
            try:
                bd_dt = datetime.fromisoformat(bd).date()
                # construct this year's birthday date
                try:
                    this_year_bd = bd_dt.replace(year=today.year)
                except Exception:
                    # fallback: if invalid (e.g., Feb 29 on non-leap), skip
                    this_year_bd = None

                display_name = u.get('nome_completo') or ' '.join([(u.get('nome') or '').strip(), (u.get('sobrenome') or '').strip()]).strip()
                if this_year_bd:
                    # If the birthday is today, include only in birthdays_today (happy birthday)
                    is_today = (this_year_bd.month == today.month and this_year_bd.day == today.day)
                    if week_start <= this_year_bd <= week_end and not is_today:
                        birthdays_week.append({'id': u['id'], 'nome_completo': display_name, 'data_nascimento': bd, 'display': bd_dt.strftime('%d/%m')})
                    if is_today:
                        birthdays_today.append({'id': u['id'], 'nome_completo': display_name, 'data_nascimento': bd, 'display': bd_dt.strftime('%d/%m')})
            except Exception:
                pass

    # Events: show upcoming events on dashboard (1.5 weeks window) or important ones
    def parse_sched(e):
        sa = e.get('scheduled_at') or ''
        try:
            if sa:
                return datetime.fromisoformat(sa)
        except Exception:
            pass
        return datetime.max

    now_dt = datetime.now()
    window_end = now_dt + timedelta(days=10, hours=12)  # 1.5 weeks = 10 days 12 hours
    raw_events = data.get('events', [])
    filtered_events = []
    for e in raw_events:
        sa = parse_sched(e)
        important = bool(e.get('important'))
        if important:
            filtered_events.append(e)
            continue
        # include if scheduled_at is within the upcoming 1.5 weeks
        if sa != datetime.max and now_dt <= sa <= window_end:
            filtered_events.append(e)

    # sort: important first, then by scheduled date
    events = sorted(filtered_events, key=lambda ev: (not bool(ev.get('important')), parse_sched(ev)))
    # limit number of events shown in dashboard for brevity (match announcements behavior)
    MAX_DASH_EVENTS = 3
    events_total = len(events)
    events_more = events_total > MAX_DASH_EVENTS
    events = events[:MAX_DASH_EVENTS]

    # Enrich events with author name and formatted createdAt for display
    events_display = []
    for e in events:
        ev_copy = dict(e)
        author_id = e.get('authorId')
        if author_id and author_id in users_by_id:
            ev_copy['authorName'] = users_by_id[author_id].get('nome_completo') or 'Sistema'
        else:
            ev_copy['authorName'] = 'Sistema'
        # format createdAt as dd/mm/yyyy HH:MM
        ca = e.get('createdAt')
        if ca:
            try:
                ca_dt = datetime.fromisoformat(ca)
                ev_copy['createdAt_fmt'] = ca_dt.strftime('%d/%m/%Y %H:%M')
            except Exception:
                ev_copy['createdAt_fmt'] = ca
        else:
            ev_copy['createdAt_fmt'] = ''
        events_display.append(ev_copy)

    # replace events with enriched list for template
    events = events_display

    # Last punch and next quick
    last_punch = None
    next_quick = 'Entrada'
    user_id = session.get('user_id')
    if user_id:
        user_entries = [e for e in data.get('clock_entries', []) if e.get('userId') == user_id]
        if user_entries:
            last_entry = sorted(user_entries, key=lambda e: e.get('timestamp'))[-1]
            try:
                lp = datetime.fromisoformat(last_entry.get('timestamp'))
                last_punch = lp.strftime('%d/%m/%Y %H:%M')
            except Exception:
                last_punch = last_entry.get('timestamp')
            next_quick = 'Saída' if last_entry.get('type') == 'in' else 'Entrada'

    return render_template('dashboard.html',
                           user_name=session.get('user_name'),
                           total_users=total_users,
                           today_entries=len(today_entries),
                           today_in=today_in,
                           today_out=today_out,
                           total_entries=len(data.get('clock_entries', [])),
                           announcements=announcements,
                           announcements_more=announcements_more,
                           announcements_total=announcements_total,
                           birthdays_week=birthdays_week,
                           birthdays_today=birthdays_today,
                           events=events,
                           events_more=events_more,
                           events_total=events_total,
                           last_punch=last_punch,
                           next_quick=next_quick,
                           users=[{'id': u.get('id'), 'nome_completo': (u.get('nome_completo') or u.get('nome',''))} for u in data.get('users', [])])

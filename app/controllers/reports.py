from flask import Blueprint, current_app as app, render_template, request, redirect, url_for, jsonify, flash, session
from datetime import datetime, timedelta
from io import StringIO, BytesIO
import importlib

from app.models.storage import load_data, save_data, ensure_data_keys, activity_assignments
from app.utils import log_action, login_required, admin_required

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@reports_bp.route('/reports', endpoint='reports_index')
@login_required
@admin_required
def reports_index():
    """Simple reports index page with links/forms for CSV exports."""
    data = load_data()
    ensure_data_keys(data)
    users = data.get('users', [])
    activities = data.get('activities', [])
    # active users (exclude deactivated) used for most reports/eligible lists
    active_users = [u for u in users if u.get('estado_user', 1) != 0]
    # Standardize assignment objects for activities so assigned_at is available
    for a in activities:
        try:
            activity_assignments(a)
        except Exception:
            # be defensive: skip if something is malformed
            pass

    # Build eligible volunteers mapping per activity id according to rule:
    # eligible if user is a registered volunteer (role != 'admin') OR
    # appears in activity.assigned_to with assigned_at within last 30 days.
    eligible_by_activity = {}
    now = datetime.now()
    for a in activities:
        act_id = a.get('id')
        eligible = []
        # precompute assigned recent ids
        recent_assigned_ids = set()
        for obj in a.get('assigned_to', []) or []:
            assigned_at = obj.get('assigned_at')
            removed_at = obj.get('removed_at')
            if not assigned_at:
                continue
            try:
                dt = datetime.fromisoformat(assigned_at)
            except Exception:
                continue
            if removed_at:
                # if removed, skip
                continue
            if (now - dt).days <= 30:
                recent_assigned_ids.add(obj.get('user_id'))

        # consider only active users when building eligible lists
        for u in active_users:
            uid = u.get('id')
            is_registered_vol = (u.get('role') != 'admin')
            if is_registered_vol or (uid in recent_assigned_ids):
                display = u.get('nome_completo') or u.get('nome')
                eligible.append({'id': uid, 'display': f"{display} ({u.get('username','')})"})

        eligible_by_activity[act_id] = eligible

    return render_template('reports_index.html', user_name=session.get('user_name'), users=users, activities=activities, eligible_by_activity=eligible_by_activity)


@reports_bp.route('/api/dashboard/hours')
@login_required
@admin_required
def api_dashboard_hours():
    """Return JSON with labels and data for the last 7 days total worked hours (summed across users).

    The algorithm pairs 'in' and next 'out' entries and attributes the worked duration to the day of the 'in' timestamp.
    """
    data = load_data()
    now = datetime.now().date()
    # last 7 days (oldest -> newest)
    days = [now - timedelta(days=i) for i in range(6, -1, -1)]
    labels = [d.strftime('%d/%m') for d in days]
    totals = [0.0 for _ in days]

    entries = sorted(data.get('clock_entries', []), key=lambda e: e.get('timestamp', ''))

    # iterate and pair in->out sequentially
    i = 0
    while i < len(entries):
        e = entries[i]
        if e.get('type') != 'in':
            i += 1
            continue
        # find next out
        j = i + 1
        while j < len(entries) and entries[j].get('type') != 'out':
            j += 1
        if j < len(entries):
            try:
                t_in = datetime.fromisoformat(e.get('timestamp'))
                t_out = datetime.fromisoformat(entries[j].get('timestamp'))
                delta = (t_out - t_in).total_seconds()
                if delta > 0:
                    in_date = t_in.date()
                    for idx, d in enumerate(days):
                        if in_date == d:
                            totals[idx] += delta / 3600.0
                            break
            except Exception:
                pass
            i = j + 1
        else:
            break

    # round to 2 decimals for display
    rounded = [round(x, 2) for x in totals]
    return jsonify({'labels': labels, 'data': rounded})


@reports_bp.route('/reports/hours')
@login_required
@admin_required
def report_hours():
    """Export total worked hours per volunteer as CSV for a date range and optional user filter."""
    data = load_data()
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    user_filter = request.args.get('user_id')

    # reuse compute logic: compute total seconds within range per user
    def in_range(ts):
        if not (start or end):
            return True
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            return False
        if start:
            try:
                sdt = datetime.fromisoformat(start + 'T00:00:00')
            except Exception:
                sdt = None
            if sdt and dt < sdt:
                return False
        if end:
            try:
                edt = datetime.fromisoformat(end + 'T23:59:59')
            except Exception:
                edt = None
            if edt and dt > edt:
                return False
        return True

    # map only active users for hours report
    users = {u['id']: u for u in data.get('users', []) if u.get('estado_user', 1) != 0}
    entries = [e for e in data.get('clock_entries', []) if in_range(e.get('timestamp',''))]
    if user_filter:
        entries = [e for e in entries if e.get('userId') == user_filter]

    # group entries by user and sort by timestamp
    by_user = {}
    for e in sorted(entries, key=lambda x: x.get('timestamp','')):
        uid = e.get('userId')
        by_user.setdefault(uid, []).append(e)

    # compute total seconds per user by pairing in/out inside the filtered range
    rows = []
    for uid, user_entries in by_user.items():
        # skip users who are deactivated (only consider active users mapped above)
        if uid not in users:
            continue
        total = 0
        i = 0
        while i < len(user_entries):
            e = user_entries[i]
            if e.get('type') == 'in':
                j = i + 1
                while j < len(user_entries) and user_entries[j].get('type') != 'out':
                    j += 1
                if j < len(user_entries):
                    try:
                        t_in = datetime.fromisoformat(e.get('timestamp'))
                        t_out = datetime.fromisoformat(user_entries[j].get('timestamp'))
                        delta = (t_out - t_in).total_seconds()
                        if delta > 0:
                            total += delta
                    except Exception:
                        pass
                    i = j + 1
                else:
                    break
            else:
                i += 1

        hrs = int(total // 3600)
        mins = int((total % 3600) // 60)
    u = users.get(uid, {})
    display = (u.get('nome_completo') or u.get('nome'))
    rows.append({'id': uid, 'username': u.get('username',''), 'nome': display, 'hours': hrs, 'minutes': mins, 'hours_str': f"{hrs}h {mins}m"})

    # support CSV and PDF output
    fmt = request.args.get('format') or request.args.get('output')
    import csv
    from io import StringIO
    if fmt == 'pdf':
        # PDF export removed — inform user and redirect to reports index
        flash('Exportação em PDF foi removida desta instalação. Use CSV ou relatório em tela.', 'error')
        return redirect(url_for('reports_index'))

    # default: CSV
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Usuário','Nome','Horas Trabalhadas'])
    for r in rows:
        writer.writerow([r['username'], r['nome'], r['hours_str']])

    output = si.getvalue()
    return app.response_class(output, mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename="hours_report.csv"'
    })


@reports_bp.route('/reports/activity-completions')
@login_required
@admin_required
def report_activity_completions():
    """Export activity completions as CSV. Optional query params: start_date, end_date (YYYY-MM-DD), activity_id"""
    data = load_data()
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    activity_id = request.args.get('activity_id')

    comps = data.get('activity_completions', [])
    # only consider active users when exporting activity completions
    users = {u['id']: u for u in data.get('users', []) if u.get('estado_user', 1) != 0}
    acts = {a['id']: a for a in data.get('activities', [])}

    def in_range(c):
        d = c.get('date')
        if not d:
            return False
        if start and d < start:
            return False
        if end and d > end:
            return False
        return True

    filtered = [c for c in comps if in_range(c)]
    if activity_id:
        filtered = [c for c in filtered if c.get('activity_id') == activity_id]

    # Only consider completions that have an associated 'entrada' (clock-in) on the same date.
    # This avoids counting rows where the user only has a 'saida' on that date.
    clock_entries = data.get('clock_entries', [])
    def _has_clock_in_for(user_id, date_str):
        if not user_id or not date_str:
            return False
        for e in clock_entries:
            if e.get('userId') == user_id:
                ts = (e.get('timestamp') or '')[:10]
                if ts == date_str and (e.get('type') == 'in' or e.get('type') == 'entrada'):
                    return True
        return False

    filtered = [c for c in filtered if _has_clock_in_for(c.get('user_id'), c.get('date'))]

    include_value = request.args.get('include_value') in ('1','true','on')
    import csv
    from io import StringIO
    si = StringIO()
    writer = csv.writer(si)
    header = ['ID Atividade','Nome Atividade','ID Usuário','Nome Usuário','Data','Concluído Em']
    if include_value:
        header.append('Valor economizado (R$)')
    writer.writerow(header)
    # filter out completions by deactivated users
    filtered = [c for c in filtered if users.get(c.get('user_id'))]

    total_value = 0.0
    for c in sorted(filtered, key=lambda x: x.get('createdAt','')):
        aid = c.get('activity_id')
        uid = c.get('user_id')
        row = [aid, acts.get(aid, {}).get('title',''), uid, (users.get(uid, {}).get('nome_completo') or users.get(uid, {}).get('nome')), c.get('date',''), c.get('createdAt','')]
        if include_value:
            act = acts.get(aid, {})
            try:
                hrs = float(act.get('default_hours', 0) or 0)
                rate = float(act.get('hourly_cost', 0) or 0)
                value = round(hrs * rate, 2)
            except Exception:
                value = 0.0
            row.append(f"{value:.2f}")
            total_value += value
        writer.writerow(row)

    if include_value:
        # append a summary row with total value
        writer.writerow([])
        writer.writerow(['', '', '', '', 'Total valor economizado (R$):', f"{total_value:.2f}"])
    output = si.getvalue()
    try:
        log_action(session.get('user_id'), 'export_activity_completions', {'activity_id': activity_id, 'start': start, 'end': end})
    except Exception:
        pass

    return app.response_class(output, mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename="activity_completions.csv"'
    })


@reports_bp.route('/export/users')
@login_required
@admin_required
def export_users():
    """Export all users as CSV (id,username,nome,email,role,department,cpf,createdAt)."""
    data = load_data()
    si = StringIO()
    import csv
    writer = csv.writer(si)
    writer.writerow(['ID Usuário', 'Usuário', 'Nome', 'E-mail', 'Função', 'CPF', 'Data de Criação'])
    for u in data.get('users', []):
        writer.writerow([
            u.get('id',''),
            u.get('username',''),
            (u.get('nome_completo') or u.get('nome')),
            u.get('email',''),
            u.get('role',''),
            u.get('cpf',''),
            u.get('createdAt','')
        ])
    output = si.getvalue()
    # audit
    try:
        log_action(session.get('user_id'), 'export_users_csv', {'count': len(data.get('users', []))})
    except Exception:
        pass
    return app.response_class(output, mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename="users.csv"'
    })

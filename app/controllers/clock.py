from flask import Blueprint, current_app as app, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
from io import StringIO, BytesIO
import importlib

from app.models.storage import load_data, save_data, ensure_data_keys
from app.utils import log_action, login_required, admin_required, compute_user_week_seconds

clock_bp = Blueprint('clock', __name__)


@clock_bp.route('/clock-entries')
@clock_bp.route('/clock-entries', endpoint='clock_entries')
@clock_bp.route('/clock-entries')
@login_required
@admin_required
def clock_entries():
    data = load_data()

    # Allow filtering by date range via query params (YYYY-MM-DD)
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    q = (request.args.get('q') or '').strip().lower()
    user_filter = request.args.get('user_id')
    # Optional filter: type of clock entry ('in' for Entrada, 'out' for Saída)
    type_filter = request.args.get('type')

    entries = data.get('clock_entries', [])[:]

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

    filtered = [e for e in entries if in_range(e.get('timestamp',''))]

    # If user_id provided, filter to that user's entries
    if user_filter:
        filtered = [e for e in filtered if e.get('userId') == user_filter]

    # If type filter provided ('in' or 'out'), filter by entry type
    if type_filter:
        tf = type_filter.strip().lower()
        if tf in ('in','entrada'):
            filtered = [e for e in filtered if e.get('type') == 'in']
        elif tf in ('out','saida','saída'):
            filtered = [e for e in filtered if e.get('type') and e.get('type') != 'in']

    # Add userName and username for display / filtering
    for entry in filtered:
        user = next((u for u in data.get('users', []) if u['id'] == entry['userId']), None)
        # prefer nome_completo/nome for display; keep 'Desconhecido' fallback
        entry['userName'] = (user.get('nome_completo') or user.get('nome')) if user else 'Desconhecido'
        entry['username'] = user.get('username') if user else ''
        # expose cpf for client-side filtering if available
        entry['cpf'] = user.get('cpf','') if user else ''

    # If search query q provided, filter entries by userName/username/notes
    if q:
        filtered = [e for e in filtered if (
            (e.get('userName') and q in e.get('userName','').lower()) or
            (e.get('username') and q in e.get('username','').lower()) or
            (e.get('notes') and q in e.get('notes','').lower())
        )]

    # If CSV/XLSX report requested
    report_type = request.args.get('report')
    if report_type == 'csv':
        si = StringIO()
        import csv
        writer = csv.writer(si)
        writer.writerow(['Usuário','Tipo','Data/Hora','Observações'])
        for e in filtered:
            writer.writerow([e.get('userName',''), ('Entrada' if e.get('type')=='in' else 'Saída'), e.get('timestamp',''), e.get('notes','')])
        output = si.getvalue()
        return app.response_class(output, mimetype='text/csv', headers={
            'Content-Disposition': 'attachment; filename="clock_report.csv"'
        })
    if report_type == 'xlsx':
        try:
            mod = importlib.import_module('openpyxl')
            Workbook = getattr(mod, 'Workbook')
        except Exception:
            flash('Exportação XLSX não disponível: dependência ausente', 'error')
            return redirect(url_for('clock.clock_entries'))

        wb = Workbook()
        ws = wb.active
        ws.title = 'Registros'
        headers = ['Usuário', 'Tipo', 'Data/Hora', 'Observações']
        ws.append(headers)
        for e in filtered:
            row = [
                e.get('userName',''),
                ('Entrada' if e.get('type')=='in' else 'Saída'),
                e.get('timestamp',''),
                e.get('notes','')
            ]
            ws.append(row)

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        return app.response_class(bio.read(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
            'Content-Disposition': 'attachment; filename="clock_report.xlsx"'
        })

    # Render HTML table for non-CSV requests
    return render_template('clock_entries.html', 
                         user_name=session.get('user_name'),
                         entries=filtered,
                         start_date=start,
                         end_date=end,
                         q=request.args.get('q',''),
                         user_id=user_filter,
                         entry_type=type_filter)


@clock_bp.route('/my-clock-entries')
@login_required
def my_clock_entries():
    data = load_data()
    user_id = session.get('user_id')
    entries = [e for e in data.get('clock_entries', []) if e['userId'] == user_id]
    for entry in entries:
        entry['userName'] = session.get('user_name')
    return render_template('clock_entries.html', user_name=session.get('user_name'), entries=entries)


@clock_bp.route('/clock-entries/add', methods=['GET', 'POST'])
@login_required
def add_clock_entry():
    data = load_data()
    data.setdefault('clock_entries', [])
    if request.method == 'POST':
        user_id = session.get('user_id') if session.get('user_role') != 'admin' else request.form.get('userId')
        type_val = request.form.get('type', '').strip().lower()
        if type_val in ['entrada', 'in']:
            type_val = 'in'
        elif type_val in ['saida', 'saída', 'out']:
            type_val = 'out'
        else:
            type_val = 'in'

        # Weekly limits: 15h max (block), warn when within 1h of limit
        MAX_WEEK_SECONDS = 15 * 3600
        ALERT_THRESHOLD_SECONDS = 14 * 3600

        # If the target user is an admin account, or the current session actor
        # is an admin, do not enforce weekly limits. The user requested the
        # check be skipped when session.user_role == 'admin'.
        target_user = next((u for u in data.get('users', []) if str(u.get('id')) == str(user_id)), None)
        target_is_admin = bool(target_user and target_user.get('role') == 'admin')
        actor_is_admin = session.get('user_role') == 'admin'

        current_week_secs = compute_user_week_seconds(user_id, data)
        # If this is an 'out' registration, estimate the delta from last 'in' to now
        estimated_delta = 0
        if type_val == 'out':
            # find last 'in' entry for this user
            user_entries = [e for e in data.get('clock_entries', []) if str(e.get('userId')) == str(user_id)]
            user_entries = sorted(user_entries, key=lambda e: e.get('timestamp',''))
            last_in = None
            for e in reversed(user_entries):
                if e.get('type') == 'in':
                    last_in = e
                    break
                if e.get('type') == 'out':
                    break
            try:
                if last_in:
                    t_in = datetime.fromisoformat(last_in.get('timestamp'))
                    estimated_delta = (datetime.now() - t_in).total_seconds()
            except Exception:
                estimated_delta = 0

        # warn if near threshold; block if it would exceed the limit
        # EXEMPT admins: skip blocking/warning when either the target user is
        # an admin account or the currently authenticated actor is an admin.
        exempt_from_check = target_is_admin or actor_is_admin
        if not exempt_from_check and (current_week_secs >= MAX_WEEK_SECONDS or (type_val == 'out' and (current_week_secs + estimated_delta) > MAX_WEEK_SECONDS)):
            flash('Limite semanal de 15 horas atingido — não é possível registrar ponto.', 'error')
            if actor_is_admin:
                return redirect(url_for('clock.clock_entries'))
            return redirect(url_for('clock.my_clock_entries'))
        elif not exempt_from_check and (current_week_secs >= ALERT_THRESHOLD_SECONDS or (type_val == 'out' and (current_week_secs + estimated_delta) >= ALERT_THRESHOLD_SECONDS)):
            flash('Atenção: este voluntário aproximou-se do limite semanal de 15 horas.', 'warning')

        new_entry = {
            'id': str(len(data.get('clock_entries', [])) + 1),
            'userId': user_id,
            'type': type_val,
            'timestamp': datetime.now().isoformat(),
            'notes': request.form.get('notes', '')
        }
        data.setdefault('clock_entries', []).append(new_entry)
        save_data(data)
        try:
            log_action(session.get('user_id'), 'clock_create', {'entry_id': new_entry['id'], 'type': new_entry.get('type')})
        except Exception:
            pass
        if session.get('user_role') == 'admin':
            return redirect(url_for('clock.clock_entries'))
        return redirect(url_for('clock.my_clock_entries'))

    active_users = [u for u in data.get('users', []) if u.get('estado_user', 1) != 0]
    # compute weekly seconds for each active user to allow client-side warnings
    users_week_map = {}
    users_role_map = {}
    for u in active_users:
        try:
            secs = compute_user_week_seconds(u.get('id'), data)
        except Exception:
            secs = 0
        users_week_map[str(u.get('id'))] = secs
        users_role_map[str(u.get('id'))] = u.get('role') or ''

    return render_template('clock_entry_form.html', 
                         user_name=session.get('user_name'),
                         users=active_users,
                         entry=None,
                         users_week_map=users_week_map,
                         users_role_map=users_role_map)


@clock_bp.route('/clock-entries/edit/<entry_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_clock_entry(entry_id):
    data = load_data()
    entry = next((e for e in data.get('clock_entries', []) if e.get('id') == entry_id), None)
    if not entry:
        flash('Registro não encontrado.', 'error')
        return redirect(url_for('clock.clock_entries'))

    if request.method == 'POST':
        # admin may change userId
        user_id = request.form.get('user_id') or entry.get('userId')
        type_val = request.form.get('type', '').strip().lower()
        if type_val in ['entrada', 'in']:
            type_val = 'in'
        elif type_val in ['saida', 'saída', 'out']:
            type_val = 'out'
        else:
            type_val = 'in'

        ts = request.form.get('timestamp') or entry.get('timestamp')
        notes = request.form.get('notes','')

        # persist changes
        entry['userId'] = user_id
        entry['type'] = type_val
        entry['timestamp'] = ts
        entry['notes'] = notes
        save_data(data)
        try:
            log_action(session.get('user_id'), 'clock_edit', {'entry_id': entry_id})
        except Exception:
            pass
        return redirect(url_for('clock.clock_entries'))

    # GET -> render form prefilled (only active users selectable)
    active_users = [u for u in data.get('users', []) if u.get('estado_user', 1) != 0]
    users_week_map = {}
    users_role_map = {}
    for u in active_users:
        try:
            secs = compute_user_week_seconds(u.get('id'), data)
        except Exception:
            secs = 0
        users_week_map[str(u.get('id'))] = secs
        users_role_map[str(u.get('id'))] = u.get('role') or ''

    return render_template('clock_entry_form.html', user_name=session.get('user_name'), users=active_users, entry=entry, users_week_map=users_week_map, users_role_map=users_role_map)


@clock_bp.route('/clock/toggle', methods=['POST'])
@login_required
def toggle_clock_entry():
    data = load_data()
    user_id = session.get('user_id')
    user_entries = [e for e in data.get('clock_entries', []) if e['userId'] == user_id]
    last = None
    if user_entries:
        last = sorted(user_entries, key=lambda e: e['timestamp'])[-1]

    next_type = 'in'
    if last and last.get('type') == 'in':
        next_type = 'out'

    new_entry = {
        'id': str(len(data.get('clock_entries', [])) + 1),
        'userId': user_id,
        'type': next_type,
        'timestamp': datetime.now().isoformat(),
        'notes': 'Registro rápido'
    }
    # enforce weekly limit before toggling
    MAX_WEEK_SECONDS = 15 * 3600
    # If the actor is an admin or the target user is admin, skip enforcement.
    target_user = next((u for u in data.get('users', []) if str(u.get('id')) == str(user_id)), None)
    actor_is_admin = session.get('user_role') == 'admin'
    target_is_admin = bool(target_user and target_user.get('role') == 'admin')
    if target_is_admin or actor_is_admin:
        # admin users (actor or target) are exempt from the weekly limit
        pass
    else:
        current_week_secs = compute_user_week_seconds(user_id, data)
        # if toggling to 'out', estimate the delta from last 'in'
        if next_type == 'out':
            last_in = None
            for e in reversed(sorted(user_entries, key=lambda e: e.get('timestamp'))):
                if e.get('type') == 'in':
                    last_in = e
                    break
                if e.get('type') == 'out':
                    break
            est_delta = 0
            try:
                if last_in:
                    t_in = datetime.fromisoformat(last_in.get('timestamp'))
                    est_delta = (datetime.now() - t_in).total_seconds()
            except Exception:
                est_delta = 0

            if current_week_secs >= MAX_WEEK_SECONDS or (current_week_secs + est_delta) > MAX_WEEK_SECONDS:
                flash('Limite semanal de 15 horas atingido — não é possível registrar ponto.', 'error')
                return redirect(url_for('home'))
        else:
            if current_week_secs >= MAX_WEEK_SECONDS:
                flash('Limite semanal de 15 horas atingido — não é possível registrar ponto.', 'error')
                return redirect(url_for('home'))

    data.setdefault('clock_entries', []).append(new_entry)
    save_data(data)
    try:
        log_action(session.get('user_id'), 'clock_toggle', {'entry_id': new_entry['id'], 'type': new_entry.get('type')})
    except Exception:
        pass

    if next_type == 'in':
        flash('Entrada registrada', 'success')
    else:
        flash('Saída registrada', 'success')

    return redirect(url_for('home'))

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import csv
from io import StringIO

from ..models.storage import load_data, save_data, ensure_data_keys
from ..utils import generate_username, default_password_from_cpf, log_action, login_required, admin_required, compute_user_week_seconds

users_bp = Blueprint('users', __name__)


@users_bp.route('/users')
@login_required
@admin_required
def users():
    data = load_data()
    q = (request.args.get('q') or '').strip().lower()
    q_digits = re.sub(r'\D', '', q)

    def compute_total_seconds(user_id):
        entries = [e for e in data.get('clock_entries', []) if e.get('userId') == user_id]
        entries = sorted(entries, key=lambda e: e.get('timestamp'))
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
                    break
            else:
                i += 1
        return total

    users_with_hours = []
    for u in data.get('users', []):
        secs = compute_total_seconds(u.get('id'))
        hrs = int(secs // 3600)
        mins = int((secs % 3600) // 60)
        users_with_hours.append({
            'id': u.get('id'),
            'username': u.get('username'),
            'nome_completo': u.get('nome_completo',''),
            'nome': u.get('nome',''),
            'sobrenome': u.get('sobrenome',''),
            'cpf': u.get('cpf',''),
            'email': u.get('email'),
            'role': u.get('role'),
            'hospital': u.get('hospital',''),
            'codigo_cracha': u.get('codigo_cracha',''),
            'celular': u.get('celular',''),
            'telefone_residencial': u.get('telefone_residencial',''),
            'data_nascimento': u.get('data_nascimento',''),
            'estado_user': int(u.get('estado_user', 1) or 0),
            'createdAt': u.get('createdAt',''),
            'hours_str': f"{hrs}h {mins}m",
        })

    # apply free-text search first
    if q:
        def matches(u):
            if u.get('nome_completo') and q in u.get('nome_completo','').lower():
                return True
            if u.get('username') and q in u.get('username','').lower():
                return True
            if q_digits:
                stored_cpf = re.sub(r'\D', '', u.get('cpf',''))
                if q_digits in stored_cpf:
                    return True
            return False

        users_with_hours = [u for u in users_with_hours if matches(u)]

    # additional filters: role, status (active/inactive)
    role_filter = (request.args.get('role') or '').strip()
    status_filter = (request.args.get('status') or '').strip()  # 'active'|'inactive' or ''

    def passes_filters(u):
        if role_filter:
            if (u.get('role') or '') != role_filter:
                return False
        if status_filter:
            if status_filter == 'active' and int(u.get('estado_user', 1) or 0) != 1:
                return False
            if status_filter == 'inactive' and int(u.get('estado_user', 1) or 0) == 1:
                return False
        return True

    users_with_hours = [u for u in users_with_hours if passes_filters(u)]

    return render_template('users.html', user_name=session.get('user_name'), users=users_with_hours, q=request.args.get('q',''), role_selected=role_filter, status_selected=status_filter)


@users_bp.route('/schedules')
@login_required
@admin_required
def schedules():
    data = load_data()
    users = data.get('users', [])
    schedules = data.get('schedules', [])
    # compute weekly seconds per user
    week_map = {}
    for u in users:
        try:
            week_map[str(u.get('id'))] = compute_user_week_seconds(u.get('id'), data)
        except Exception:
            week_map[str(u.get('id'))] = 0

    return render_template('schedules.html', users=users, schedules=schedules, week_map=week_map, user_name=session.get('user_name'))


@users_bp.route('/schedules/add', methods=['POST'])
@login_required
@admin_required
def add_schedule():
    data = load_data()
    data.setdefault('schedules', [])
    user_id = request.form.get('user_id')
    day = request.form.get('day')
    start = request.form.get('start')
    end = request.form.get('end')
    try:
        next_id = str(max([int(x.get('id')) for x in data['schedules']]) + 1 if data['schedules'] else 1)
    except Exception:
        next_id = '1'
    sched = {
        'id': next_id,
        'userId': user_id,
        'day': day,
        'start': start,
        'end': end,
        'createdAt': datetime.now().isoformat()
    }
    data['schedules'].append(sched)
    save_data(data)
    try:
        log_action(session.get('user_id'), 'schedule_create', {'schedule_id': next_id, 'user_id': user_id})
    except Exception:
        pass
    flash('Escala adicionada.', 'success')
    return redirect(url_for('users.schedules'))


@users_bp.route('/schedules/delete/<sched_id>', methods=['POST'])
@login_required
@admin_required
def delete_schedule(sched_id):
    data = load_data()
    schedules = data.get('schedules', [])
    if not any(str(s.get('id')) == str(sched_id) for s in schedules):
        flash('Escala não encontrada.', 'error')
        return redirect(url_for('users.schedules'))
    data['schedules'] = [s for s in schedules if str(s.get('id')) != str(sched_id)]
    save_data(data)
    try:
        log_action(session.get('user_id'), 'schedule_delete', {'schedule_id': sched_id})
    except Exception:
        pass
    flash('Escala removida.', 'success')
    return redirect(url_for('users.schedules'))


@users_bp.route('/schedules/edit/<sched_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_schedule(sched_id):
    data = load_data()
    schedules = data.get('schedules', [])
    sched = next((s for s in schedules if str(s.get('id')) == str(sched_id)), None)
    if not sched:
        flash('Escala não encontrada.', 'error')
        return redirect(url_for('users.schedules'))

    if request.method == 'POST':
        sched['userId'] = request.form.get('user_id') or sched.get('userId')
        sched['day'] = request.form.get('day') or sched.get('day')
        sched['start'] = request.form.get('start') or sched.get('start')
        sched['end'] = request.form.get('end') or sched.get('end')
        save_data(data)
        try:
            log_action(session.get('user_id'), 'schedule_edit', {'schedule_id': sched_id})
        except Exception:
            pass
        flash('Escala atualizada.', 'success')
        return redirect(url_for('users.schedules'))

    users = data.get('users', [])
    return render_template('schedules_edit.html', sched=sched, users=users, user_name=session.get('user_name'))


@users_bp.route('/users/check_username')
@login_required
@admin_required
def check_username():
    username = (request.args.get('username') or '').strip()
    user_id = request.args.get('user_id')
    if not username:
        return jsonify({'available': False, 'message': 'Informe um nome de usuário.'})
    data = load_data()
    for u in data.get('users', []):
        if (u.get('username') or '').lower() == username.lower():
            if user_id and str(u.get('id')) == str(user_id):
                continue
            return jsonify({'available': False, 'message': 'Nome de usuário indisponível.'})
    return jsonify({'available': True, 'message': 'Disponível.'})


@users_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        data = load_data()
        cpf = request.form.get('cpf','')
        pw = request.form.get('password') or ''
        if not pw:
            pw = default_password_from_cpf(cpf)
        existing_usernames = { (u.get('username') or '').lower() for u in data.get('users', []) }
        provided_username = (request.form.get('username') or '').strip()
        if provided_username:
            if provided_username.lower() in existing_usernames:
                user_prefill = {k: request.form.get(k) for k in request.form}
                field_errors = {'username': 'Nome de usuário indisponível — escolha outro.'}
                return render_template('user_form.html', user_name=session.get('user_name'), user=user_prefill, add_mode=True, field_errors=field_errors)
            username_to_use = provided_username
        else:
            username_to_use = generate_username(request.form.get('nome',''), request.form.get('sobrenome',''), existing_usernames)

        # normalize name fields and build a clean full name with a single space when both parts exist
        nome_val = (request.form.get('nome','') or '').strip()
        sobrenome_val = (request.form.get('sobrenome','') or '').strip()

        new_user = {
            'id': str(len(data.get('users', [])) + 1),
            'username': username_to_use,
            'password': generate_password_hash(pw) if pw else '',
            'nome': nome_val,
            'sobrenome': sobrenome_val,
            'nome_completo': f"{nome_val} {sobrenome_val}".strip(),
            'hospital': request.form.get('hospital',''),
            'email': request.form.get('email'),
            'role': request.form.get('role') or 'user',
            'phone': request.form.get('phone', ''),
            'celular': request.form.get('celular',''),
            'telefone_residencial': request.form.get('telefone_residencial',''),
            'local_nascimento': request.form.get('local_nascimento',''),
            'nome_conjuge': request.form.get('nome_conjuge',''),
            'nome_pai': request.form.get('nome_pai',''),
            'nome_mae': request.form.get('nome_mae',''),
            'data_nascimento': request.form.get('data_nascimento', ''),
            'codigo_cracha': request.form.get('codigo_cracha',''),
            'cpf': request.form.get('cpf',''),
            'rg': request.form.get('rg',''),
            'endereco': request.form.get('endereco',''),
            'numero': request.form.get('numero',''),
            'bairro': request.form.get('bairro',''),
            'cidade': request.form.get('cidade',''),
            'cep': request.form.get('cep',''),
            'estado_civil': request.form.get('estado_civil',''),
            'religiao': request.form.get('religiao',''),
            'escolaridade_curso': request.form.get('escolaridade_curso',''),
            'local_trabalho': request.form.get('local_trabalho',''),
            'telefone_trabalho': request.form.get('telefone_trabalho',''),
            'ocupacao': request.form.get('ocupacao',''),
            'ocupacao_outro': request.form.get('ocupacao_outro',''),
            'acomp_med': request.form.get('acomp_med') or ( 'Sim' if request.form.get('acomp_med_radio')=='yes' else ('Não' if request.form.get('acomp_med_radio')=='no' else '')),
            'acomp_med_qual': request.form.get('acomp_med_qual',''),
            'transporte': request.form.get('transporte',''),
            'ficou_sab': request.form.get('ficou_sab',''),
            'ja_volunt': 1 if request.form.get('ja_volunt_radio')=='yes' or request.form.get('ja_volunt') else 0,
            'ja_volunt_onde': request.form.get('ja_volunt_onde',''),
            'faz_volunt': request.form.get('faz_volunt',''),
            'contrib_ser': request.form.get('contrib_ser',''),
            'hab_musical': 1 if request.form.get('hab_musical_radio')=='yes' or request.form.get('hab_musical') else 0,
            'hab_musical_qual': request.form.get('hab_musical_qual',''),
            'aux_alimentacao': 1 if request.form.get('aux_alimentacao')=='yes' or request.form.get('aux_alimentacao')=='1' else 0,
            'estado_user': 1,
            'createdAt': datetime.now().isoformat()
        }

        data.setdefault('users', []).append(new_user)
        save_data(data)
        try:
            log_action(session.get('user_id'), 'user_create', {'new_user_id': new_user['id'], 'username': new_user.get('username')})
        except Exception:
            pass
        return redirect(url_for('users.users'))

    return render_template('user_form.html', user_name=session.get('user_name'), user=None, add_mode=True)


@users_bp.route('/users/edit/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    data = load_data()
    user = next((u for u in data.get('users', []) if u.get('id') == user_id), None)
    if not user:
        return redirect(url_for('users.users'))

    if request.method == 'POST':
        new_username = (request.form.get('username') or '').strip()
        if new_username and new_username.lower() != (user.get('username') or '').lower():
            data = load_data()
            # reload the user object from the freshly loaded data so modifications land in the saved structure
            user = next((u for u in data.get('users', []) if u.get('id') == user_id), None)
            other_usernames = { (u.get('username') or '').lower(): u.get('id') for u in data.get('users', []) }
            owner = other_usernames.get(new_username.lower())
            if owner and owner != user_id:
                user_prefill = dict(user)
                for k in request.form:
                    user_prefill[k] = request.form.get(k)
                field_errors = {'username': 'Nome de usuário indisponível — escolha outro.'}
                return render_template('user_form.html', user_name=session.get('user_name'), user=user_prefill, field_errors=field_errors)

        user['username'] = new_username or user.get('username')
        user['nome'] = (request.form.get('nome','') or '').strip()
        user['sobrenome'] = (request.form.get('sobrenome','') or '').strip()
        user['nome_completo'] = f"{user['nome']} {user['sobrenome']}".strip()
        user['hospital'] = request.form.get('hospital','')
        user['email'] = request.form.get('email')
        user['role'] = request.form.get('role')
        user['phone'] = request.form.get('phone', '')
        user['celular'] = request.form.get('celular','')
        user['telefone_residencial'] = request.form.get('telefone_residencial','')
        user['local_nascimento'] = request.form.get('local_nascimento','')
        user['nome_conjuge'] = request.form.get('nome_conjuge','')
        user['nome_pai'] = request.form.get('nome_pai','')
        user['nome_mae'] = request.form.get('nome_mae','')
        user['data_nascimento'] = request.form.get('data_nascimento', '')
        user['codigo_cracha'] = request.form.get('codigo_cracha','')
        user['cpf'] = request.form.get('cpf','')
        user['rg'] = request.form.get('rg','')
        user['endereco'] = request.form.get('endereco','')
        user['numero'] = request.form.get('numero','')
        user['bairro'] = request.form.get('bairro','')
        user['cidade'] = request.form.get('cidade','')
        user['cep'] = request.form.get('cep','')
        user['estado_civil'] = request.form.get('estado_civil','')
        user['religiao'] = request.form.get('religiao','')
        user['escolaridade_curso'] = request.form.get('escolaridade_curso','')
        user['local_trabalho'] = request.form.get('local_trabalho','')
        user['telefone_trabalho'] = request.form.get('telefone_trabalho','')
        user['ocupacao'] = request.form.get('ocupacao','')
        user['ocupacao_outro'] = request.form.get('ocupacao_outro','')
        user['acomp_med'] = request.form.get('acomp_med') or ( 'Sim' if request.form.get('acomp_med_radio')=='yes' else ('Não' if request.form.get('acomp_med_radio')=='no' else ''))
        user['acomp_med_qual'] = request.form.get('acomp_med_qual','')
        user['transporte'] = request.form.get('transporte','')
        user['ficou_sab'] = request.form.get('ficou_sab','')
        user['ja_volunt'] = 1 if request.form.get('ja_volunt_radio')=='yes' or request.form.get('ja_volunt') else 0
        user['ja_volunt_onde'] = request.form.get('ja_volunt_onde','')
        user['faz_volunt'] = request.form.get('faz_volunt','')
        user['contrib_ser'] = request.form.get('contrib_ser','')
        user['hab_musical'] = 1 if request.form.get('hab_musical_radio')=='yes' or request.form.get('hab_musical') else 0
        user['hab_musical_qual'] = request.form.get('hab_musical_qual','')
        user['aux_alimentacao'] = 1 if request.form.get('aux_alimentacao')=='yes' or request.form.get('aux_alimentacao')=='1' else 0
        if request.form.get('password'):
            user['password'] = generate_password_hash(request.form.get('password'))

        # NOTE: do NOT update 'estado_user' here. Activation state must only be
        # changed via the dedicated toggle action (`/users/toggle_active`) so that
        # deactivation/activation is explicit and admins cannot be accidentally
        # deactivated by saving the edit form. The toggle endpoint enforces that
        # admin accounts cannot be deactivated unless their role is changed first.

        save_data(data)
        try:
            log_action(session.get('user_id'), 'user_edit', {'edited_user_id': user_id})
        except Exception:
            pass
        return redirect(url_for('users.users'))

    # compute current week worked seconds so the form can warn when near the weekly cap
    try:
        from app.utils import compute_user_week_seconds
        week_secs = compute_user_week_seconds(user_id)
    except Exception:
        week_secs = 0
    hrs = int(week_secs // 3600)
    mins = int((week_secs % 3600) // 60)
    week_hours_str = f"{hrs}h {mins}m"
    return render_template('user_form.html', user_name=session.get('user_name'), user=user, week_hours_str=week_hours_str, week_secs=week_secs)


@users_bp.route('/users/delete/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_user(user_id):
    data = load_data()
    user = next((u for u in data.get('users', []) if u.get('id') == user_id), None)
    if not user:
        flash('Voluntário não encontrado.', 'error')
        return redirect(url_for('users.users'))

    if user.get('username') == 'admin':
        flash('O usuário administrador principal não pode ser removido.', 'error')
        return redirect(url_for('users.users'))

    require_password = (user.get('role') == 'admin')

    if request.method == 'POST':
        if require_password:
            admin_password = request.form.get('admin_password')
            current = next((u for u in data.get('users', []) if u.get('id') == session.get('user_id')), None)
            ok = False
            if current:
                stored = current.get('password','')
                if stored == admin_password or (stored and check_password_hash(stored, admin_password)):
                    ok = True
            if not ok:
                flash('Senha do administrador inválida.', 'error')
                return redirect(url_for('users.delete_user', user_id=user_id))

        data['users'] = [u for u in data.get('users', []) if u.get('id') != user_id]
        save_data(data)
        try:
            log_action(session.get('user_id'), 'user_delete', {'deleted_user_id': user_id})
        except Exception:
            pass
    flash('Voluntário removido com sucesso.', 'success')
    return redirect(url_for('users.users'))

    return render_template('confirm_delete.html', user=user, require_password=require_password, user_name=session.get('user_name'))


@users_bp.route('/users/toggle_active/<user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_active(user_id):
    data = load_data()
    user = next((u for u in data.get('users', []) if u.get('id') == user_id), None)
    if not user:
        flash('Voluntário não encontrado.', 'error')
        return redirect(url_for('users.users'))

    # Prevent deactivating the primary admin
    if user.get('role') == 'admin' and user.get('username') == 'admin':
        flash('O usuário administrador principal não pode ser desativado.', 'error')
        return redirect(url_for('users.users'))

    current = int(user.get('estado_user', 1) or 0)
    # If trying to deactivate any admin account, block it
    if current == 1 and user.get('role') == 'admin':
        # If request is AJAX, return a JSON error so client can show a message
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Contas com papel de administrador não podem ser desativadas.'}), 403
        flash('Contas com papel de administrador não podem ser desativadas.', 'error')
        return redirect(url_for('users.users'))

    new_state = 0 if current == 1 else 1
    user['estado_user'] = new_state
    save_data(data)
    try:
        log_action(session.get('user_id'), 'user_toggle_active', {'target_user_id': user_id, 'new_state': new_state})
    except Exception:
        pass

    # Support AJAX toggles: return JSON when requested so the client can update UI without a reload
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'ok', 'new_state': new_state})

    flash('Usuário {}.'.format('ativado' if new_state == 1 else 'desativado'), 'success')
    return redirect(url_for('users.users'))


@users_bp.route('/export/users')
@login_required
@admin_required
def export_users():
    data = load_data()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['id', 'username', 'nome_completo', 'email', 'role', 'cpf', 'criadoEm'])
    for u in data.get('users', []):
        writer.writerow([
            u.get('id',''),
            u.get('username',''),
            u.get('nome_completo',''),
            u.get('email',''),
            u.get('role',''),
            u.get('cpf',''),
            u.get('createdAt','')
        ])
    output = si.getvalue()
    try:
        log_action(session.get('user_id'), 'export_users_csv', {'count': len(data.get('users', []))})
    except Exception:
        pass
    return users_bp.make_response((output, 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename="users.csv"'}))


@users_bp.route('/register-badge', methods=['GET', 'POST'])
@login_required
@admin_required
def register_badge():
    data = load_data()
    q = (request.args.get('q') or '').strip().lower()
    users = data.get('users', [])[:]
    if q:
        users = [u for u in users if (q in (u.get('nome') or '').lower()) or (q in (u.get('username') or '').lower())]

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        code = request.form.get('codigo_cracha')
        user = next((u for u in data.get('users', []) if u.get('id') == user_id), None)
        if not user:
            flash('Voluntário não encontrado.', 'error')
            return redirect(url_for('users.register_badge'))
        user['codigo_cracha'] = code or ''
        save_data(data)
    flash('Crachá registrado com sucesso!', 'success')
    return redirect(url_for('users.register_badge'))

    users_for_template = [type('X', (), u)() for u in users]
    return render_template('register_badge.html', users=users_for_template, q=request.args.get('q',''))

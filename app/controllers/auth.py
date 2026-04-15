from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, abort
from werkzeug.security import check_password_hash, generate_password_hash

from ..models.storage import load_data, save_data
from ..utils import log_action, default_password_from_cpf, login_required, admin_required, generate_username
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        data = load_data()
        user = next((u for u in data.get('users', []) if u.get('username') == username), None)
        authenticated = False
        if user:
            stored = user.get('password', '')
            if stored == password or (stored and check_password_hash(stored, password)):
                authenticated = True
                # migrate plaintext to hashed
                if not stored or stored == password:
                    try:
                        user['password'] = generate_password_hash(password)
                        save_data(data)
                    except Exception:
                        pass

        if authenticated:
            # Prevent login for deactivated users
            if user.get('estado_user', 1) == 0:
                return render_template('login.html', error='Conta desativada. Entre em contato com o administrador.')
            session['user_id'] = user['id']
            session['user_name'] = user.get('nome_completo') or user.get('nome')
            session['user_role'] = user['role']
            return redirect(url_for('home'))

        return render_template('login.html', error='Usuário ou senha inválidos')

    return render_template('login.html')


@auth_bp.route('/logout', endpoint='logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@auth_bp.route('/profile', methods=['GET', 'POST'], endpoint='profile')
@login_required
def profile():
    data = load_data()
    user_id = session.get('user_id')
    user = next((u for u in data['users'] if u['id'] == user_id), None)
    if not user:
        flash('Usuário não encontrado', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        new_username = request.form.get('username')
        if new_username and new_username.strip() and new_username != user.get('username'):
            if any(u for u in data['users'] if u.get('username') == new_username and u.get('id') != user_id):
                flash('Nome de usuário já está em uso por outro voluntário.', 'error')
                return redirect(url_for('auth.profile'))
            user['username'] = new_username.strip()

        new_pw = request.form.get('password')
        confirm_pw = request.form.get('password_confirm')
        if new_pw:
            if new_pw != confirm_pw:
                flash('As senhas informadas não coincidem.', 'error')
                return redirect(url_for('auth.profile'))
            user['password'] = generate_password_hash(new_pw)

        save_data(data)
        flash('Perfil atualizado com sucesso.', 'success')
        session['user_name'] = user.get('nome_completo') or user.get('nome')
        return redirect(url_for('home'))

    return render_template('user_form.html', user=user, user_name=session.get('user_name'), profile_mode=True)


@auth_bp.route('/register', methods=['GET', 'POST'], endpoint='register')
@login_required
@admin_required
def register():
    if request.method == 'POST':
        data = load_data()

        # accept both 'username' and a generated username from name/sobrenome
        provided_username = (request.form.get('username') or '').strip()

        cpf = request.form.get('cpf','').strip()
        nome = request.form.get('nome','').strip()
        sobrenome = request.form.get('sobrenome','').strip()

        existing_usernames = { (u.get('username') or '').lower() for u in data.get('users', []) }
        if provided_username:
            if provided_username.lower() in existing_usernames:
                return render_template('login.html', error='Nome de usuário já existe.')
            username_to_use = provided_username
        else:
            username_to_use = generate_username(request.form.get('nome','') or (request.form.get('nome','') + ' ' + request.form.get('sobrenome','')), request.form.get('sobrenome',''), existing_usernames)

        pw = request.form.get('password') or ''
        if not pw:
            pw = default_password_from_cpf(cpf)

        # build new user with fields consistent with the users add/edit handlers
        new_user = {
            'id': str(len(data['users']) + 1),
            'username': username_to_use,
            'password': generate_password_hash(pw) if pw else '',
            'nome': request.form.get('nome',''),
            'sobrenome': request.form.get('sobrenome',''),
            'nome_completo': ((request.form.get('nome','') or '') + ((' ' + request.form.get('sobrenome','')) if request.form.get('sobrenome','') else '')).strip(),
            'hospital': request.form.get('hospital',''),
            'email': request.form.get('email'),
            'role': request.form.get('role') or 'user',
            'department': request.form.get('department'),
            'phone': request.form.get('phone', ''),
            'celular': request.form.get('celular',''),
            'telefone_residencial': request.form.get('telefone_residencial',''),
            'local_nascimento': request.form.get('local_nascimento',''),
            'nome_conjuge': request.form.get('nome_conjuge',''),
            'nome_pai': request.form.get('nome_pai',''),
            'nome_mae': request.form.get('nome_mae',''),
            'data_nascimento': request.form.get('data_nascimento', ''),
            'codigo_cracha': request.form.get('codigo_cracha',''),
            'cpf': cpf,
            'rg': request.form.get('rg',''),
            'rua': request.form.get('rua',''),
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
            'createdAt': datetime.now().isoformat()
        }

        data['users'].append(new_user)
        save_data(data)
        # Audit log
        try:
            log_action(session.get('user_id'), 'user_create', {'new_user_id': new_user['id'], 'username': new_user.get('username')})
        except Exception:
            pass
        return redirect(url_for('users'))

    return render_template('user_form.html', user=None, user_name=None)


@auth_bp.route('/dev-login', endpoint='dev_login')
def dev_login():
    """Development helper: automatically log in as the admin user.

    This route is intentionally available only when the Flask app is running
    in development mode (ENV='development' or debug True). It should NOT be
    enabled in production.
    """
    # Allow only in development/debug environments
    if not (current_app.debug or current_app.config.get('ENV') == 'development' or str(current_app.config.get('FLASK_ENV','')).lower() == 'development'):
        abort(404)

    data = load_data()
    # prefer username 'admin', otherwise first admin-role user
    user = next((u for u in data.get('users', []) if u.get('username') == 'admin'), None)
    if not user:
        user = next((u for u in data.get('users', []) if u.get('role') == 'admin'), None)
    if not user:
        abort(404)

    session['user_id'] = user['id']
    session['user_name'] = user.get('nome_completo') or user.get('nome')
    session['user_role'] = user.get('role')
    try:
        log_action(user['id'], 'dev_login', {'note': 'dev-login used'})
    except Exception:
        pass
    return redirect(url_for('home'))

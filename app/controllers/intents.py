from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app as app
from datetime import datetime
from werkzeug.security import generate_password_hash

from app.models.storage import load_data, save_data
from app.utils import log_action, login_required, admin_required, generate_username, default_password_from_cpf

intents_bp = Blueprint('intents', __name__)


@intents_bp.route('/intencao', methods=['GET', 'POST'])
def submit_intention():
    data = load_data()
    # build a quick map of existing users by normalized cpf to current week seconds
    cpf_week_map = {}
    try:
        from app.utils import compute_user_week_seconds
        for u in data.get('users', []) or []:
            cpf = (u.get('cpf') or '')
            digits = ''.join([c for c in cpf if c.isdigit()])
            if not digits:
                continue
            try:
                secs = compute_user_week_seconds(u.get('id'), data)
            except Exception:
                secs = 0
            cpf_week_map[digits] = {'secs': secs, 'name': u.get('nome_completo') or u.get('nome') or '', 'role': u.get('role')}
    except Exception:
        cpf_week_map = {}

    if request.method == 'POST':
        form = request.form
        required = ['nome', 'sobrenome', 'data_nascimento', 'rg', 'cpf', 'celular', 'email', 'endereco', 'numero', 'bairro', 'cidade', 'cep']
        missing = [f for f in required if not form.get(f)]
        if missing:
            flash('Por favor preencha os campos obrigatórios: ' + ', '.join(missing), 'error')
            return redirect(url_for('intents.submit_intention'))

        intent = {
            'hospital': form.get('hospital') or '',
            'nome': ((form.get('nome') or '').strip() + ' ' + (form.get('sobrenome') or '').strip()).strip(),
            'sobrenome': form.get('sobrenome') or '',
            'data_nascimento': form.get('data_nascimento') or '',
            'local_nascimento': form.get('local_nascimento') or '',
            'rg': form.get('rg') or '',
            'cpf': form.get('cpf') or '',
            'estado_civil': form.get('estado_civil') or '',
            'nome_conjuge': form.get('nome_conjuge') or '',
            'nome_pai': form.get('nome_pai') or '',
            'nome_mae': form.get('nome_mae') or '',
            'endereco': form.get('endereco') or '',
            'numero': form.get('numero') or '',
            'bairro': form.get('bairro') or '',
            'cidade': form.get('cidade') or '',
            'cep': form.get('cep') or '',
            'telefone_residencial': form.get('telefone_residencial') or '',
            'celular': form.get('celular') or '',
            'religiao': form.get('religiao') or '',
            'email': form.get('email') or '',
            'escolaridade_curso': form.get('escolaridade_curso') or '',
            'local_trabalho': form.get('local_trabalho') or '',
            'telefone_trabalho': form.get('telefone_trabalho') or '',
            'ocupacao': form.get('ocupacao') or '',
            'ocupacao_outro': form.get('ocupacao_outro') or '',
            'acomp_med': ('Sim' if form.get('acomp_med_radio') == 'yes' else 'Não') if form.get('acomp_med_radio') else (form.get('acomp_med') or ''),
            'acomp_med_qual': form.get('acomp_med_qual') or '',
            'transporte': form.get('transporte') or '',
            'ficou_sab': form.get('ficou_sab') or '',
            'ja_volunt': 1 if form.get('ja_volunt') else 0,
            'ja_volunt_onde': form.get('ja_volunt_onde') or '',
            'faz_volunt': form.get('faz_volunt') or '',
            'contrib_ser': form.get('contrib_ser') or '',
            'hab_musical': 1 if form.get('hab_musical') else 0,
            'hab_musical_qual': form.get('hab_musical_qual') or '',
            'aux_alimentacao': 1 if form.get('aux_alimentacao') else 0,
            'createdAt': datetime.now().isoformat()
        }

        data = load_data()
        data.setdefault('intents', [])
        try:
            next_id = max([int(x.get('idintencao')) for x in data['intents']]) + 1 if data['intents'] else 1
        except Exception:
            next_id = 1
        intent['idintencao'] = str(next_id)

        dup = next((x for x in data['intents'] if x.get('cpf') == intent['cpf'] or x.get('email') == intent['email']), None)
        if dup:
            flash('Já existe uma inscrição com este CPF ou e-mail.', 'error')
            return redirect(url_for('intents.submit_intention'))

        data['intents'].append(intent)
        save_data(data)
        flash('Inscrição enviada com sucesso. Obrigado!', 'success')
        return redirect(url_for('intents.submit_intention'))

    return render_template('intention_form.html', cpf_week_map=cpf_week_map)


@intents_bp.route('/intencoes')
@login_required
@admin_required
def intents():
    data = load_data()
    intents = data.get('intents', [])
    return render_template('intents.html', intents=intents)


@intents_bp.route('/intencao/approve/<intent_id>', methods=['POST'])
@login_required
@admin_required
def approve_intent(intent_id):
    data = load_data()
    intents = data.get('intents', [])
    intent = next((i for i in intents if str(i.get('idintencao')) == str(intent_id)), None)
    if not intent:
        flash('Inscrição não encontrada.', 'error')
        return redirect(url_for('intents.intents'))

    users = data.get('users', [])
    try:
        next_uid = str(max([int(u.get('id')) for u in users]) + 1 if users else 1)
    except Exception:
        next_uid = '1'

    existing_usernames = {u.get('username') for u in users}
    username = generate_username(intent.get('nome') or 'user', intent.get('sobrenome',''), existing_usernames)
    password_plain = default_password_from_cpf(intent.get('cpf')) or 'changeme'

    new_user = {
        'id': next_uid,
        'username': username,
        'password': generate_password_hash(password_plain),
        'nome': intent.get('nome'),
        'sobrenome': intent.get('sobrenome',''),
        'nome_completo': ((intent.get('nome') or '') + ((' ' + (intent.get('sobrenome') or '')) if intent.get('sobrenome') else '')).strip(),
        'hospital': intent.get('hospital',''),
        'email': intent.get('email'),
        'role': 'user',
        'phone': intent.get('celular') or intent.get('telefone_residencial') or '',
        'celular': intent.get('celular',''),
        'telefone_residencial': intent.get('telefone_residencial',''),
        'cpf': intent.get('cpf'),
        'rg': intent.get('rg'),
        'data_nascimento': intent.get('data_nascimento') or '',
        'local_nascimento': intent.get('local_nascimento',''),
        'nome_conjuge': intent.get('nome_conjuge',''),
        'nome_pai': intent.get('nome_pai',''),
        'nome_mae': intent.get('nome_mae',''),
        'endereco': intent.get('endereco',''),
        'numero': intent.get('numero',''),
        'bairro': intent.get('bairro',''),
        'cidade': intent.get('cidade',''),
        'cep': intent.get('cep',''),
        'estado_civil': intent.get('estado_civil',''),
        'religiao': intent.get('religiao',''),
        'escolaridade_curso': intent.get('escolaridade_curso',''),
        'local_trabalho': intent.get('local_trabalho',''),
        'telefone_trabalho': intent.get('telefone_trabalho',''),
        'ocupacao': intent.get('ocupacao',''),
        'ocupacao_outro': intent.get('ocupacao_outro',''),
        'acomp_med': intent.get('acomp_med',''),
        'acomp_med_qual': intent.get('acomp_med_qual',''),
        'transporte': intent.get('transporte',''),
        'ficou_sab': intent.get('ficou_sab',''),
        'ja_volunt': intent.get('ja_volunt', 0),
        'ja_volunt_onde': intent.get('ja_volunt_onde',''),
        'faz_volunt': intent.get('faz_volunt',''),
        'contrib_ser': intent.get('contrib_ser',''),
        'hab_musical': intent.get('hab_musical', 0),
        'hab_musical_qual': intent.get('hab_musical_qual',''),
        'aux_alimentacao': intent.get('aux_alimentacao', 0),
        'createdAt': datetime.now().isoformat()
    }

    users.append(new_user)
    data['intents'] = [i for i in intents if str(i.get('idintencao')) != str(intent_id)]
    save_data(data)

    log_action(session.get('user_id'), 'approve_intent', {'intent_id': intent_id, 'new_user_id': next_uid})

    flash(f"Candidato aprovado e criado como voluntário (usuário: {username}). Senha inicial: {password_plain}" , 'success')
    return redirect(url_for('intents.intents'))


@intents_bp.route('/intencao/delete/<intent_id>', methods=['POST'])
@login_required
@admin_required
def delete_intent(intent_id):
    data = load_data()
    intents = data.get('intents', [])
    if not any(str(i.get('idintencao')) == str(intent_id) for i in intents):
        flash('Inscrição não encontrada.', 'error')
        return redirect(url_for('intents.intents'))
    data['intents'] = [i for i in intents if str(i.get('idintencao')) != str(intent_id)]
    save_data(data)
    log_action(session.get('user_id'), 'delete_intent', {'intent_id': intent_id})
    flash('Inscrição removida.', 'success')
    return redirect(url_for('intents.intents'))

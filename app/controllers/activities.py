from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime

from app.models.storage import load_data, save_data, ensure_data_keys, activity_assignments
from app.utils import log_action, login_required, admin_required

activities_bp = Blueprint('activities', __name__)


@activities_bp.route('/activities')
@login_required
def activities():
    data = load_data()
    ensure_data_keys(data)
    activities = data.get('activities', [])

    # Deduplicate activities with identical titles (case-insensitive, trimmed)
    # Reason: sometimes imports or backups can create multiple activity objects
    # with the same display title which results in repeated cards in the UI.
    seen_titles = set()
    unique_activities = []
    for a in activities:
        title_norm = (a.get('title') or '').strip().lower()
        if title_norm in seen_titles:
            # skip exact-title duplicates
            continue
        seen_titles.add(title_norm)
        unique_activities.append(a)
    activities = unique_activities

    # provide users to the template (used by admin assign panels)
    # Only include active users in activity lists/assignments and templates
    users = [u for u in data.get('users', []) if u.get('estado_user', 1) != 0]

    # assign a primary_section attribute to activities when missing, using simple keyword heuristics
    def determine_section(title):
        if not title:
            return 'Geral Voluntários'
        t = title.lower()
        cuidando_list = ['auriculoterapia', 'reiki']
        integracao_list = ['momento musical', 'projeto amigo bicho', 'anjos solidários', 'anjos solidarios', 'contadores de estória', 'contadores de estoria', 'origamis do bem', 'momento da beleza', 'momento beleza']
        treinamentos_list = ['formação dos voluntários', 'formacao dos voluntarios', 'acolher novos voluntários', 'acolher novos voluntarios', 'treinamentos realizados', 'treinamentos']
        atendimento_list = ['atendimento telefônico', 'atendimento telefonico', 'acompanhamento solidário', 'acompanhamento solidario', 'visita solidária', 'visita solidaria', 'acolhimento espiritual', 'acolhimento familiar', 'acolhimento familiar - utis - hsmc', 'acolhimento familiar - utis - huc', 'auxílio alimentação', 'auxilio alimentacao']
        grupo_palhacos_list = ['terapia intensiva do amor', 't.i.a', 'tia', 'sorindo', 'so­rindo', 'semeando amor', 'vol. da palhaçaria', 'vol da palhaca', 'vol da palhaçaria']
        grupo_palhacos_others = ['especialistas da alegria', 'avalanche do riso']
        projetos_parceiros = ['coral']

        for kw in atendimento_list:
            if kw in t:
                return 'Atendimento'
        for kw in integracao_list:
            if kw in t:
                return 'Integração'
        for kw in treinamentos_list:
            if kw in t:
                return 'Treinamentos'
        for kw in cuidando_list:
            if kw in t:
                return 'Cuidando de quem cuida'
        for kw in grupo_palhacos_list + grupo_palhacos_others:
            if kw in t:
                return 'Grupo de Palhaços'
        for kw in projetos_parceiros:
            if kw in t:
                return 'Projetos Parceiros'
        return 'Geral Voluntários'


    # normalize assignment structures
    for act in activities:
        activity_assignments(act)
        # ensure primary_section exists for grouping in the template
        if not act.get('primary_section'):
            act['primary_section'] = determine_section(act.get('title',''))

    # for each activity, compute whether current user has completed it today
    today = datetime.now().date().isoformat()
    completions = data.get('activity_completions', [])
    user_id = session.get('user_id')
    def completed_for_user(act):
        return any(c for c in completions if c.get('activity_id') == act['id'] and c.get('user_id') == user_id and c.get('date') == today)

    for a in activities:
        a['completed_today'] = completed_for_user(a)

    # compute active assignment counts for display
    for a in activities:
        assigned_objs = a.get('assigned_to', [])
        active_count = 0
        for ao in assigned_objs:
            if ao.get('removed_at') in (None, '', False):
                # count only if the assigned user is still active
                uid = ao.get('user_id')
                user_obj = next((u for u in data.get('users', []) if u.get('id') == uid), None)
                if not user_obj or user_obj.get('estado_user', 1) == 0:
                    continue
                active_count += 1
        a['active_assigned_count'] = active_count

    # If admin, compute additional stats: completions today count and recent completers
    if session.get('user_role') == 'admin':
        today = datetime.now().date().isoformat()
        comps = data.get('activity_completions', [])
        # map only active users for admin stats (exclude deactivated users)
        users = {u['id']: u for u in data.get('users', []) if u.get('estado_user', 1) != 0}
        for a in activities:
            c_today = [c for c in comps if c.get('activity_id') == a['id'] and c.get('date') == today]
            a['completions_today_count'] = len(c_today)
            names = []
            for c in sorted(c_today, key=lambda x: x.get('createdAt',''), reverse=True)[:5]:
                uid = c.get('user_id')
                u = users.get(uid, {})
                names.append(u.get('nome_completo') or u.get('nome') or uid)
            a['recent_completers_today'] = names
            # compute estimated value economizado today (hours * cost per hour)
            try:
                hrs = float(a.get('default_hours', 0) or 0)
                rate = float(a.get('hourly_cost', 0) or 0)
                a['value_per_session'] = round(hrs * rate, 2)
                a['value_saved_today'] = round(a['completions_today_count'] * a['value_per_session'], 2)
            except Exception:
                a['value_per_session'] = 0.0
                a['value_saved_today'] = 0.0

    return render_template('activities.html', user_name=session.get('user_name'), activities=activities, users=users)


@activities_bp.route('/activities/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_activity():
    data = load_data()
    ensure_data_keys(data)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description','')
        assigned = request.form.getlist('assigned') or []
        location = request.form.get('location_custom') or request.form.get('location','')
        # read optional economic fields
        try:
            default_hours = float(request.form.get('default_hours') or 0) if request.form.get('default_hours') else 1.0
        except Exception:
            default_hours = 1.0
        try:
            hourly_cost = float(request.form.get('hourly_cost') or 0) if request.form.get('hourly_cost') else 0.0
        except Exception:
            hourly_cost = 0.0

        new_act = {
            'id': str(len(data.get('activities', [])) + 1),
            'title': title,
            'description': description,
            'assigned_to': [],
            'location': location,
            'createdAt': datetime.now().isoformat(),
            'default_hours': default_hours,
            'hourly_cost': hourly_cost
        }
        now = datetime.now().isoformat()
        for uid in assigned:
            new_act['assigned_to'].append({'user_id': uid, 'assigned_at': now, 'removed_at': None})
        data.setdefault('activities', []).append(new_act)
        save_data(data)
        try:
            log_action(session.get('user_id'), 'activity_create', {'activity_id': new_act['id']})
        except Exception:
            pass
        return redirect(url_for('activities.activities'))

    users = [u for u in data.get('users', []) if u.get('estado_user', 1) != 0]
    return render_template('activity_form.html', user_name=session.get('user_name'), users=users, activity=None)


@activities_bp.route('/activities/edit/<act_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_activity(act_id):
    data = load_data()
    ensure_data_keys(data)
    act = next((a for a in data.get('activities', []) if a['id'] == act_id), None)
    if not act:
        flash('Atividade não encontrada', 'error')
        return redirect(url_for('activities.activities'))

    if request.method == 'POST':
        act['title'] = request.form.get('title')
        act['description'] = request.form.get('description','')
        new_assigned = request.form.getlist('assigned') or []
        act['location'] = request.form.get('location_custom') or request.form.get('location','')
        # update optional economic fields
        try:
            act['default_hours'] = float(request.form.get('default_hours') or act.get('default_hours') or 1.0)
        except Exception:
            act['default_hours'] = act.get('default_hours', 1.0)
        try:
            act['hourly_cost'] = float(request.form.get('hourly_cost') or act.get('hourly_cost') or 0.0)
        except Exception:
            act['hourly_cost'] = act.get('hourly_cost', 0.0)
        activity_assignments(act)
        now = datetime.now().isoformat()
        existing = { o.get('user_id'): o for o in act.get('assigned_to', []) }
        for uid in new_assigned:
            o = existing.get(uid)
            if o:
                if o.get('removed_at'):
                    o['removed_at'] = None
                    o['assigned_at'] = now
            else:
                act.setdefault('assigned_to', []).append({'user_id': uid, 'assigned_at': now, 'removed_at': None})
        for uid, o in existing.items():
            if uid not in new_assigned and not o.get('removed_at'):
                o['removed_at'] = now
        save_data(data)
        try:
            log_action(session.get('user_id'), 'activity_edit', {'activity_id': act_id})
        except Exception:
            pass
        return redirect(url_for('activities.activities'))

    users = [u for u in data.get('users', []) if u.get('estado_user', 1) != 0]
    activity_assignments(act)
    act['active_assigned_ids'] = [o.get('user_id') for o in act.get('assigned_to', []) if not o.get('removed_at')]
    return render_template('activity_form.html', user_name=session.get('user_name'), users=users, activity=act)


@activities_bp.route('/activities/delete/<act_id>', methods=['POST'])
@login_required
@admin_required
def delete_activity(act_id):
    data = load_data()
    ensure_data_keys(data)
    data['activities'] = [a for a in data.get('activities', []) if a['id'] != act_id]
    data['activity_completions'] = [c for c in data.get('activity_completions', []) if c.get('activity_id') != act_id]
    save_data(data)
    try:
        log_action(session.get('user_id'), 'activity_delete', {'activity_id': act_id})
    except Exception:
        pass
    flash('Atividade removida', 'success')
    return redirect(url_for('activities.activities'))


@activities_bp.route('/activities/toggle/<act_id>', methods=['POST'])
@login_required
def toggle_activity_completion(act_id):
    data = load_data()
    ensure_data_keys(data)
    uid = session.get('user_id')
    today = datetime.now().date().isoformat()
    existing = next((c for c in data.get('activity_completions', []) if c.get('activity_id') == act_id and c.get('user_id') == uid and c.get('date') == today), None)
    if existing:
        data['activity_completions'] = [c for c in data.get('activity_completions', []) if not (c.get('activity_id') == act_id and c.get('user_id') == uid and c.get('date') == today)]
        save_data(data)
        try:
            log_action(uid, 'activity_uncomplete', {'activity_id': act_id, 'date': today})
        except Exception:
            pass
        return jsonify({'status': 'removed'})
    else:
        newc = {
            'id': str(len(data.get('activity_completions', [])) + 1),
            'activity_id': act_id,
            'user_id': uid,
            'date': today,
            'createdAt': datetime.now().isoformat()
        }
        data.setdefault('activity_completions', []).append(newc)
        save_data(data)
        try:
            log_action(uid, 'activity_complete', {'activity_id': act_id, 'date': today})
        except Exception:
            pass
        return jsonify({'status': 'added'})


@activities_bp.route('/activities/assign/<act_id>', methods=['GET'])
@login_required
@admin_required
def assign_activity_page(act_id):
    data = load_data()
    ensure_data_keys(data)
    act = next((a for a in data.get('activities', []) if a.get('id') == act_id), None)
    if not act:
        flash('Atividade não encontrada', 'error')
        return redirect(url_for('activities.activities'))
    activity_assignments(act)
    users = [u for u in data.get('users', []) if u.get('estado_user', 1) != 0]
    return render_template('assign_activity.html', user_name=session.get('user_name'), activity=act, users=users)


@activities_bp.route('/activities/assign/<act_id>', methods=['POST'])
@login_required
@admin_required
def assign_activity(act_id):
    data = load_data()
    ensure_data_keys(data)
    act = next((a for a in data.get('activities', []) if a.get('id') == act_id), None)
    if not act:
        flash('Atividade não encontrada', 'error')
        return redirect(url_for('activities.activities'))

    activity_assignments(act)
    new_assigned = request.form.getlist('assigned') or []
    now = datetime.now().isoformat()
    existing = { o.get('user_id'): o for o in act.get('assigned_to', []) }
    for uid in new_assigned:
        o = existing.get(uid)
        if o:
            if o.get('removed_at'):
                o['removed_at'] = None
                o['assigned_at'] = now
        else:
            act.setdefault('assigned_to', []).append({'user_id': uid, 'assigned_at': now, 'removed_at': None})
    for uid, o in existing.items():
        if uid not in new_assigned and not o.get('removed_at'):
            o['removed_at'] = now

    save_data(data)
    try:
        log_action(session.get('user_id'), 'activity_assign', {'activity_id': act_id})
    except Exception:
        pass
    flash('Atribuições atualizadas', 'success')
    return redirect(url_for('activities.activities'))

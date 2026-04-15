from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime

from app.models.storage import load_data, save_data
from app.utils import log_action, login_required, admin_required

announcements_bp = Blueprint('announcements', __name__)


@announcements_bp.route('/announcements')
@login_required
def announcements():
    data = load_data()
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
            ann_copy['authorName'] = users_by_id[author_id].get('nome_completo') or users_by_id[author_id].get('nome') or 'Sistema'
        else:
            ann_copy['authorName'] = 'Sistema'

        announcements.append(ann_copy)

    return render_template('announcements.html', user_name=session.get('user_name'), announcements=announcements)


@announcements_bp.route('/announcements/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_announcement():
    if request.method == 'POST':
        data = load_data()
        new_ann = {
            'id': str(len(data.get('announcements', [])) + 1),
            'title': request.form.get('title'),
            'message': request.form.get('message'),
            'authorId': session.get('user_id'),
            'important': bool(request.form.get('important')),
            'createdAt': datetime.now().isoformat()
        }
        data.setdefault('announcements', []).append(new_ann)
        save_data(data)
        try:
            log_action(session.get('user_id'), 'announcement_create', {'announcement_id': new_ann['id'], 'title': new_ann.get('title')})
        except Exception:
            pass
        return redirect(url_for('announcements.announcements'))

    return render_template('announcement_form.html', user_name=session.get('user_name'), announcement=None)


@announcements_bp.route('/announcements/delete/<ann_id>')
@login_required
@admin_required
def delete_announcement(ann_id):
    data = load_data()
    data['announcements'] = [a for a in data.get('announcements', []) if a['id'] != ann_id]
    save_data(data)
    try:
        log_action(session.get('user_id'), 'announcement_delete', {'announcement_id': ann_id})
    except Exception:
        pass
    return redirect(url_for('announcements.announcements'))


@announcements_bp.route('/announcements/edit/<ann_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_announcement(ann_id):
    data = load_data()
    ann = next((a for a in data.get('announcements', []) if a['id'] == ann_id), None)
    if not ann:
        flash('Aviso não encontrado', 'error')
        return redirect(url_for('announcements.announcements'))

    if request.method == 'POST':
        ann['title'] = request.form.get('title')
        ann['message'] = request.form.get('message')
        ann['important'] = bool(request.form.get('important'))
        save_data(data)
        try:
            log_action(session.get('user_id'), 'announcement_edit', {'announcement_id': ann_id})
        except Exception:
            pass
        return redirect(url_for('announcements.announcements'))

    return render_template('announcement_form.html', user_name=session.get('user_name'), announcement=ann)

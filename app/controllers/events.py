from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime

from app.models.storage import load_data, save_data
from app.utils import login_required, admin_required

events_bp = Blueprint('events', __name__)


def parse_dt_or_none(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except Exception:
        return None


@events_bp.route('/events')
@login_required
def events():
    data = load_data()
    show_future = request.args.get('future') == '1'
    now = datetime.now()
    filtered = []
    for e in data.get('events', []):
        sa = parse_dt_or_none(e.get('scheduled_at'))
        if show_future:
            if sa is None or sa >= now:
                filtered.append(e)
        else:
            filtered.append(e)

    def _parse_sched_or_created(e):
        sa = parse_dt_or_none(e.get('scheduled_at'))
        if sa is not None:
            return sa
        ca = parse_dt_or_none(e.get('createdAt') or '')
        if ca is not None:
            return ca
        return datetime.max

    events = sorted(filtered, key=_parse_sched_or_created)
    return render_template('events.html', user_name=session.get('user_name'), events=events, show_future=show_future, is_admin=(session.get('user_role') == 'admin'))


@events_bp.route('/events/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_event():
    if request.method == 'POST':
        data = load_data()
        date_val = request.form.get('date','')
        time_val = request.form.get('time','')
        scheduled_at = ''
        if date_val and time_val:
            scheduled_at = f"{date_val}T{time_val}"
        elif date_val:
            scheduled_at = date_val
        # Also accept optional end date/time (data_fim) from the form
        end_date_val = request.form.get('end_date','')
        end_time_val = request.form.get('end_time','')
        scheduled_end = ''
        if end_date_val and end_time_val:
            scheduled_end = f"{end_date_val}T{end_time_val}"
        elif end_date_val:
            scheduled_end = end_date_val

        new_ev = {
            'id': str(len(data.get('events', [])) + 1),
            'title': request.form.get('title'),
            'description': request.form.get('description',''),
            'date': date_val or request.form.get('date',''),
            'scheduled_at': scheduled_at,
            'scheduled_end': scheduled_end,
            'location': request.form.get('location',''),
            'createdAt': datetime.now().isoformat(),
            'important': True if request.form.get('important') in ('1','on','true','True') else False
        }
        data.setdefault('events', []).append(new_ev)
        save_data(data)
        return redirect(url_for('events.events'))

    return render_template('event_form.html', user_name=session.get('user_name'))


@events_bp.route('/events/edit/<ev_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_event(ev_id):
    data = load_data()
    ev = next((e for e in data.get('events', []) if e.get('id') == ev_id), None)
    if not ev:
        flash('Evento não encontrado', 'error')
        return redirect(url_for('events.events'))

    if request.method == 'POST':
        ev['title'] = request.form.get('title')
        ev['description'] = request.form.get('description','')
        date_val = request.form.get('date','')
        time_val = request.form.get('time','')
        if date_val and time_val:
            ev['scheduled_at'] = f"{date_val}T{time_val}"
        elif date_val:
            ev['scheduled_at'] = date_val
        else:
            ev['scheduled_at'] = ''
        # handle optional end datetime
        end_date_val = request.form.get('end_date','')
        end_time_val = request.form.get('end_time','')
        if end_date_val and end_time_val:
            ev['scheduled_end'] = f"{end_date_val}T{end_time_val}"
        elif end_date_val:
            ev['scheduled_end'] = end_date_val
        else:
            ev['scheduled_end'] = ''
        ev['date'] = date_val
        ev['location'] = request.form.get('location','')
        # priority flag
        ev['important'] = True if request.form.get('important') in ('1','on','true','True') else False
        save_data(data)
        flash('Evento atualizado com sucesso', 'success')
        return redirect(url_for('events.events'))

    return render_template('event_form.html', user_name=session.get('user_name'), event=ev)


@events_bp.route('/events/delete/<ev_id>', methods=['POST'])
@login_required
@admin_required
def delete_event(ev_id):
    data = load_data()
    ev = next((e for e in data.get('events', []) if e.get('id') == ev_id), None)
    if not ev:
        flash('Evento não encontrado', 'error')
        return redirect(url_for('events.events'))

    # remove the event
    data['events'] = [e for e in data.get('events', []) if e.get('id') != ev_id]
    save_data(data)
    flash('Evento removido com sucesso', 'success')
    return redirect(url_for('events.events'))

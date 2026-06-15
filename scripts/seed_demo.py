"""Popula o data.json com dados de demonstração para os screenshots."""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from werkzeug.security import generate_password_hash
from app.models.storage import new_id

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data.json')

now = datetime.now()

def iso(dt):
    return dt.isoformat()

# ─── Usuários ───────────────────────────────────────────────────────────────
uid_admin  = new_id()
uid_maria  = new_id()
uid_joao   = new_id()
uid_ana    = new_id()
uid_carlos = new_id()

users = [
    {
        'id': uid_admin,
        'username': 'admin',
        'password': generate_password_hash('adm123'),
        'nome': 'Administrador',
        'sobrenome': '',
        'nome_completo': 'Administrador',
        'email': 'admin@cajuru.org.br',
        'role': 'admin',
        'phone': '(41) 99000-0000',
        'data_nascimento': '1985-03-15',
        'estado_user': 1,
        'createdAt': iso(now - timedelta(days=180)),
    },
    {
        'id': uid_maria,
        'username': 'maria.silva',
        'password': generate_password_hash('vol123'),
        'nome': 'Maria',
        'sobrenome': 'Silva',
        'nome_completo': 'Maria Silva',
        'email': 'maria.silva@email.com',
        'role': 'voluntario',
        'phone': '(41) 99111-2222',
        'data_nascimento': '1995-07-20',
        'estado_user': 1,
        'cpf': '123.456.789-00',
        'createdAt': iso(now - timedelta(days=90)),
    },
    {
        'id': uid_joao,
        'username': 'joao.santos',
        'password': generate_password_hash('vol123'),
        'nome': 'João',
        'sobrenome': 'Santos',
        'nome_completo': 'João Santos',
        'email': 'joao.santos@email.com',
        'role': 'voluntario',
        'phone': '(41) 99333-4444',
        'data_nascimento': '1988-11-05',
        'estado_user': 1,
        'cpf': '987.654.321-00',
        'createdAt': iso(now - timedelta(days=60)),
    },
    {
        'id': uid_ana,
        'username': 'ana.lima',
        'password': generate_password_hash('vol123'),
        'nome': 'Ana',
        'sobrenome': 'Lima',
        'nome_completo': 'Ana Lima',
        'email': 'ana.lima@email.com',
        'role': 'voluntario',
        'phone': '(41) 99555-6666',
        'data_nascimento': '2000-01-10',
        'estado_user': 1,
        'createdAt': iso(now - timedelta(days=30)),
    },
    {
        'id': uid_carlos,
        'username': 'carlos.mendes',
        'password': generate_password_hash('vol123'),
        'nome': 'Carlos',
        'sobrenome': 'Mendes',
        'nome_completo': 'Carlos Mendes',
        'email': 'carlos.mendes@email.com',
        'role': 'voluntario',
        'phone': '(41) 99777-8888',
        'data_nascimento': '1975-06-22',
        'estado_user': 1,
        'createdAt': iso(now - timedelta(days=15)),
    },
]

# ─── Registros de ponto ──────────────────────────────────────────────────────
clock_entries = []
for uid, name in [(uid_maria, 'Maria'), (uid_joao, 'João'), (uid_ana, 'Ana')]:
    for d in range(5):
        day = now - timedelta(days=d+1)
        entry_in = day.replace(hour=8, minute=0, second=0, microsecond=0)
        entry_out = day.replace(hour=12, minute=0, second=0, microsecond=0)
        clock_entries.append({
            'id': new_id(),
            'userId': uid,
            'userName': name,
            'username': name.lower().replace(' ', '.'),
            'type': 'in',
            'timestamp': iso(entry_in),
            'notes': '',
            'createdAt': iso(entry_in),
        })
        clock_entries.append({
            'id': new_id(),
            'userId': uid,
            'userName': name,
            'username': name.lower().replace(' ', '.'),
            'type': 'out',
            'timestamp': iso(entry_out),
            'notes': '',
            'createdAt': iso(entry_out),
        })

# ─── Atividades ──────────────────────────────────────────────────────────────
act_music  = new_id()
act_read   = new_id()
act_clown  = new_id()
act_train  = new_id()
act_care   = new_id()

activities = [
    {
        'id': act_music,
        'title': 'Musicoterapia',
        'description': 'Sessões de musicoterapia nas enfermarias pediátricas.',
        'emoji': '🎵',
        'primary_section': 'Atendimento',
        'hourly_cost': 75.00,
        'allow_multiple': True,
        'report_metrics': ['pacientes'],
        'assigned_to': [
            {'user_id': uid_maria, 'removed_at': None, 'assignedAt': iso(now - timedelta(days=30))},
            {'user_id': uid_joao, 'removed_at': None, 'assignedAt': iso(now - timedelta(days=20))},
        ],
        'createdAt': iso(now - timedelta(days=60)),
    },
    {
        'id': act_read,
        'title': 'Contação de Histórias',
        'description': 'Leitura e narração de histórias para crianças internadas.',
        'emoji': '📚',
        'primary_section': 'Atendimento',
        'hourly_cost': 50.00,
        'allow_multiple': True,
        'report_metrics': ['pacientes', 'acompanhantes'],
        'assigned_to': [
            {'user_id': uid_ana, 'removed_at': None, 'assignedAt': iso(now - timedelta(days=25))},
        ],
        'createdAt': iso(now - timedelta(days=55)),
    },
    {
        'id': act_clown,
        'title': 'Palhaços do Coração',
        'description': 'Visitas de palhaços terapêuticos para alegrar os pacientes.',
        'emoji': '🤡',
        'primary_section': 'Grupo de Palhaços',
        'hourly_cost': 60.00,
        'allow_multiple': False,
        'report_metrics': ['pacientes'],
        'assigned_to': [
            {'user_id': uid_carlos, 'removed_at': None, 'assignedAt': iso(now - timedelta(days=10))},
            {'user_id': uid_joao, 'removed_at': None, 'assignedAt': iso(now - timedelta(days=5))},
        ],
        'createdAt': iso(now - timedelta(days=40)),
    },
    {
        'id': act_train,
        'title': 'Capacitação Humanização',
        'description': 'Treinamento de humanização do atendimento hospitalar.',
        'emoji': '🎓',
        'primary_section': 'Treinamentos',
        'hourly_cost': 80.00,
        'allow_multiple': False,
        'report_metrics': ['colaboradores'],
        'assigned_to': [],
        'createdAt': iso(now - timedelta(days=20)),
    },
    {
        'id': act_care,
        'title': 'Roda de Conversa — Equipe',
        'description': 'Apoio emocional à equipe de saúde.',
        'emoji': '💬',
        'primary_section': 'Cuidando de quem cuida',
        'hourly_cost': 70.00,
        'allow_multiple': False,
        'report_metrics': ['colaboradores'],
        'assigned_to': [
            {'user_id': uid_maria, 'removed_at': None, 'assignedAt': iso(now - timedelta(days=15))},
        ],
        'createdAt': iso(now - timedelta(days=30)),
    },
]

# ─── Completions de atividade ─────────────────────────────────────────────────
activity_completions = []
for uid in [uid_maria, uid_joao]:
    for d in range(3):
        activity_completions.append({
            'id': new_id(),
            'activity_id': act_music,
            'user_id': uid,
            'count': 3,
            'attendance_type': 'pacientes',
            'unit_scope': 'UTI 1',
            'createdAt': iso(now - timedelta(days=d+1)),
        })
for d in range(2):
    activity_completions.append({
        'id': new_id(),
        'activity_id': act_clown,
        'user_id': uid_carlos,
        'count': 1,
        'attendance_type': 'pacientes',
        'unit_scope': '',
        'createdAt': iso(now - timedelta(days=d+1)),
    })

# ─── Avisos ───────────────────────────────────────────────────────────────────
announcements = [
    {
        'id': new_id(),
        'title': 'Reunião Mensal de Voluntários',
        'message': 'Convidamos todos os voluntários para a reunião mensal que acontecerá na próxima sexta-feira, às 14h, na sala de treinamentos. Pauta: balanço das atividades do mês e planejamento para o próximo período.',
        'authorId': uid_admin,
        'authorName': 'Administrador',
        'important': True,
        'is_new': True,
        'createdAt': iso(now - timedelta(days=2)),
    },
    {
        'id': new_id(),
        'title': 'Atualização do Crachá',
        'message': 'Lembramos que todos os voluntários devem atualizar o crachá de identificação até o final deste mês. Compareça à recepção com documento com foto.',
        'authorId': uid_admin,
        'authorName': 'Administrador',
        'important': False,
        'is_new': False,
        'createdAt': iso(now - timedelta(days=10)),
    },
    {
        'id': new_id(),
        'title': 'Semana do Voluntariado',
        'message': 'De 15 a 21 de setembro celebramos a Semana Nacional do Voluntariado. Programação especial em breve! Contamos com a presença de todos.',
        'authorId': uid_admin,
        'authorName': 'Administrador',
        'important': False,
        'is_new': False,
        'createdAt': iso(now - timedelta(days=20)),
    },
]

# ─── Eventos ─────────────────────────────────────────────────────────────────
events = [
    {
        'id': new_id(),
        'title': 'Capacitação: Saúde Mental e Voluntariado',
        'description': 'Workshop sobre saúde mental para voluntários. Parceria com a psicologia do hospital. Presença obrigatória para novos voluntários.',
        'scheduled_at': iso(now + timedelta(days=7)),
        'scheduled_end': iso(now + timedelta(days=7, hours=3)),
        'location': 'Auditório Principal',
        'important': True,
        'createdAt': iso(now - timedelta(days=5)),
    },
    {
        'id': new_id(),
        'title': 'Bingo Beneficente',
        'description': 'Bingo organizado pelos voluntários para arrecadar fundos para a ala pediátrica.',
        'scheduled_at': iso(now + timedelta(days=14)),
        'scheduled_end': iso(now + timedelta(days=14, hours=4)),
        'location': 'Pátio do Hospital',
        'important': False,
        'createdAt': iso(now - timedelta(days=3)),
    },
    {
        'id': new_id(),
        'title': 'Entrega de Presentes — Natal',
        'description': 'Distribuição de presentes para as crianças internadas na época do Natal.',
        'scheduled_at': iso(now + timedelta(days=30)),
        'scheduled_end': '',
        'location': 'Ala Pediátrica',
        'important': True,
        'createdAt': iso(now - timedelta(days=1)),
    },
]

# ─── Escalas ─────────────────────────────────────────────────────────────────
schedules = [
    {'id': new_id(), 'userId': uid_maria,  'day': 'seg', 'start': '08:00', 'end': '12:00', 'createdAt': iso(now)},
    {'id': new_id(), 'userId': uid_maria,  'day': 'qua', 'start': '08:00', 'end': '12:00', 'createdAt': iso(now)},
    {'id': new_id(), 'userId': uid_joao,   'day': 'ter', 'start': '09:00', 'end': '13:00', 'createdAt': iso(now)},
    {'id': new_id(), 'userId': uid_joao,   'day': 'qui', 'start': '09:00', 'end': '13:00', 'createdAt': iso(now)},
    {'id': new_id(), 'userId': uid_ana,    'day': 'sex', 'start': '14:00', 'end': '18:00', 'createdAt': iso(now)},
    {'id': new_id(), 'userId': uid_carlos, 'day': 'sab', 'start': '10:00', 'end': '14:00', 'createdAt': iso(now)},
]

# ─── Intenções de voluntariado ────────────────────────────────────────────────
intents = [
    {
        'idintencao': new_id(),
        'hospital': 'Hospital Cajuru',
        'nome': 'Fernanda Costa',
        'data_nascimento': '1998-04-12',
        'local_nascimento': 'Curitiba/PR',
        'rg': '12.345.678-9',
        'cpf': '111.222.333-44',
        'estado_civil': 'Solteira',
        'nome_conjuge': '',
        'nome_pai': 'Roberto Costa',
        'nome_mae': 'Sandra Costa',
        'endereco': 'Rua das Flores, 123, Bairro Alto, Curitiba/PR',
        'telefone_residencial': '(41) 3333-4444',
        'celular': '(41) 99888-7766',
        'religiao': 'Católica',
        'email': 'fernanda.costa@email.com',
        'escolaridade_curso': 'Superior Completo — Enfermagem',
        'local_trabalho': 'Clínica São Lucas',
        'telefone_trabalho': '(41) 3222-5555',
        'ocupacao': 'Enfermeira',
        'ocupacao_outro': '',
        'acomp_med': 'Não',
        'transporte': 'Carro próprio',
        'ficou_sab': 'Aos sábados',
        'ja_volunt': 'Sim',
        'ja_volunt_onde': 'Cruz Vermelha Brasileira',
        'faz_volunt': 'Não',
        'contrib_ser': 'Gostaria de contribuir com minha experiência em saúde para ajudar pacientes.',
        'hab_musical': 'Sim',
        'hab_musical_qual': 'Violão',
        'aux_alimentacao': 'Não',
        'createdAt': iso(now - timedelta(days=3)),
    },
    {
        'idintencao': new_id(),
        'hospital': 'Hospital Cajuru',
        'nome': 'Rafael Oliveira',
        'data_nascimento': '1990-08-25',
        'local_nascimento': 'São Paulo/SP',
        'rg': '98.765.432-1',
        'cpf': '555.666.777-88',
        'estado_civil': 'Casado',
        'nome_conjuge': 'Camila Oliveira',
        'nome_pai': 'Paulo Oliveira',
        'nome_mae': 'Lúcia Oliveira',
        'endereco': 'Av. Brasil, 456, Centro, Curitiba/PR',
        'telefone_residencial': '',
        'celular': '(41) 99444-3322',
        'religiao': 'Evangélica',
        'email': 'rafael.oliveira@email.com',
        'escolaridade_curso': 'Ensino Médio Completo',
        'local_trabalho': 'Supermercado BomPreço',
        'telefone_trabalho': '',
        'ocupacao': 'Vendedor',
        'ocupacao_outro': '',
        'acomp_med': 'Não',
        'transporte': 'Ônibus',
        'ficou_sab': 'Aos domingos',
        'ja_volunt': 'Não',
        'ja_volunt_onde': '',
        'faz_volunt': 'Não',
        'contrib_ser': 'Quero ajudar pessoas que precisam e contribuir com meu tempo.',
        'hab_musical': 'Não',
        'hab_musical_qual': '',
        'aux_alimentacao': 'Sim',
        'createdAt': iso(now - timedelta(days=1)),
    },
]

# ─── Salvar ────────────────────────────────────────────────────────────────────
data = {
    'users': users,
    'clock_entries': clock_entries,
    'activities': activities,
    'activity_completions': activity_completions,
    'announcements': announcements,
    'events': events,
    'schedules': schedules,
    'intents': intents,
}

with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✓ data.json criado com dados de demonstração em: {DATA_FILE}")
print(f"  {len(users)} usuários, {len(clock_entries)} registros de ponto, {len(activities)} atividades")
print(f"  {len(announcements)} avisos, {len(events)} eventos, {len(schedules)} escalas, {len(intents)} intenções")

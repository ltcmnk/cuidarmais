#!/usr/bin/env python3
"""
Migration script to canonicalize user fields in data.json.
- For each user object, ensure keys: nome, sobrenome, nome_completo, data_nascimento
- If legacy 'name' exists, split into nome/sobrenome and set nome_completo
- If legacy 'birthdate' exists, copy to data_nascimento
- Remove legacy keys 'name' and 'birthdate'
- Backup original data.json to data.json.bak.TIMESTAMP
"""
import json
import shutil
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data.json'

if not DATA_FILE.exists():
    print('data.json not found at', DATA_FILE)
    raise SystemExit(1)

bak = ROOT / f"data.json.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
shutil.copy2(DATA_FILE, bak)
print('Backup written to', bak)

with DATA_FILE.open('r', encoding='utf-8') as f:
    data = json.load(f)

users = data.get('users', [])
changed = 0
for u in users:
    orig = dict(u)
    name_legacy = u.get('name')
    # Ensure nome and sobrenome
    nome = u.get('nome')
    sobrenome = u.get('sobrenome')
    nome_completo = u.get('nome_completo')

    if not nome and name_legacy:
        parts = name_legacy.split()
        if parts:
            nome = parts[0]
            sobrenome = parts[-1] if len(parts) > 1 else ''
    if not nome and nome_completo:
        parts = nome_completo.split()
        if parts:
            nome = parts[0]
            sobrenome = parts[-1] if len(parts) > 1 else ''
    if not nome:
        # leave empty string to avoid None
        nome = ''
    if sobrenome is None:
        sobrenome = ''
    # Build nome_completo
    if not nome_completo:
        if nome and sobrenome:
            nome_completo = f"{nome} {sobrenome}".strip()
        elif nome:
            nome_completo = nome
        elif name_legacy:
            nome_completo = name_legacy
        else:
            nome_completo = ''

    # Migrate birthdate -> data_nascimento
    if 'birthdate' in u and not u.get('data_nascimento'):
        u['data_nascimento'] = u.get('birthdate', '')

    # Assign canonical fields
    u['nome'] = nome
    u['sobrenome'] = sobrenome
    u['nome_completo'] = nome_completo

    # Remove legacy keys
    if 'name' in u:
        del u['name']
    if 'birthdate' in u:
        del u['birthdate']

    if any(u.get(k) != orig.get(k) for k in ('nome','sobrenome','nome_completo','data_nascimento')):
        changed += 1

print(f'Migrating {len(users)} users, updated {changed} user records')

# Write back file
with DATA_FILE.open('w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('data.json updated')

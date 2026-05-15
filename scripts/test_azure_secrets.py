"""Test at load_env() i intake-server.py henter secrets fra Azure Key Vault.

Importerer modulen — den kjører load_env() ved import.
Skriver ut HVOR hver secret kom fra og LENGDEN på verdien (aldri verdien selv).

Kjør: python scripts\test_azure_secrets.py
"""
import os
import sys
from pathlib import Path

# La oss importere intake-server uten å starte HTTP-loopen.
# load_env() kjører ved import, men HTTPServer-instansieringen er gated bak __name__ == '__main__'.
# Sjekker først:
intake_path = Path(__file__).resolve().parent.parent / 'intake-server.py'
source = intake_path.read_text(encoding='utf-8')
assert 'if __name__' in source, 'intake-server.py må gate HTTP-loop bak __name__ == "__main__"'

# Importer modulen
sys.path.insert(0, str(intake_path.parent))
# Filnavnet har bindestrek så vanlig import virker ikke — bruk importlib
import importlib.util
spec = importlib.util.spec_from_file_location('intake_server', intake_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

print()
print('Secrets etter load_env():')
print('-' * 60)
expected = ['HALO_CLIENT_ID', 'HALO_CLIENT_SECRET', 'MAILGUN_API_KEY', 'TURNSTILE_SECRET']
ok = True
for key in expected:
    val = os.environ.get(key, '')
    if val:
        print(f'  {key:25s} OK   (len={len(val)})')
    else:
        print(f'  {key:25s} TOM')
        if key != 'TURNSTILE_SECRET':  # Turnstile er valgfri
            ok = False

print('-' * 60)
print('PASS' if ok else 'FAIL — én eller flere kritiske secrets mangler')
sys.exit(0 if ok else 1)

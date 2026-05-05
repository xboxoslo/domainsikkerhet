"""Engangs-test: rendre shield PNG-er lokalt for visuell sjekk."""
import importlib.util
spec = importlib.util.spec_from_file_location('intake', 'intake-server.py')
import os
os.environ.setdefault('HALO_CLIENT_ID', 'x')
os.environ.setdefault('HALO_CLIENT_SECRET', 'x')
os.environ.setdefault('MAILGUN_API_KEY', 'x')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

for s in [100, 88, 75, 60, 40, 15]:
    grade, gc, gcl = mod.grade_palette(s)
    png = mod.render_shield_png(grade, gc, gcl)
    fn = f'shield_test_{s}.png'
    open(fn, 'wb').write(png)
    print(f'  score={s:3d} grade={grade:2s} -> {fn} ({len(png)} bytes)')

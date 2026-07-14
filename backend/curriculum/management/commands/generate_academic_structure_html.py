from django.core.management.base import BaseCommand
from curriculum.models import Filiere, Module
import os
from collections import OrderedDict, defaultdict


class Command(BaseCommand):
    help = "Génère un fichier HTML de la structure académique"

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o', default=None,
            help='Chemin du fichier HTML de sortie (défaut: academic_structure.html)',
        )

    def handle(self, *args, **options):
        output = options['output']
        if output is None:
            output = os.path.join(os.getcwd(), 'academic_structure.html')

        # Fetch all data in 3 queries
        filieres = list(Filiere.objects.all().select_related('semestre', 'department'))
        modules = list(Module.objects.all().select_related('filiere'))

        # Index modules by filiere_id
        modules_by_filiere = defaultdict(list)
        for m in modules:
            modules_by_filiere[m.filiere_id].append(m)

        # Group filieres
        grouped = OrderedDict()
        for f in filieres:
            grouped.setdefault(f.name, OrderedDict()).setdefault(f.niveau or "N/A", []).append(f)

        total_semestres = 0
        total_modules = 0

        html_parts = []
        html_parts.append("""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Structure Académique — ESTO</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f2f5; color: #333; padding: 30px; }
  .container { max-width: 1100px; margin: 0 auto; }
  h1 { color: #1a1a2e; border-bottom: 3px solid #1a1a2e; padding-bottom: 8px; margin: 30px 0 20px; font-size: 20px; }
  h1:first-of-type { margin-top: 0; }
  .subtitle { color: #555; font-size: 14px; margin-bottom: 25px; }
  h2 { color: #16213e; margin: 20px 0 10px; font-size: 16px; border-left: 4px solid #0f3460; padding-left: 10px; }
  h3 { color: #0f3460; margin: 12px 0 6px; font-size: 14px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 13px; }
  th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
  th { background: #1a1a2e; color: #fff; font-weight: 600; }
  tr:nth-child(even) { background: #f8f9fa; }
  tr.total-row { background: #e9ecef; font-weight: bold; }
  .filiere-info { color: #555; font-size: 13px; margin-bottom: 8px; }
  .toc { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 25px; }
  .toc a { color: #0f3460; text-decoration: none; display: block; padding: 3px 0; }
  .toc a:hover { text-decoration: underline; }
  .section { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }
  @media print { body { background: #fff; padding: 10px; } .section { box-shadow: none; border: 1px solid #ddd; } }
</style>
</head>
<body>
<div class="container">
  <h1 style="text-align:center;">Structure Académique</h1>
  <p class="subtitle" style="text-align:center;">Université Mohammed Ier — École Supérieure de Technologie d'Oujda</p>
""")

        overview_rows = ""
        for fname, niveaux in grouped.items():
            for niv, entries in niveaux.items():
                mod_ids = [f.id for f in entries]
                n_m = sum(len(modules_by_filiere.get(fid, [])) for fid in mod_ids)
                n_s = len(entries)
                total_modules += n_m
                total_semestres += n_s
                overview_rows += f"<tr><td>{fname}</td><td>{niv}</td><td>{n_s}</td><td>{n_m}</td></tr>"

        html_parts.append(f"""
  <h1>Aperçu général</h1>
  <table>
    <tr><th>Filière</th><th>Niveau</th><th>Semestres</th><th>Modules</th></tr>
    {overview_rows}
    <tr class="total-row"><td>TOTAL</td><td></td><td>{total_semestres}</td><td>{total_modules}</td></tr>
  </table>
""")

        toc_items = ""
        for idx, fname in enumerate(grouped.keys(), 1):
            toc_items += f"    <a href='#f{idx}'>{idx}. {fname}</a>"

        html_parts.append(f"""
  <h1>Table des matières</h1>
  <div class="toc">
    {toc_items}
  </div>
""")

        for idx, (fname, niveaux) in enumerate(grouped.items(), 1):
            html_parts.append(f"<div class='section'><h1 id='f{idx}'>{fname}</h1>")

            depts = set()
            for entries in niveaux.values():
                for f in entries:
                    if f.department:
                        depts.add(f.department.name)
            if depts:
                html_parts.append(f"<p class='filiere-info'>Département(s) : {', '.join(sorted(depts))}</p>")

            for niv, entries in niveaux.items():
                mod_ids = [f.id for f in entries]
                n_m = sum(len(modules_by_filiere.get(fid, [])) for fid in mod_ids)
                html_parts.append(f"<h2>{niv} — {n_m} modules</h2>")

                for f in entries:
                    sem = f.semestre.name
                    f_modules = sorted(modules_by_filiere.get(f.id, []), key=lambda x: x.name)
                    html_parts.append(f"<h3>Semestre {sem}</h3>")

                    if f_modules:
                        html_parts.append("""<table><tr><th>#</th><th>Module</th><th>Code</th><th>Coeff.</th><th>H. totales</th></tr>""")
                        for i, m in enumerate(f_modules, 1):
                            code = m.code if m.code else "—"
                            hours = str(m.total_hours) if m.total_hours else "—"
                            html_parts.append(f"<tr><td>{i}</td><td>{m.name}</td><td>{code}</td><td>{m.coefficient}</td><td>{hours}</td></tr>")
                        html_parts.append("</table>")
                    else:
                        html_parts.append("<p><i>Aucun module</i></p>")

            html_parts.append("</div>")

        html_parts.append("</div></body></html>")

        with open(output, 'w', encoding='utf-8') as f:
            f.write("\n".join(html_parts))

        self.stdout.write(self.style.SUCCESS(f"HTML généré : {output}"))
        self.stdout.write(f"Total : {len(grouped)} filières, {total_semestres} semestres, {total_modules} modules")

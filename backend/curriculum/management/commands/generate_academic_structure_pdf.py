from django.core.management.base import BaseCommand
from curriculum.models import Filiere, Module
import os
from collections import OrderedDict


def generate_pdf(filepath):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, mm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, ListFlowable, ListItem
        )
    except ImportError:
        print("reportlab is not installed. Run: pip install reportlab")
        return

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=18, leading=22, spaceAfter=6,
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Normal'],
        fontSize=12, leading=14, spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#555555'),
    )
    h1_style = ParagraphStyle(
        'H1', parent=styles['Heading1'],
        fontSize=14, leading=17, spaceBefore=20, spaceAfter=8,
        textColor=colors.HexColor('#1a1a2e'),
    )
    h2_style = ParagraphStyle(
        'H2', parent=styles['Heading2'],
        fontSize=12, leading=15, spaceBefore=14, spaceAfter=6,
        textColor=colors.HexColor('#16213e'),
    )
    h3_style = ParagraphStyle(
        'H3', parent=styles['Heading3'],
        fontSize=10, leading=13, spaceBefore=10, spaceAfter=4,
        textColor=colors.HexColor('#0f3460'),
    )
    normal_style = ParagraphStyle(
        'CustomNormal', parent=styles['Normal'],
        fontSize=9, leading=11,
    )
    cell_style = ParagraphStyle(
        'CellStyle', parent=styles['Normal'],
        fontSize=8, leading=10,
    )
    tocentry_style = ParagraphStyle(
        'TOCEntry', parent=styles['Normal'],
        fontSize=10, leading=14,
        leftIndent=10,
    )

    col_header_style = ParagraphStyle(
        'ColHeader', parent=styles['Normal'],
        fontSize=8, leading=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    elements = []

    # Title
    elements.append(Spacer(1, 3*cm))
    elements.append(Paragraph("Structure Académique", title_style))
    elements.append(Paragraph("Université Mohammed Ier — École Supérieure de Technologie d'Oujda", subtitle_style))
    elements.append(Spacer(1, 1*cm))

    # Fetch and group data
    filieres = Filiere.objects.all().select_related('semestre', 'department').prefetch_related('modules')
    filieres = filieres.order_by('name', 'semestre__name')

    grouped = OrderedDict()
    for f in filieres:
        key = f.name
        if key not in grouped:
            grouped[key] = OrderedDict()
        niv = f.niveau if f.niveau else "N/A"
        if niv not in grouped[key]:
            grouped[key][niv] = []
        grouped[key][niv].append(f)

    # Page 1: overview table
    elements.append(Paragraph("Aperçu général", h1_style))
    overview_data = [["Filière", "Niveau", "Semestres", "Modules"]]
    total_modules = 0
    total_semestres = 0
    for fname, niveaux in grouped.items():
        for niv, entries in niveaux.items():
            mod_ids = [f.id for f in entries]
            n_m = Module.objects.filter(filiere_id__in=mod_ids).count()
            n_s = len(entries)
            total_modules += n_m
            total_semestres += n_s
            overview_data.append([
                Paragraph(fname, cell_style),
                Paragraph(niv, cell_style),
                Paragraph(str(n_s), cell_style),
                Paragraph(str(n_m), cell_style),
            ])
    overview_data.append([
        Paragraph("<b>TOTAL</b>", cell_style),
        Paragraph("", cell_style),
        Paragraph(f"<b>{total_semestres}</b>", cell_style),
        Paragraph(f"<b>{total_modules}</b>", cell_style),
    ])

    col_w = [10*cm, 3.5*cm, 2.5*cm, 2.5*cm]
    overview_table = Table(overview_data, colWidths=col_w, repeatRows=1)
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.HexColor('#f8f9fa'), colors.white]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e9ecef')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(overview_table)
    elements.append(PageBreak())

    # Table of Contents
    elements.append(Paragraph("Table des matières", h1_style))
    for idx, fname in enumerate(grouped.keys(), 1):
        elements.append(Paragraph(f"{idx}. {fname}", tocentry_style))
    elements.append(PageBreak())

    # Detail pages
    for fname, niveaux in grouped.items():
        elements.append(Paragraph(fname, h1_style))

        # Collect department info
        depts = set()
        for entries in niveaux.values():
            for f in entries:
                if f.department:
                    depts.add(f.department.name)
        if depts:
            elements.append(Paragraph(f"Département(s) : {', '.join(sorted(depts))}", normal_style))
            elements.append(Spacer(1, 4))

        for niv, entries in niveaux.items():
            # Get module count for this niveau
            mod_ids = [f.id for f in entries]
            n_m = Module.objects.filter(filiere_id__in=mod_ids).count()
            elements.append(Paragraph(f"{niv} — {n_m} modules", h2_style))

            for f in entries:
                sem = f.semestre.name
                modules_qs = Module.objects.filter(filiere=f).order_by('name')

                elements.append(Paragraph(f"Semestre {sem}", h3_style))

                mod_data = [["#", "Module", "Code", "Coeff.", "H. totales"]]
                for i, m in enumerate(modules_qs, 1):
                    mod_data.append([
                        Paragraph(str(i), cell_style),
                        Paragraph(m.name, cell_style),
                        Paragraph(m.code if m.code else "—", cell_style),
                        Paragraph(str(m.coefficient), cell_style),
                        Paragraph(str(m.total_hours) if m.total_hours else "—", cell_style),
                    ])

                if len(mod_data) > 1:
                    mod_col_w = [1*cm, 8*cm, 3*cm, 1.5*cm, 2*cm]
                    mod_table = Table(mod_data, colWidths=mod_col_w, repeatRows=1)
                    mod_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3460')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f5')]),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 2),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ]))
                    elements.append(mod_table)
                else:
                    elements.append(Paragraph("<i>Aucun module</i>", normal_style))

                elements.append(Spacer(1, 4))

        elements.append(PageBreak())

    doc.build(elements)
    print(f"PDF généré : {filepath}")
    print(f"Total : {len(grouped)} filières, {total_semestres} semestres, {total_modules} modules")


class Command(BaseCommand):
    help = "Génère un PDF de la structure académique (Filières, Semestres, Modules)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o',
            default=None,
            help='Chemin du fichier PDF de sortie (défaut: academic_structure.pdf)',
        )

    def handle(self, *args, **options):
        output = options['output']
        if output is None:
            output = os.path.join(os.getcwd(), 'academic_structure.pdf')

        generate_pdf(output)

import re
from functools import lru_cache

from django.core.cache import cache
from django.utils.cache import patch_cache_control

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from rest_framework import status

from users.models import User
from users.permissions import IsAdmin, IsAdminOrTeacher, apply_role_filtering, get_user_department, get_user_filiere_ids

from .models import Filiere, Module, NIVEAU_CHOICES, Semestre
from .serializers import FiliereSerializer, ModuleSerializer, SemestreSerializer


CACHE_TTL = 300  # 5 minutes


def _cache_key(*parts):
    raw = ":".join(str(p) for p in parts)
    safe = re.sub(r'[^a-zA-Z0-9_:.-]', '_', raw)
    return f"curric:{safe}"


def _cached_response(key, ttl=CACHE_TTL):
    cached = cache.get(key)
    if cached is not None:
        resp = Response(cached)
        patch_cache_control(resp, max_age=ttl)
        return resp
    return None


# ---------------------------------------------------------------------------
# FS-UMI (Faculte des Sciences - Universite Moulay Ismail) Academic Data
# ---------------------------------------------------------------------------
FS_UMI_DATA = {
    "LIC": {
        "S1": {
            "Biologie Cellulaire et Physiologie Humaine": [
                "Biologie Cellulaire et Histologie", "Geologie Generale",
                "Atomistique et Liaison Chimique", "Physique 1: Thermodynamique Mecanique",
                "Mathematiques", "Langues Etrangeres", "Methodologie de Travail Universitaire"
            ],
            "Chimie Organique et Bioorganique": [
                "Atomistique et liaison chimique", "Thermochimie", "Analyse",
                "Mecanique du point", "Thermodynamique", "Langues etrangeres",
                "Methodologie de travail universitaire"
            ],
            "Chimie Physique Appliquee et Environnement": [
                "Atomistique et liaison chimique", "Thermochimie", "Analyse",
                "Thermodynamique", "Mecanique du point", "Langues Etrangeres",
                "Methodologie de travail universitaire"
            ],
            "Digitalisation": [
                "Analyse 1", "Algebre 1", "Electronique numerique",
                "Algorithmique 1", "Programmation C 1", "Langues Etrangeres",
                "Methodologie de travail universitaire"
            ],
            "Electronique et Systemes": [
                "Mecanique du point", "Thermodynamique", "Analyse",
                "Atomistique/Liaison Chimique", "Thermochimie", "Langues Etrangeres",
                "Methodologie de travail universitaire"
            ],
            "Genie Informatique": [
                "Analyse 1", "Algebre 1", "Mecanique du point", "Thermodynamique",
                "Informatique 1: Algorithmique 1/Python", "Langues Etrangeres",
                "Methodologie de travail universitaire"
            ],
            "Geosciences et Geologie de l'Ingenieur": [
                "Biologie Cellulaire et Histologie", "Geologie Generale",
                "Atomistique et Liaison Chimique", "Physique 1: Thermodynamique Mecanique",
                "Mathematiques", "Methodologie de travail universitaire", "Langues Etrangeres"
            ],
            "Hydrologie et Hydrogeologie": [
                "Biologie Cellulaire et Histologie", "Geologie Generale",
                "Atomistique et Liaison Chimique", "Physique 1: Thermodynamique Mecanique",
                "Mathematiques", "Methodologie de travail universitaire", "Langues Etrangeres"
            ],
            "Materiaux et Energetique": [
                "Analyse", "Thermodynamique", "Mecanique du point",
                "Atomistique / Liaison Chimique", "Thermochimie", "Langues Etrangeres",
                "Methodologie de travail universitaire"
            ],
            "Mathematiques et Applications": [
                "Analyse 1", "Algebre 1", "Mecanique du point", "Thermodynamique",
                "Informatique 1", "Langues Etrangeres", "Methodologie de travail universitaire"
            ],
        },
        "S2": {
            "Biologie Cellulaire et Physiologie Humaine": [
                "Biologie des Organismes Animaux et Vegetaux", "Geodynamique",
                "Chimie des Solutions et Initiation a la Chimie Organique",
                "Physique 2: Optique Electricite", "Informatique", "Langues Etrangeres",
                "Culture Digitale"
            ],
            "Chimie Organique et Bioorganique": [
                "Chimie organique generale", "Chimie en solution",
                "Electrostatique et magnetostatique", "Optique geometrique",
                "Algebre", "Langues etrangeres", "Culture digitale"
            ],
            "Chimie Physique Appliquee et Environnement": [
                "Algebre", "Optique geometrique", "Electrostatique et magnetostatique",
                "Chimie Organique generale", "Chimie en solution", "Langues Etrangeres",
                "Culture digitale"
            ],
            "Digitalisation": [
                "Analyse 2", "Algebre 2", "Traitement du signal",
                "Algorithmique 2", "Programmation C 2", "Langues Etrangeres",
                "Culture digitale"
            ],
            "Electronique et Systemes": [
                "Optique geometrique", "Electrostatique et magnetostatique",
                "Chimie Organique generale", "Algebre", "Chimie en solution",
                "Langues Etrangeres", "Digital culture"
            ],
            "Genie Informatique": [
                "Analyse 2", "Algebre 2", "Electrostatique et magnetostatique",
                "Optique geometrique", "Informatique 2: Algorithmique 2/Python",
                "Langues Etrangeres", "Culture digitale"
            ],
            "Geosciences et Geologie de l'Ingenieur": [
                "Biologie des Organismes Animaux et Vegetaux", "Geodynamique",
                "Chimie des solutions et Initiation a la Chimie Organique",
                "Physique II: Optique et Electricite", "Informatique", "Langues Etrangeres",
                "Culture digitale"
            ],
            "Hydrologie et Hydrogeologie": [
                "Biologie des Organismes Animaux et Vegetaux", "Geodynamique",
                "Chimie des solutions et Initiation a la Chimie Organique",
                "Physique 2: Optique Electricite", "Informatique", "Langues Etrangeres",
                "Culture digitale"
            ],
            "Materiaux et Energetique": [
                "Algebre", "Optique geometrique", "Electrostatique et magnetostatique",
                "Chimie organique generale", "Chimie en solution", "Langues Etrangeres",
                "Culture digitale"
            ],
            "Mathematiques et Applications": [
                "Analyse 2", "Algebre 2", "Electrostatique et magnetostatique",
                "Optique geometrique", "Informatique 2: Algorithmique 2/Python",
                "Langues Etrangeres", "Culture digitale"
            ],
        },
        "S3": {
            "Biologie Cellulaire et Physiologie Humaine": [
                "Ecologie Generale", "Techniques d'Analyse", "Biochimie Structurale",
                "Microbiologie Generale", "Biostatistique", "Langues Etrangeres",
                "Culture and Art Skills"
            ],
            "Chimie Organique et Bioorganique": [
                "Hydrocarbures et fonctions monovalentes", "Chimie des electrolytes",
                "Chimie descriptive / Diagrammes de phases", "Mecanique quantique",
                "Mathematiques pour la chimie", "Langues etrangeres",
                "Histoire, art et patrimoine du Maroc"
            ],
            "Chimie Physique Appliquee et Environnement": [
                "Chimie des electrolytes", "Hydrocarbures et Fonctions Monovalentes",
                "Chimie descriptive I et Diagrammes de phases", "Mecanique quantique",
                "Mathematiques pour la chimie", "Langues Etrangeres",
                "Culture and art skills"
            ],
            "Digitalisation": [
                "Probabilites et statistiques", "Programmation Web 1",
                "Architecture des ordinateurs", "Systeme d'exploitation 1",
                "Structure de donnees en C", "Langues Etrangeres",
                "Culture and art skills"
            ],
            "Electronique et Systemes": [
                "Mecanique du solide", "Circuits electriques", "Electromagnetisme",
                "Algorithmique et Programmation (Python)", "Mathematiques pour la Physique",
                "Langues Etrangeres", "Culture and art skills"
            ],
            "Genie Informatique": [
                "Probabilites et statistiques", "Architecture des ordinateurs",
                "Systeme d'exploitation 1", "Programmation en langage C",
                "Programmation Web 1", "Langues Etrangeres",
                "Competences culturelles et artistiques"
            ],
            "Geosciences et Geologie de l'Ingenieur": [
                "Geologie structurale", "Techniques d'exploration des substances utiles",
                "Petrologie (magmatique et metamorphique)", "Petrographie sedimentaire",
                "Hydrogeologie et hydrologie (eau et sol)", "Culture and Art Skills",
                "Langues Etrangeres"
            ],
            "Hydrologie et Hydrogeologie": [
                "Geologie structurale", "Techniques d'exploration des substances utiles",
                "Petrologie (magmatique et metamorphique)", "Petrographie sedimentaire",
                "Hydrogeologie et hydrologie (sol et eau)", "Culture and Art Skills",
                "Langues Etrangeres"
            ],
            "Materiaux et Energetique": [
                "Mecanique du solide", "Circuits electriques", "Electromagnetisme",
                "Algorithmique et Programmation (Python)", "Mathematiques pour la Physique",
                "Langues Etrangeres", "Culture and Art Skills"
            ],
            "Mathematiques et Applications": [
                "Analyse 4", "Analyse 3", "Algebre 3", "Probabilites et Statistiques",
                "Informatique 3", "Langues Etrangeres", "Culture and art skills"
            ],
        },
        "S4": {
            "Biologie Cellulaire et Physiologie Humaine": [
                "Systematique et Notion de Biodiversite", "Enzymologie et Biochimie Metabolique",
                "Physiologie Vegetale", "Physiologie Animale",
                "Biologie Moleculaire et Genetique", "Langues Etrangeres",
                "Developpement Personnel"
            ],
            "Chimie Organique et Bioorganique": [
                "Chimie organique fonctionnelle", "Thermodynamique chimique",
                "Techniques d'analyse", "Cristallographie geometrique et cristallochimie",
                "Probabilites et statistiques", "Langues etrangeres",
                "Developpement personnel"
            ],
            "Chimie Physique Appliquee et Environnement": [
                "Chimie Organique Fonctionnelle", "Thermodynamique chimique",
                "Techniques d'analyse", "Cristallographie geometrique et cristallochimie",
                "Probabilites et statistiques", "Langues Etrangeres",
                "Developpement personnel"
            ],
            "Digitalisation": [
                "Recherche operationnelle et optimisation", "Bases de donnees relationnelles",
                "Reseaux", "Systeme d'exploitation 2",
                "Programmation objet avec C++", "Langues Etrangeres",
                "Developpement personnel"
            ],
            "Electronique et Systemes": [
                "Electronique analogique", "Optique ondulatoire", "Mecanique quantique",
                "Electronique numerique", "Analyse numerique", "Langues Etrangeres",
                "Developpement personnel"
            ],
            "Genie Informatique": [
                "Structures de donnees", "Programmation Web 2: JavaScript",
                "Systeme d'exploitation 2", "Programmation objet avec C++",
                "Algebre relationnel & SQL", "Langues Etrangeres",
                "Developpement personnel"
            ],
            "Geosciences et Geologie de l'Ingenieur": [
                "Ressources minerales", "Sedimentologie et environnements sedimentaires",
                "Stratigraphie Paleontologie II", "Geomatique (SIG et Teledetection) et Geostatistiques",
                "Geochimie", "Langues Etrangeres", "Developpement personnel"
            ],
            "Hydrologie et Hydrogeologie": [
                "Ressources minerales", "Sedimentologie et environnements sedimentaires",
                "Geochimie", "Stratigraphie Paleontologie",
                "Geomatique (SIG et Teledetection) et Geostatistique", "Langues Etrangeres",
                "Developpement personnel"
            ],
            "Materiaux et Energetique": [
                "Electronique analogique", "Optique ondulatoire", "Mecanique quantique",
                "Electronique numerique", "Analyse numerique", "Langues Etrangeres",
                "Developpement personnel"
            ],
            "Mathematiques et Applications": [
                "Analyse 5", "Algebre 4", "Algebre 5", "Analyse Numerique",
                "Informatique 4", "Langues Etrangeres", "Developpement personnel"
            ],
        },
        "S5": {
            "Biologie Cellulaire et Physiologie Humaine": [
                "Biologie Moleculaire", "Genetique II", "Immunologie",
                "Pharmacologie et Enzymologie Approfondie", "Physiologie des Grandes Fonctions",
                "Langues Etrangeres (3)", "Soft Skills"
            ],
            "Chimie Organique et Bioorganique": [
                "Chimie theorique et modelisation", "Chimie organique approfondie",
                "Chimie des heterocycles et organometallique",
                "Controle qualite et securite dans le laboratoire",
                "Methodes spectroscopiques et analyse", "Langues etrangeres",
                "Competences numeriques"
            ],
            "Chimie Physique Appliquee et Environnement": [
                "Controle Qualite & Securite dans le laboratoire",
                "Techniques d'analyse chromatographique et spectroscopique",
                "Cinetique chimique et catalyse", "Chimie theorique et modelisation",
                "Langues Etrangeres", "Digital Skills II : Excel avance"
            ],
            "Digitalisation": [
                "Compilation", "Programmation orientee en Java",
                "Conception Orientee Objet & Genie Logiciel",
                "Traitement du Signal et de l'Image", "Securite reseaux",
                "Langues Etrangeres", "Systemes de Gestion de Contenu (CMS)"
            ],
            "Electronique et Systemes": [
                "Traitement du signal", "Instrumentation et mesures",
                "Informatique industrielle", "Physique des materiaux",
                "Physique nucleaire", "Langues Etrangeres",
                "Digital Skills II : Excel avance"
            ],
            "Genie Informatique": [
                "Recherche operationnelle et optimisation", "Compilation",
                "Conception orientee objet & Genie logiciel",
                "Programmation orientee objet en Java", "Reseaux informatique",
                "Langues Etrangeres", "Digital Skills II : Excel avance"
            ],
            "Geosciences et Geologie de l'Ingenieur": [
                "Geologie du Maroc I", "Geologie du Maroc II", "Geophysique",
                "Paleontologie et Paleoecosystemes",
                "Module professionnel 1 (Ecole de terrain)", "Langues Etrangeres",
                "Digital Skills II: Excel avance"
            ],
            "Hydrologie et Hydrogeologie": [
                "Geologie du Maroc I", "Geologie du Maroc II", "Geophysique",
                "Stratigraphie Paleontologie II", "Module professionnel 1 (Ecole de terrain)",
                "Langues Etrangeres", "Digital Skills II : Excel avance"
            ],
            "Materiaux et Energetique": [
                "Physique des materiaux", "Physique statistique", "Physique nucleaire",
                "Mecanique des fluides", "Instrumentation et mesures",
                "Langues Etrangeres", "Digital Skills II : Excel avance"
            ],
            "Mathematiques et Applications": [
                "Integration", "Topologie", "Analyse Numerique 2",
                "Calcul Differentiel et Applications a l'Optimisation",
                "Mathematiques Financieres", "Langues Etrangeres",
                "Algorithmique et programmation en Python"
            ],
        },
        "S6": {
            "Biologie Cellulaire et Physiologie Humaine": [
                "Signalisation Cellulaire", "Microbiologie II",
                "Neurophysio Endocrinologie", "Developpement et Reproduction Humaine",
                "Entreprenariat et Elaboration de Documents de Recherche",
                "Langues Etrangeres (3)", "Culture & Art Skills"
            ],
            "Chimie Organique et Bioorganique": [
                "Chimie bioorganique : application aux domaines de la sante et de l'agroalimentaire",
                "Materiaux polymeres",
                "Strategie de synthese et retrosynthese en chimie organique",
                "Photochimie et formulation", "Gestion des dechets", "Langues etrangeres",
                "Droit, civisme et citoyennete"
            ],
            "Chimie Physique Appliquee et Environnement": [
                "Genie des procedes chimiques", "Statistiques appliquees a la chimie",
                "Chimie de l'environnement", "Gestion des dechets",
                "Methodes d'elaboration, d'analyse et de caracterisation des materiaux",
                "Langues Etrangeres", "Droit, civisme et citoyennete"
            ],
            "Digitalisation": [
                "JEE", "Developpement mobile", "Bases de donnees avancees",
                "Intelligence Artificielle", "Stage professionnel",
                "Langues Etrangeres", "Droit, civisme et citoyennete"
            ],
            "Electronique et Systemes": [
                "Electronique de communications analogiques", "Optoelectronique",
                "Circuits et systemes hyperfrequences",
                "Automatisation des systemes industriels", "Automatique",
                "Langues Etrangeres", "Droit, civisme et citoyennete"
            ],
            "Genie Informatique": [
                "JEE", "Developpement mobile", "Intelligence Artificielle",
                "Bases de donnees avancees", "Stage professionnel",
                "Langues Etrangeres", "Droit, civisme et citoyennete"
            ],
            "Geosciences et Geologie de l'Ingenieur": [
                "Cartographie numerique et geoinformation",
                "Module professionnel I (Ecole de terrain)", "Risques naturels",
                "Geotechnique", "Modelisation et prevention", "Langues Etrangeres",
                "Droit, civisme et citoyennete"
            ],
            "Hydrologie et Hydrogeologie": [
                "Cartographie numerique et geoinformation", "Geologie des reservoirs",
                "Climatologie et hydrologie", "Hydrogeologie II",
                "Module professionnel 2: Stage de terrain", "Langues Etrangeres",
                "Droit, civisme et citoyennete"
            ],
            "Materiaux et Energetique": [
                "Physique quantique", "Techniques d'analyses et de caracterisation",
                "Transferts thermiques", "Energies renouvelables",
                "Thermodynamique appliquee", "Langues etrangeres",
                "Droit, civisme et citoyennete"
            ],
            "Mathematiques et Applications": [
                "Analyse fonctionnelle", "Analyse complexe et geometrie",
                "Distributions", "Probabilites 2", "Mathematiques Actuarielles",
                "Langues Etrangeres", "Droit, civisme et citoyennete"
            ],
        },
    },
    "LIC_EXC": {
        "S5": {
            "Chimie des Materiaux et des Procedes Industriels": [
                "Cinetique chimique et catalyse industrielle", "Electrochimie industrielle",
                "Techniques d'analyse chromatographiques et spectroscopiques",
                "Genie des procedes I: Transfert de matiere et de chaleur",
                "Chimie organique: reactivite et mecanisme reactionnels",
                "Anglais/Francais", "Digital Skills II : Excel avance"
            ],
            "Intelligence et Securite des Objets Connectes": [
                "Competences numeriques II", "Compilation",
                "Reseaux: Mise a niveau et programmation reseau",
                "Developpement Materiel", "Bases de donnees avancees",
                "De l'UML a Java: du concept au code", "Anglais/Francais"
            ],
            "Systemes Intelligents et Recherche Operationnelle": [
                "Langues etrangeres 1", "Intelligence artificielle 1",
                "Programmation mathematique 1", "Algorithmes et programmation",
                "Bases de donnees & IA", "RO & IA pour le developpement durable",
                "Systemes de Gestion de Contenu"
            ],
            "Sciences des Donnees et Intelligence Artificielle": [
                "Administration systeme sous linux",
                "Modelisation et conception orientee objets",
                "Programmation orientee objets (Java)",
                "Recherche operationnelle et optimisation",
                "Reseaux informatique", "Langues Etrangeres",
                "Digital Skills II : Excel avance"
            ],
        },
        "S6": {
            "Chimie des Materiaux et des Procedes Industriels": [
                "Cristallographie et analyse structurale",
                "Demarche qualite concepts et sensibilisation",
                "Chimie minerale et industrielle", "Projet tutore professionnel",
                "Corrosion et procedes de revetement industriels",
                "Anglais/Francais", "Droit, civisme et citoyennete"
            ],
            "Intelligence et Securite des Objets Connectes": [
                "Administration des reseaux", "Developpement embarque",
                "Apprentissage Automatique", "JEE", "Projet informatique",
                "Anglais/Francais", "Droit, civisme et citoyennete"
            ],
            "Systemes Intelligents et Recherche Operationnelle": [
                "Intelligence artificielle 2", "Programmation mathematique 2",
                "Programmation orientee objets", "Securite des donnees",
                "Langues etrangeres 2",
                "Outils de prise a la decision et design thinking",
                "Droit, civisme et citoyennete"
            ],
            "Sciences des Donnees et Intelligence Artificielle": [
                "Developpement web JEE", "Bases de donnees avancees",
                "Langage Python pour l'Intelligence artificielle",
                "Stage/Projet Informatique", "Traitement d'image",
                "Langues Etrangeres", "Droit, civisme et citoyennete"
            ],
        },
    },
    "MAS": {
        "S7": {
            "BioActifs, Sante et Environnement": [
                "Epidemiologie environnementale",
                "Modeles Conceptuels en Sante Environnementale/One Health",
                "Nutrition Humaine & Sante", "Chimie des molecules bioactives & Sante",
                "Biostatistique & Modelisation", "Soft Skills", "Langues Etrangeres"
            ],
            "Geodynamique et Georessources": [
                "Geologie des bassins sedimentaires", "Initiation a la Recherche Scientifique",
                "Geologie structurale", "Transferts lithospheriques",
                "SIG et Teledetection", "Soft Skills", "Langues Etrangeres"
            ],
            "Intelligence Artificielle et Recherche Operationnelle": [
                "Algorithmes et structures de donnees avec Python",
                "Optimisation dans les Graphes", "RO & IA pour le developpement durable",
                "Methodologie de travail universitaire et de la recherche scientifique",
                "Bases de l'intelligence artificielle",
                "Programmation mathematique", "Langues etrangeres 1"
            ],
            "Mecanique des Fluides et Energetique": [
                "Mecanique des milieux continus", "Mecanique des fluides",
                "Resistance des materiaux", "Mathematique pour la physique",
                "Analyse numerique des EDP et simulation sous MATLAB",
                "Langues Etrangeres", "Developpement personnel et methodologie de recherche"
            ],
            "Physique Appliquee et Ingenierie Physique": [
                "Mecanique quantique II", "Physique du solide 1",
                "Symetrie Cristalline et radiocristallographie",
                "Physique statistique avancee",
                "Mathematiques et methodes numeriques pour la physique",
                "Competences generales", "Langues etrangeres 1"
            ],
            "Plasturgie et Ingenierie Biomedicale": [
                "Generalites sur les Systemes Colloidaux",
                "Thermodynamique et Rheologie des Polymeres",
                "Interaction Rayonnement Matiere et Radioprotection",
                "Modelisation des Systemes Complexes: Scilab",
                "Chimie des Polymeres", "Langues etrangeres 1", "Soft Skills"
            ],
        },
        "S8": {
            "BioActifs, Sante et Environnement": [
                "Bioactifs, Alicaments et Sante", "Pharmacologie & Toxicologie",
                "Qualite, Normalisation et Certification",
                "Bioethique & Biosecurite",
                "Genomique fonctionnelle & Epigenetique", "Digital Skills",
                "Langues Etrangeres"
            ],
            "Geodynamique et Georessources": [
                "Cartographie numerique et geostatistique",
                "Modelisation geochimique des processus petrogenetiques",
                "Ecole de terrain", "Geophysique appliquee",
                "Techniques analytiques et traitement du minerai",
                "Langues Etrangeres", "Culture digitale"
            ],
            "Intelligence Artificielle et Recherche Operationnelle": [
                "Optimisation stochastique", "Workshop scientifique & industriel",
                "Machine Learning", "Programmation non lineaire",
                "Algorithmes et programmation avancee avec Python",
                "Langues etrangeres 2", "Systemes de Gestion de Contenu (CMS)"
            ],
            "Mecanique des Fluides et Energetique": [
                "Hydrodynamique", "Rheologie et ecoulements polyphasiques",
                "Aerodynamique", "Programmation en Python et calcul symbolique",
                "Mecanique des fluides numerique (ANSYS Fluent, SolidWorks)",
                "Langues Etrangeres", "Culture digitale"
            ],
            "Physique Appliquee et Ingenierie Physique": [
                "Magnetisme et nanomagnetisme", "Mecanique quantique Avancee",
                "Physique du solide 2 et methodes spectroscopiques",
                "Traitement de signal",
                "Nanomateriaux pour les technologies emergentes",
                "Culture numerique", "Langues etrangeres 2"
            ],
            "Plasturgie et Ingenierie Biomedicale": [
                "Commande de Processus Industriel",
                "Biologie cellulaire: Organisation et Fonctions de la Cellule",
                "Physique de la matiere Molle et Colloides",
                "Mecanique des milieux continus",
                "Cristallographie Geometrique et Radiocristallographie",
                "Langues Etrangeres 2", "Digital Skills"
            ],
        },
        "S9": {
            "BioActifs, Sante et Environnement": [
                "Methodes d'analyses de la relation SE et Biomonitoring humaine",
                "Statistiques avancees et Data science Appliquees a la Sante et l'Environnement",
                "Ingenierie des projets de developpement/Audit et evaluation",
                "Developpement et Validation des methodes bioanalytiques",
                "Innovations technologiques en sante environnementale & Omics",
                "Langues Etrangeres", "Culture and Art skills"
            ],
            "Geodynamique et Georessources": [
                "Metallogenie", "Gisements marocains et legislation miniere",
                "Instabilites, Risques et Environnement Miniers",
                "Geomateriaux", "Metaux strategiques et energie renouvelable",
                "Langues Etrangeres", "Culture and Art skills"
            ],
            "Intelligence Artificielle et Recherche Operationnelle": [
                "Programmation mathematique avancee",
                "Cloud & Securite des donnees",
                "Science de la decision et theorie des jeux",
                "Projet R&D", "Deep Learning", "Langues etrangeres 3",
                "Competences culturelles et artistiques"
            ],
            "Mecanique des Fluides et Energetique": [
                "Turbomachines et ecoulements internes",
                "Hydraulique et ecoulements dans les reseaux",
                "Energie renouvelable hydrolienne, eolienne, marine et solaire",
                "Agroclimatologie, pilotage des reseaux de microirrigation et instrumentations",
                "Mecanique du sol, geotechnique, geophysique et hydrogeologie",
                "Langues Etrangeres", "Competences culturelles et artistiques"
            ],
            "Physique Appliquee et Ingenierie Physique": [
                "Ingenierie Laser et applications",
                "Dynamique des systemes complexes", "Photonique avancee",
                "Sciences atmospheriques et spectroscopie",
                "Optique, Photonique, Lasers", "Langue etrangeres 3",
                "Competences culturelles et artistiques"
            ],
            "Plasturgie et Ingenierie Biomedicale": [
                "Physique des Systemes Microfluidiques", "Materiaux Composites",
                "Preparation et Procedes de Mise en Forme des Matieres Molles",
                "Matieres Plastiques & Mousses", "Biopolymeres",
                "Langues Etrangeres 3", "Culture and art skills"
            ],
        },
        "S10": {
            "BioActifs, Sante et Environnement": [
                "Projet de fin d'etudes (PFE)", "Employment Skills"
            ],
            "Geodynamique et Georessources": [
                "Projet de fin d'etudes", "Employment Skills"
            ],
            "Intelligence Artificielle et Recherche Operationnelle": [
                "Developpement personnel et employabilite",
                "Projet de fin d'etudes (PFE)"
            ],
            "Mecanique des Fluides et Energetique": [
                "Entreprenariat et sensibilisation a la sociologie du travail",
                "Projet de fin d'etudes (PFE)"
            ],
            "Physique Appliquee et Ingenierie Physique": [
                "Competences professionnelles", "Projet de fin d'etudes (PFE)"
            ],
            "Plasturgie et Ingenierie Biomedicale": [
                "Employment Skills", "Projet de fin d'etudes (PFE)"
            ],
        },
    },
    "MAS_EXC": {
        "S7": {
            "Sciences des Donnees et Intelligence Artificielle": [
                "Representation des connaissances",
                "Python avance pour la Data Science", "Robotique",
                "Variables aleatoires", "Statistiques",
                "Competences generales", "Langues Etrangeres"
            ],
            "Intelligence Artificielle et Systemes de Decisions Optimales": [
                "Modules non disponibles sur le site officiel"
            ],
        },
        "S8": {
            "Sciences des Donnees et Intelligence Artificielle": [
                "Data Mining",
                "Systemes informatiques distribues et middlewares",
                "Apprentissage Automatique",
                "Programmation d'interfaces graphiques",
                "Projet 1: Intelligence Artificielle et Imagerie",
                "Culture digitale", "Langues Etrangeres"
            ],
            "Intelligence Artificielle et Systemes de Decisions Optimales": [
                "Modules non disponibles sur le site officiel"
            ],
        },
        "S9": {
            "Sciences des Donnees et Intelligence Artificielle": [
                "NLP et Web Mining", "Architectures pour Big Data",
                "L'apprentissage en profondeur (Deep Learning)",
                "Projet 2: Intelligence artificielle et donnees numeriques",
                "IA, realite virtuelle et augmentee",
                "Culture and Art Skills", "Langues Etrangeres"
            ],
            "Intelligence Artificielle et Systemes de Decisions Optimales": [
                "Modules non disponibles sur le site officiel"
            ],
        },
        "S10": {
            "Sciences des Donnees et Intelligence Artificielle": [
                "Employment Skills", "Projet de fin d'etudes (PFE)"
            ],
            "Intelligence Artificielle et Systemes de Decisions Optimales": [
                "Employment Skills", "Projet de fin d'etudes (PFE)"
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def curriculum_view(request):
    if Semestre.objects.count() == 0:
        _seed_curriculum_data()

    cache_key = _cache_key("curriculum", str(request.user.role), str(request.user.id))
    cached = _cached_response(cache_key)
    if cached:
        return cached

    semestres = Semestre.objects.prefetch_related("filieres__modules").all()

    # Role-based filtering
    user = request.user
    if user.role == "department_head":
        dept = get_user_department(user)
        if dept:
            semestres = Semestre.objects.filter(
                filieres__department=dept
            ).prefetch_related("filieres__modules").distinct()
        else:
            semestres = Semestre.objects.none()
    elif user.role == "program_manager":
        filiere_ids = get_user_filiere_ids(user)
        if filiere_ids:
            semestres = Semestre.objects.filter(
                filieres__id__in=filiere_ids
            ).prefetch_related("filieres__modules").distinct()
        else:
            semestres = Semestre.objects.none()

    serializer = SemestreSerializer(semestres, many=True)

    data = serializer.data
    cache.set(cache_key, data, CACHE_TTL)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def semestre_list(request):
    department_id = request.query_params.get("department_id", "")
    filiere_ids_param = request.query_params.get("filiere_ids", "")
    user = request.user
    cache_key = _cache_key("semestres", str(user.role), str(user.id), department_id, filiere_ids_param)
    cached = _cached_response(cache_key)
    if cached:
        return cached
    
    sems = (
        Semestre.objects
        .filter(filieres__niveau__gt="")
    )
    if user.role == "department_head":
        dept = get_user_department(user)
        if dept:
            sems = sems.filter(filieres__department=dept)
        else:
            sems = Semestre.objects.none()
    elif user.role == "program_manager":
        pm_filiere_ids = get_user_filiere_ids(user)
        if pm_filiere_ids:
            sems = sems.filter(filieres__id__in=pm_filiere_ids)
        else:
            sems = Semestre.objects.none()
    if department_id:
        sems = sems.filter(filieres__department_id=department_id)
    if filiere_ids_param:
        ids = [int(x) for x in filiere_ids_param.split(",") if x.strip().isdigit()]
        if ids:
            sems = sems.filter(filieres__id__in=ids)
    sems = sems.distinct().order_by("name").values("id", "name")
    
    data = list(sems)
    cache.set(cache_key, data, CACHE_TTL)
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def semestres_par_niveau(request):
    from users.models import NIVEAU_SEMESTRE_MAP

    niveau = request.query_params.get("niveau", "")
    if not niveau:
        return Response([])

    allowed_sem_names = NIVEAU_SEMESTRE_MAP.get(niveau)
    if allowed_sem_names is None:
        return Response([])

    cache_key = _cache_key("sems-niv", niveau)
    cached = _cached_response(cache_key)
    if cached:
        return cached

    sems = (
        Semestre.objects
        .filter(name__in=allowed_sem_names)
        .filter(filieres__niveau=niveau)
        .distinct()
        .order_by("name")
        .values("id", "name")
    )
    data = list(sems)
    cache.set(cache_key, data, CACHE_TTL)
    return Response(data)


def _bulk_create_filieres(name, niveau, extra_data):
    """Create Filiere records for every semester of the given niveau."""
    from users.models import NIVEAU_SEMESTRE_MAP

    allowed_sem_names = NIVEAU_SEMESTRE_MAP.get(niveau, [])
    if not allowed_sem_names:
        return Response(
            {"detail": f"Aucun semestre trouvé pour le niveau '{niveau}'."},
            status=400,
        )

    semestres = Semestre.objects.filter(name__in=allowed_sem_names).order_by("name")
    created = []
    skipped = []

    department_id = extra_data.get("department_id")
    manager_id = extra_data.get("manager_id")

    for sem in semestres:
        existing = Filiere.objects.filter(name=name, semestre=sem, niveau=niveau).first()
        if existing:
            skipped.append(existing)
            continue

        filiere = Filiere(
            name=name,
            semestre=sem,
            niveau=niveau,
        )
        if department_id:
            try:
                filiere.department_id = int(department_id)
            except (ValueError, TypeError):
                pass
        if manager_id:
            try:
                filiere.manager_id = int(manager_id)
            except (ValueError, TypeError):
                pass
        filiere.save()
        created.append(filiere)

    cache.clear()
    serializer = FiliereSerializer(created + skipped, many=True)

    msg_parts = []
    if created:
        msg_parts.append(f"{len(created)} filière(s) créée(s)")
    if skipped:
        msg_parts.append(f"{len(skipped)} existai(en)t déjà")
    message = ", ".join(msg_parts) + "."

    return Response({
        "created": len(created),
        "skipped": len(skipped),
        "message": message,
        "filieres": serializer.data,
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def filiere_list(request):
    if request.method == "POST":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)

        name = request.data.get("name", "").strip()
        niveau = request.data.get("niveau", "")
        semestre_id = request.data.get("semestre_id", None)

        # Bulk create: name + niveau only (no semestre_id)
        if name and niveau and not semestre_id and semestre_id is None:
            return _bulk_create_filieres(name, niveau, request.data)

        # Single create (backward compatible, used by edit when changing semester)
        if not semestre_id:
            return Response(
                {"semestre_id": "Le semestre est requis pour la création unitaire."},
                status=400,
            )
        serializer = FiliereSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    semestre_id = request.query_params.get("semestre_id", "")
    niveau = request.query_params.get("niveau", "")
    department_id = request.query_params.get("department_id", "")
    cache_key = _cache_key("filieres", semestre_id, niveau, department_id)
    cached = _cached_response(cache_key)
    if cached:
        return cached
    queryset = Filiere.objects.select_related("department", "manager").order_by("name")
    if semestre_id:
        queryset = queryset.filter(semestre_id=semestre_id)
    if niveau:
        from users.models import NIVEAU_SEMESTRE_MAP
        allowed = NIVEAU_SEMESTRE_MAP.get(niveau)
        if allowed is not None and semestre_id:
            queryset = queryset.filter(
                semestre_id=semestre_id,
                niveau=niveau,
            )
        elif allowed is not None:
            queryset = queryset.filter(
                niveau=niveau,
                semestre__name__in=allowed,
            )
        else:
            queryset = queryset.filter(niveau=niveau)
    if department_id:
        queryset = queryset.filter(department_id=department_id)
    if request.user.role == "department_head":
        queryset = apply_role_filtering(queryset, "filiere", request)
    elif request.user.role == "program_manager":
        queryset = apply_role_filtering(queryset, "filiere", request)
    serializer = FiliereSerializer(queryset, many=True)
    data = serializer.data
    cache.set(cache_key, data, CACHE_TTL)
    return Response(data)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def filiere_detail(request, pk):
    try:
        filiere = Filiere.objects.get(pk=pk)
    except Filiere.DoesNotExist:
        return Response({"detail": "Filière introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        # Role-based scope check
        if request.user.role == "department_head":
            dept = get_user_department(request.user)
            if not dept or filiere.department_id != dept.id:
                return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        elif request.user.role == "program_manager":
            filiere_ids = get_user_filiere_ids(request.user)
            if filiere.id not in filiere_ids:
                return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        serializer = FiliereSerializer(filiere)
        return Response(serializer.data)

    if request.method == "PATCH":
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== FILIERE_PATCH_START pk=%s role=%s user_id=%s data=%s", pk, request.user.role, request.user.id, request.data)
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        logger.info("=== FILIERE_PATCH_BEFORE_SERIALIZER pk=%s", pk)
        serializer = FiliereSerializer(filiere, data=request.data, partial=True)
        logger.info("=== FILIERE_PATCH_BEFORE_VALIDATION pk=%s", pk)
        if serializer.is_valid():
            logger.info("=== FILIERE_PATCH_VALID_OK pk=%s validated_data=%s", pk, serializer.validated_data)
            logger.info("=== FILIERE_PATCH_BEFORE_SAVE pk=%s", pk)
            serializer.save()
            logger.info("=== FILIERE_PATCH_AFTER_SAVE pk=%s", pk)
            logger.info("=== FILIERE_PATCH_BEFORE_CACHE_CLEAR pk=%s", pk)
            cache.clear()
            logger.info("=== FILIERE_PATCH_AFTER_CACHE_CLEAR pk=%s", pk)
            resp_data = serializer.data
            logger.info("=== FILIERE_PATCH_RESPONSE_OK pk=%s", pk)
            return Response(resp_data)
        logger.error("=== FILIERE_PATCH_VALID_FAIL pk=%s errors=%s", pk, serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        try:
            filiere.delete()
            cache.clear()
            return Response(status=204)
        except Exception as exc:
            return Response(
                {"detail": f"Erreur lors de la suppression : {exc}"},
                status=500,
            )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def filiere_assign_manager(request, pk):
    """Assign a teacher as the responsible (program_manager) for a filiere.

    - Changes the teacher's role to program_manager automatically.
    - If the teacher already manages another filiere, removes them first.
    - If the target filiere already has a different manager, removes them.
    - One filiere = one manager, one teacher = one filiere.
    """
    if request.user.role != "admin":
        return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)

    try:
        filiere = Filiere.objects.get(pk=pk)
    except Filiere.DoesNotExist:
        return Response({"detail": "Filière introuvable."}, status=status.HTTP_404_NOT_FOUND)

    teacher_id = request.data.get("manager_id")

    # Unassign current manager
    if not teacher_id:
        old_manager = filiere.manager
        if old_manager:
            filiere.manager = None
            filiere.save(update_fields=["manager"])
            if old_manager.role == "program_manager" and not old_manager.managed_filieres.exists():
                old_manager.role = "teacher"
                old_manager.save(update_fields=["role"])
            cache.clear()
        return Response({"detail": "Responsable retiré.", "manager_id": None, "manager_name": None})

    try:
        teacher = User.objects.get(pk=teacher_id)
    except User.DoesNotExist:
        return Response({"detail": "Enseignant introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if teacher.role not in ("teacher", "program_manager"):
        return Response(
            {"detail": "Seul un enseignant peut être responsable de filière."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Same teacher already assigned to this filiere → no-op
    if filiere.manager == teacher:
        return Response({
            "detail": f"{teacher.full_name} est déjà responsable de cette filière.",
            "manager_id": teacher.id,
            "manager_name": teacher.full_name,
        })

    # Step 1: If teacher already manages another filiere, remove them
    if teacher.managed_filieres.exists():
        for other in teacher.managed_filieres.exclude(pk=filiere.pk):
            other.manager = None
            other.save(update_fields=["manager"])

    # Step 2: If this filiere has a different manager, remove them
    if filiere.manager and filiere.manager != teacher:
        old_manager = filiere.manager
        filiere.manager = None
        filiere.save(update_fields=["manager"])
        if old_manager.role == "program_manager" and not old_manager.managed_filieres.exists():
            old_manager.role = "teacher"
            old_manager.save(update_fields=["role"])

    # Step 3: Assign the teacher as manager
    teacher.role = "program_manager"
    teacher.save(update_fields=["role"])
    filiere.manager = teacher
    filiere.save(update_fields=["manager"])
    cache.clear()

    return Response({
        "detail": f"{teacher.full_name} est maintenant responsable de {filiere.name}.",
        "manager_id": teacher.id,
        "manager_name": teacher.full_name,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def filiere_modules_by_semester(request, pk):
    """Return modules grouped by semester for all filieres sharing the same name."""
    try:
        filiere = Filiere.objects.select_related("semestre").get(pk=pk)
    except Filiere.DoesNotExist:
        return Response({"detail": "Filière introuvable."}, status=404)

    user = request.user
    if user.role == "department_head":
        dept = get_user_department(user)
        if not dept or filiere.department_id != dept.id:
            return Response({"detail": "Permission refusée."}, status=403)
    elif user.role == "program_manager":
        filiere_ids = get_user_filiere_ids(user)
        if filiere.id not in filiere_ids:
            return Response({"detail": "Permission refusée."}, status=403)

    niveau = filiere.niveau
    from users.models import NIVEAU_SEMESTRE_MAP
    allowed_sem_names = NIVEAU_SEMESTRE_MAP.get(niveau, [])

    sems = Semestre.objects.filter(name__in=allowed_sem_names).order_by("name")

    result = []
    for sem in sems:
        filiere_same = Filiere.objects.filter(
            name=filiere.name, semestre=sem, niveau=niveau,
        ).first()
        modules = []
        if filiere_same:
            modules = list(
                Module.objects.filter(filiere=filiere_same)
                .order_by("name")
                .values("id", "name")
            )
        result.append({
            "semestre_id": sem.id,
            "semestre_name": sem.name,
            "filiere_id": filiere_same.id if filiere_same else None,
            "modules": modules,
        })

    return Response({
        "filiere_name": filiere.name,
        "niveau": filiere.niveau,
        "niveau_label": dict(NIVEAU_CHOICES).get(filiere.niveau, filiere.niveau),
        "semesters": result,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def module_list(request):
    filiere_id = request.query_params.get("filiere_id", "")
    semestre_id = request.query_params.get("semestre_id", "")
    niveau = request.query_params.get("niveau", "")
    cache_key = _cache_key("modules", filiere_id, semestre_id, niveau)
    cached = _cached_response(cache_key)
    if cached:
        return cached
    queryset = Module.objects.select_related("filiere").order_by("name").only("id", "name", "filiere_id")
    if filiere_id:
        queryset = queryset.filter(filiere_id=filiere_id)
    if semestre_id:
        queryset = queryset.filter(filiere__semestre_id=semestre_id)
    if niveau:
        queryset = queryset.filter(filiere__niveau=niveau)
    if request.user.role == "department_head":
        queryset = apply_role_filtering(queryset, "module", request)
    elif request.user.role == "program_manager":
        queryset = apply_role_filtering(queryset, "module", request)
    data = list(queryset.values("id", "name", "filiere_id"))
    cache.set(cache_key, data, CACHE_TTL)
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def niveau_list(request):
    cache_key = _cache_key("niveaux")
    cached = _cached_response(cache_key)
    if cached:
        return cached
    data = [{"id": k, "label": v} for k, v in NIVEAU_CHOICES]
    cache.set(cache_key, data, CACHE_TTL)
    return Response(data)


# ---------------------------------------------------------------------------
# Subjects (Modules) CRUD
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def subject_list(request):
    if request.method == "POST":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        serializer = ModuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    filiere_id = request.query_params.get("filiere_id", "")
    queryset = Module.objects.select_related("filiere", "teacher").order_by("name")
    if filiere_id:
        queryset = queryset.filter(filiere_id=filiere_id)
    if request.user.role == "department_head":
        queryset = apply_role_filtering(queryset, "module", request)
    elif request.user.role == "program_manager":
        queryset = apply_role_filtering(queryset, "module", request)
    serializer = ModuleSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def subject_detail(request, pk):
    try:
        subject = Module.objects.select_related("filiere", "teacher").get(pk=pk)
    except Module.DoesNotExist:
        return Response({"detail": "Matière introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        # Role-based scope check
        if request.user.role == "department_head":
            dept = get_user_department(request.user)
            if not dept or subject.filiere.department_id != dept.id:
                return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        elif request.user.role == "program_manager":
            filiere_ids = get_user_filiere_ids(request.user)
            if subject.filiere_id not in filiere_ids:
                return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ModuleSerializer(subject)
        return Response(serializer.data)

    if request.method == "PATCH":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        serializer = ModuleSerializer(subject, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    if request.method == "DELETE":
        if request.user.role != "admin":
            return Response({"detail": "Permission refusée."}, status=403)
        subject.delete()
        return Response(status=204)


def _seed_curriculum_data():
    """Seeds the database with official FS-UMI academic structure using bulk_create."""
    sem_names = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]

    existing_sems = {s.name: s for s in Semestre.objects.all()}
    sem_map = {}
    for name in sem_names:
        if name in existing_sems:
            sem_map[name] = existing_sems[name]
        else:
            sem_map[name] = Semestre.objects.create(name=name)

    # Collect new filieres and modules
    new_filieres = []
    for niveau, semesters in FS_UMI_DATA.items():
        for sem_name, filieres in semesters.items():
            for filiere_name in filieres:
                new_filieres.append(Filiere(
                    name=filiere_name,
                    semestre=sem_map[sem_name],
                    niveau=niveau,
                ))

    # Bulk create filieres, batch to avoid huge queries
    existing = set(
        Filiere.objects.all().values_list("name", "semestre_id", "niveau")
    )
    filiere_objects = []
    for f in new_filieres:
        key = (f.name, f.semestre_id, f.niveau)
        if key not in existing:
            filiere_objects.append(f)
            existing.add(key)

    if filiere_objects:
        Filiere.objects.bulk_create(filiere_objects, ignore_conflicts=True)

    # Now create modules
    filiere_map = {
        (f.name, f.semestre_id, f.niveau): f.id
        for f in Filiere.objects.select_related("semestre").all()
    }

    existing_modules = set(
        Module.objects.all().values_list("name", "filiere_id")
    )
    module_objects = []
    for niveau, semesters in FS_UMI_DATA.items():
        for sem_name, filieres in semesters.items():
            sem = sem_map[sem_name]
            for filiere_name, modules in filieres.items():
                filiere_key = (filiere_name, sem.id, niveau)
                filiere_id = filiere_map.get(filiere_key)
                if not filiere_id:
                    continue
                for module_name in modules:
                    mod_key = (module_name, filiere_id)
                    if mod_key not in existing_modules:
                        module_objects.append(Module(
                            name=module_name,
                            filiere_id=filiere_id,
                        ))
                        existing_modules.add(mod_key)

    if module_objects:
        Module.objects.bulk_create(module_objects, ignore_conflicts=True)

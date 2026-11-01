"""Messages et règles métier partagés par les inscriptions étudiantes."""

# Un étudiant garde une seule filière : il peut suivre autant de modules et de
# semestres qu'il le souhaite dans cette filière, jamais dans une autre.
SINGLE_FILIERE_MESSAGE = (
    "Cet étudiant est déjà inscrit dans une autre filière. "
    "Une seule filière est autorisée par étudiant."
)


def same_filiere(first, second) -> bool:
    """Indique si deux objets Filiere représentent la même filière.

    Dans la base, une filière est déclinée en une ligne par semestre
    (« Génie Informatique » S1, S4, ...). L'identité réelle est donc le nom
    (comparé sans casse ni espaces superflus), complété par le niveau
    lorsqu'il est renseigné des deux côtés. Une valeur inconnue ne bloque pas.
    """
    if first is None or second is None:
        return True

    first_name = (first.name or "").strip().casefold()
    second_name = (second.name or "").strip().casefold()
    if not first_name or not second_name:
        return True
    if first_name != second_name:
        return False

    first_niveau = (first.niveau or "").strip()
    second_niveau = (second.niveau or "").strip()
    if first_niveau and second_niveau and first_niveau != second_niveau:
        return False
    return True

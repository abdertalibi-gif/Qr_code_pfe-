#!/usr/bin/env python3
import sys

with open('backend/templates/student.html', 'r', encoding='utf-8') as f:
    content = f.read()

checks = {
    'selectModule method': 'selectModule(moduleId) {' in content,
    'loadSchedule sig': 'loadSchedule(silent = false, moduleId = null)' in content,
    '?module_id param': '?module_id=' in content,
    '_renderScheduleModulesWithSessions call': '_renderScheduleModulesWithSessions(moduleId)' in content,
    '_renderScheduleModulesWithSessions method': '_renderScheduleModulesWithSessions(' in content,
    'no _renderScheduleClassesWithSessions': '_renderScheduleClassesWithSessions()' not in content,
    'onclick handler': 'studentPage.selectModule(' in content,
    'Retour aux modules': ' Retour aux modules' in content,
}

print('VERIFICATION WEB ETUDIANT')
print('='*40)
for name, result in checks.items():
    status = 'OK' if result else 'MANQUANT'
    print(f'  {status}: {name}')

# Additional checks with manual string search
additional = {
    'status en_cours': "session.status === 'en_cours'" in content,
    'status annulee': "session.status === 'annulee'" in content,
    'semester tag': 'schedule-semester-tag' in content,
    'modulesBySemester': 'modulesBySemester' in content,
    'teacher_name': 'session.teacher_name' in content,
    '_typeLabel': '_typeLabel(session.session_type)' in content,
    '_formatDateOnly': '_formatDateOnly(session.date)' in content,
    '_formatTime': '_formatTime(session.start_time)' in content,
}

print()
print('DETAILS SUPPLEMENTAIRES')
print('-'*30)
for name, result in additional.items():
    status = 'OK' if result else 'MANQUANT'
    print(f'  {status}: {name}')

all_ok = all(checks.values()) and all(additional.values())
print()
print('TOUT CORRECT:', all_ok)
sys.exit(0 if all_ok else 1)
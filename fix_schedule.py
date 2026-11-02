#!/usr/bin/env python3
import sys

# Read the file using codecs to handle encoding
with open('backend/templates/student.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add moduleId parameter to loadSchedule function signature
# Find: async loadSchedule(silent = false) {
# Replace with: async loadSchedule(silent = false, moduleId = null) {
import_pattern = r'async loadSchedule\(silent = false\) \{\n        if \(!silent\) this\._setSyncStatus\'(syncing)\';'
# Actually let me just do string replacement

# Find the loadSchedule function and add moduleId parameter
old_loadschedule = 'async loadSchedule(silent = false) {'
new_loadschedule = 'async loadSchedule(silent = false, moduleId = null) {'
content = content.replace(old_loadschedule, new_loadschedule, 1)

# 2. Update the API fetch call to use params
old_fetch = "const data = await API.apiFetch('/attendance/my-schedule/');"
new_fetch = "const params = moduleId ? '?module_id=' + moduleId : '';\n          const data = await API.apiFetch('/attendance/my-schedule/' + params);"
content = content.replace(old_fetch, new_fetch, 1)

# 3. Replace _renderScheduleClassesWithSessions() with _renderScheduleModulesWithSessions(moduleId)
content = content.replace('_renderScheduleClassesWithSessions()', '_renderScheduleModulesWithSessions(moduleId)')

# 4. Also need to update the refreshSchedule function call inside loadSchedule
# Actually refreshSchedule() just calls loadSchedule(false), so that should be fine

# 5. Update the error container - this might already be fine

# Write back
with open('backend/templates/student.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done fixing loadSchedule')
print('_renderScheduleClassesWithSessions remaining:', content.count('_renderScheduleClassesWithSessions'))
print('_renderScheduleModulesWithSessions count:', content.count('_renderScheduleModulesWithSessions'))
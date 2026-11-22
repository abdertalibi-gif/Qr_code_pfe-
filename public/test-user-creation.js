function getCookie(name) {
  const value = `; ${document.cookie}`.split(`; ${name}=`);
  return value.length === 2 ? value.pop().split(';').shift() : null;
}

async function testUserCreation() {
  const API_BASE = '';

  async function login() {
    try {
      const csrfToken = getCookie('csrftoken') || getCookie('csrfToken') || '';
      const resp = await fetch(`${API_BASE}/login/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'admin1@gmail.com', password: 'admin123' })
      });
      if (!resp.ok) throw new Error('Login failed');
      return resp;
    } catch (e) {
      console.error('Login error:', e);
      throw e;
    }
  }

  async function createUser(role, payload) {
    const body = JSON.stringify(payload);
    const resp = await fetch(`${API_BASE}/users/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`Failed to create ${role}: ${resp.status} ${resp.statusText}\n${text}`);
    }
    return await resp.json();
  }

  await login();
  console.log('✅ Logged in as admin');

  const testUsers = [
    {
      role: 'admin',
      payload: {
        first_name: 'Test Admin',
        last_name: '1',
        email: `admin_test_${Date.now()}@test.com`,
        password: 'testpassword123',
        password_confirm: 'testpassword123',
        role: 'admin'
      }
    },
    {
      role: 'teacher',
      payload: {
        first_name: 'Test Teacher',
        last_name: '2',
        email: `teacher_test_${Date.now()}@test.com`,
        password: 'testpassword123',
        password_confirm: 'testpassword123',
        role: 'teacher',
        is_also_teacher: false,
        assigned_class_ids: []
      }
    },
    {
      role: 'student',
      payload: {
        first_name: 'Test Student',
        last_name: '3',
        email: `student_test_${Date.now()}@test.com`,
        password: 'testpassword123',
        password_confirm: 'testpassword123',
        role: 'student',
        code_massar: `TEST${Date.now()}`,
        code_apogee: `APOGEE${Date.now()}`,
        student_classe: null
      }
    },
    {
      role: 'department_head',
      payload: {
        first_name: 'Test Dept Head',
        last_name: '4',
        email: `dept_head_test_${Date.now()}@test.com`,
        password: 'testpassword123',
        password_confirm: 'testpassword123',
        role: 'department_head',
        assigned_class_ids: []
      }
    },
    {
      role: 'program_manager',
      payload: {
        first_name: 'Test Program Manager',
        last_name: '5',
        email: `program_manager_test_${Date.now()}@test.com`,
        password: 'testpassword123',
        password_confirm: 'testpassword123',
        role: 'program_manager',
        assigned_class_ids: []
      }
    }
  ];

  const results = [];
  for (const test of testUsers) {
    try {
      console.log(`Testing ${test.role} creation...`);
      const result = await createUser(test.role, test.payload);
      console.log(`✅ ${test.role} created:`, result.id);
      results.push({ role: test.role, success: true, id: result.id });
    } catch (error) {
      console.error(`❌ ${test.role} failed:`, error.message);
      results.push({ role: test.role, success: false, error: error.message });
    }
  }

  console.log('\n=== SUMMARY ===');
  let successCount = 0;
  for (const r of results) {
    console.log(`${r.role}: ${r.success ? '✅' : '❌'}${r.success ? ` (ID: ${r.id})` : ` (${r.error})`}`);
    if (r.success) successCount++;
  }
  console.log(`\nTotal: ${results.length} | Success: ${successCount} | Failed: ${results.length - successCount}`);

  if (successCount === results.length) {
    console.log('\n🎉 All user creation tests passed!');
  } else {
    console.log('\n⚠️ Some user creation tests failed');
  }
}

(function() {
  testUserCreation();
})();
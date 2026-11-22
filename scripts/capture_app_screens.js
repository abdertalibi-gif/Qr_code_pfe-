import playwrightPkg from '/usr/local/share/bun-global/node_modules/playwright-core/index.js';
const { chromium } = playwrightPkg;
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const targetDir = path.join(__dirname, '..', 'docs', 'screenshots');
const publicScreensDir = path.join(__dirname, '..', 'public', 'screenshots');

if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });
if (!fs.existsSync(publicScreensDir)) fs.mkdirSync(publicScreensDir, { recursive: true });

// Remove old placeholder jpgs if any
for (const dir of [targetDir, publicScreensDir]) {
  for (const f of fs.readdirSync(dir)) {
    if (f.endsWith('.jpg') || f.endsWith('.png')) {
      fs.unlinkSync(path.join(dir, f));
    }
  }
}

async function run() {
  console.log('[Capture] Démarrage de Chromium...');
  const browser = await chromium.launch({
    executablePath: '/ms-playwright/chrome-headless-shell-linux64/chrome-headless-shell',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 },
    deviceScaleFactor: 1.5,
  });

  const page = await context.newPage();

  // 1. Landing Page (wait 2.5s so animated stats counters complete!)
  console.log('[Capture] 1. Page d\'Accueil...');
  await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2600);
  await page.screenshot({ path: path.join(targetDir, '01_landing_page.png') });

  // 2. Login Page
  console.log('[Capture] 2. Page de Connexion...');
  await page.goto('http://localhost:3000/login/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(targetDir, '02_login_portal.png') });

  // 3. Admin Dashboard (Live Attendance tab)
  console.log('[Capture] 3. Tableau de bord Administrateur...');
  await page.fill('#email', 'admin@qrattendance.local');
  await page.fill('#password', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/admin-ui/**', { timeout: 10000 });
  await page.waitForTimeout(2000);
  // Click Live Attendance tab to showcase real-time table + WS status
  const attTabBtn = await page.$('.tab-btn[data-tab="attendance"]');
  if (attTabBtn) {
    await attTabBtn.click();
    await page.waitForTimeout(1000);
  }
  await page.screenshot({ path: path.join(targetDir, '03_admin_live_attendance.png') });

  // 4. Admin Classes & Curriculum
  console.log('[Capture] 4. Admin Classes...');
  const classTabBtn = await page.$('.tab-btn[data-tab="classes"]');
  if (classTabBtn) {
    await classTabBtn.click();
    await page.waitForTimeout(1000);
  }
  await page.screenshot({ path: path.join(targetDir, '04_admin_classes.png') });

  // 5. Admin Absence Statistics
  console.log('[Capture] 5. Admin Statistiques des absences...');
  const absTabBtn = await page.$('.tab-btn[data-tab="absence-stats"]');
  if (absTabBtn) {
    await absTabBtn.click();
    await page.waitForTimeout(1000);
  }
  await page.screenshot({ path: path.join(targetDir, '05_admin_absence_stats.png') });

  // 6. Espace Enseignant (Live session + inline QR + attendance table)
  console.log('[Capture] 6. Espace Enseignant...');
  await page.evaluate(() => localStorage.clear());
  await page.goto('http://localhost:3000/login/', { waitUntil: 'networkidle' });
  await page.fill('#email', 'teacher@qrattendance.local');
  await page.fill('#password', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/teacher/**', { timeout: 10000 });
  await page.waitForTimeout(2000);

  const firstCourseHdr = await page.$('.course-header');
  if (firstCourseHdr) {
    await firstCourseHdr.click();
    await page.waitForTimeout(1500);
    const sessItem = await page.$('.sessions-list .session-item:not(:has-text("Chargement"))');
    if (sessItem) {
      await sessItem.click();
      await page.waitForTimeout(1800);
    }
  }
  await page.screenshot({ path: path.join(targetDir, '06_teacher_dashboard.png') });

  // 7. Teacher QR Modal view (wait 1.5s for countdown tick)
  console.log('[Capture] 7. QR Code Enseignant...');
  const enlargeBtn = await page.$('button:has-text("Enlarge QR"), button:has-text("Agrandir")');
  if (enlargeBtn) {
    await enlargeBtn.click();
    await page.waitForTimeout(1500);
  }
  await page.screenshot({ path: path.join(targetDir, '07_teacher_qr_modal.png') });

  // 8. Espace Étudiant (Profile, modules, schedule)
  console.log('[Capture] 8. Espace Étudiant...');
  await page.evaluate(() => localStorage.clear());
  await page.goto('http://localhost:3000/login/', { waitUntil: 'networkidle' });
  await page.fill('#email', 'student@qrattendance.local');
  await page.fill('#password', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/student/**', { timeout: 10000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(targetDir, '08_student_portal.png') });

  // 9. Validation Présence Mobile (/attend/)
  console.log('[Capture] 9. Validation Présence Mobile...');
  const mobileContext = await browser.newContext({
    viewport: { width: 460, height: 880 },
    deviceScaleFactor: 2,
    geolocation: { latitude: 33.8938, longitude: -5.5516 },
    permissions: ['geolocation'],
  });
  const mobilePage = await mobileContext.newPage();
  await mobilePage.goto('http://localhost:3000/attend/?token=SESSION-DEMO-QR-2026', { waitUntil: 'networkidle' });
  await mobilePage.waitForTimeout(1500);

  const fnInput = await mobilePage.$('#firstName');
  if (fnInput) await fnInput.fill('Amine');
  const lnInput = await mobilePage.$('#lastName');
  if (lnInput) await lnInput.fill('Idrissi');
  const massarInput = await mobilePage.$('#codeMassar');
  if (massarInput) await massarInput.fill('M130000001');
  await mobilePage.waitForTimeout(500);

  await mobilePage.screenshot({ path: path.join(targetDir, '09_student_attendance_validation.png') });

  await browser.close();

  const files = fs.readdirSync(targetDir).filter((f) => f.endsWith('.png'));
  for (const f of files) {
    fs.copyFileSync(path.join(targetDir, f), path.join(publicScreensDir, f));
  }

  console.log('🎉 Succès ! Captures d\'écran enregistrées :', files);
}

run().catch((e) => {
  console.error('❌ Erreur lors de la capture :', e);
  process.exit(1);
});

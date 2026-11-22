import express, { Request, Response } from 'express';
import cors from 'cors';
import http from 'http';
import path from 'path';
import { fileURLToPath } from 'url';
import { WebSocketServer, WebSocket } from 'ws';
import jwt from 'jsonwebtoken';
import QRCode from 'qrcode';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const server = http.createServer(app);
const PORT = Number(process.env.PORT) || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'presenceqr-secret-key-2026';

// Middleware
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Static files from public/
const publicDir = path.join(__dirname, 'public');
app.use(express.static(publicDir));
app.use('/media', express.static(path.join(publicDir, 'media')));

/* ─── WebSockets for Live Attendance ───────────────────────────────────── */
const wss = new WebSocketServer({ server });

interface ExtendedWebSocket extends WebSocket {
  channel?: string;
  isAlive?: boolean;
}

wss.on('connection', (ws: ExtendedWebSocket, req) => {
  const url = req.url || '';
  ws.channel = url;
  ws.isAlive = true;

  ws.on('pong', () => {
    ws.isAlive = true;
  });

  ws.send(JSON.stringify({ type: 'connected', message: 'WebSocket connecté au serveur PrésenceQR' }));
});

function broadcastAttendance(record: any, sessionId?: number) {
  const message = JSON.stringify({ type: 'attendance_record', data: record });
  wss.clients.forEach((client: ExtendedWebSocket) => {
    if (client.readyState === WebSocket.OPEN) {
      if (
        !client.channel ||
        client.channel.includes('/ws/attendance/live/') ||
        (sessionId && client.channel.includes(`/ws/attendance/${sessionId}/`)) ||
        client.channel.includes('/attendance')
      ) {
        client.send(message);
      }
    }
  });
}

/* ─── In-Memory Data Store ─────────────────────────────────────────────── */

let departments = [
  { id: 1, name: 'Informatique', code: 'INFO', description: "Département d'Informatique & Nouvelles Technologies", head_id: 8, teacher_count: 14, student_count: 180 },
  { id: 2, name: 'Mathématiques', code: 'MATH', description: 'Département de Mathématiques Appliquées', head_id: 3, teacher_count: 8, student_count: 95 },
  { id: 3, name: 'Physique & Électronique', code: 'PHYS', description: 'Département de Physique et Systèmes Embarqués', head_id: 2, teacher_count: 10, student_count: 120 },
];

let filieres = [
  { id: 1, name: 'Génie Informatique', code: 'GI', department_id: 1, department: 'Informatique', niveau: "Cycle d'Ingénieur", manager_id: 2, student_count: 90 },
  { id: 2, name: 'Sciences des Données et IA', code: 'SDIA', department_id: 1, department: 'Informatique', niveau: 'Master', manager_id: 2, student_count: 65 },
  { id: 3, name: 'Intelligence & Sécurité des Systèmes', code: 'ISIC', department_id: 1, department: 'Informatique', niveau: 'Master', manager_id: 3, student_count: 55 },
];

let blocks = [
  { id: 1, name: 'Bloc A', code: 'BL-A', rooms_count: 8 },
  { id: 2, name: 'Bloc B', code: 'BL-B', rooms_count: 12 },
  { id: 3, name: 'Bloc C (Laboratoires)', code: 'BL-C', rooms_count: 6 },
];

let rooms = [
  { id: 1, name: 'Salle 101', block: 'Bloc A', block_id: 1, capacity: 40, is_occupied: false, current_teacher: null, current_session: null },
  { id: 2, name: 'Salle 102', block: 'Bloc A', block_id: 1, capacity: 40, is_occupied: true, current_teacher: 'Pr. Karim Alami', current_session: 'Développement Web JEE' },
  { id: 3, name: 'Labo Info 1', block: 'Bloc C (Laboratoires)', block_id: 3, capacity: 32, is_occupied: false, current_teacher: null, current_session: null },
  { id: 4, name: 'Labo Info 2', block: 'Bloc C (Laboratoires)', block_id: 3, capacity: 32, is_occupied: true, current_teacher: 'Pr. Mohammed Tazi', current_session: 'Compilation' },
  { id: 5, name: 'Salle 204', block: 'Bloc B', block_id: 2, capacity: 45, is_occupied: false, current_teacher: null, current_session: null },
];

let amphitheaters = [
  { id: 1, name: 'Amphi 1', capacity: 250, is_occupied: false, current_teacher: null, current_session: null },
  { id: 2, name: 'Amphi 2', capacity: 200, is_occupied: true, current_teacher: 'Dr. Fatima Zahra', current_session: 'Algèbre Linéaire' },
  { id: 3, name: 'Amphi Al-Kindi', capacity: 350, is_occupied: false, current_teacher: null, current_session: null },
];

let classes = [
  { id: 1, name: 'SDIA 1 - S1', code: 'SDIA-S1', filiere: 'Sciences des Données et IA', filiere_id: 2, level: 'M1', academic_year: '2025/2026', student_count: 32 },
  { id: 2, name: 'GI 2 - S3', code: 'GI-S3', filiere: 'Génie Informatique', filiere_id: 1, level: 'CI2', academic_year: '2025/2026', student_count: 28 },
  { id: 3, name: 'ISIC 1 - S1', code: 'ISIC-S1', filiere: 'Intelligence & Sécurité des Systèmes', filiere_id: 3, level: 'M1', academic_year: '2025/2026', student_count: 25 },
];

let modules = [
  { id: 1, name: 'Développement Web JEE', code: 'JEE', filiere: 'Sciences des Données et IA', filiere_id: 2, teacher_id: 2, coefficient: 4 },
  { id: 2, name: 'Machine Learning & IA', code: 'MLIA', filiere: 'Sciences des Données et IA', filiere_id: 2, teacher_id: 2, coefficient: 5 },
  { id: 3, name: 'Administration Réseau', code: 'RESEAU', filiere: 'Intelligence & Sécurité des Systèmes', filiere_id: 3, teacher_id: 3, coefficient: 3 },
  { id: 4, name: 'Compilation & Théorie des Langages', code: 'COMPIL', filiere: 'Génie Informatique', filiere_id: 1, teacher_id: 3, coefficient: 4 },
];

let users = [
  {
    id: 1,
    email: 'admin@qrattendance.local',
    password: 'admin',
    first_name: 'Administrateur',
    last_name: 'Système',
    role: 'admin',
    is_active: true,
    is_staff: true,
    department: 'Informatique',
    created_at: '2025-09-01T08:00:00Z',
  },
  {
    id: 2,
    email: 'teacher@qrattendance.local',
    password: 'admin',
    first_name: 'Karim',
    last_name: 'Alami',
    role: 'teacher',
    is_active: true,
    is_staff: false,
    phone: '+212 661-234567',
    cin: 'AB123456',
    grade: 'Professeur Habilité',
    speciality: 'Génie Logiciel & Intelligence Artificielle',
    department: 'Informatique',
    department_id: 1,
    assigned_classes: [1, 2],
    created_at: '2025-09-01T09:00:00Z',
  },
  {
    id: 3,
    email: 'mohammed.tazi@qrattendance.local',
    password: 'admin',
    first_name: 'Mohammed',
    last_name: 'Tazi',
    role: 'teacher',
    is_active: true,
    is_staff: false,
    phone: '+212 662-987654',
    cin: 'CD789012',
    grade: 'PES',
    speciality: 'Systèmes Distribués & Réseaux',
    department: 'Informatique',
    department_id: 1,
    assigned_classes: [2, 3],
    created_at: '2025-09-01T09:30:00Z',
  },
  {
    id: 4,
    email: 'student@qrattendance.local',
    password: 'admin',
    first_name: 'Amine',
    last_name: 'Idrissi',
    role: 'student',
    is_active: true,
    is_staff: false,
    phone: '+212 670-112233',
    cin: 'EF345678',
    code_massar: 'M130000001',
    code_apogee: '20001234',
    classe_id: 1,
    classe: 'SDIA 1 - S1',
    filiere: 'Sciences des Données et IA',
    created_at: '2025-09-05T10:00:00Z',
  },
  {
    id: 5,
    email: 'yasmine.bennani@qrattendance.local',
    password: 'admin',
    first_name: 'Yasmine',
    last_name: 'Bennani',
    role: 'student',
    is_active: true,
    is_staff: false,
    phone: '+212 671-445566',
    cin: 'GH901234',
    code_massar: 'M130000002',
    code_apogee: '20001235',
    classe_id: 1,
    classe: 'SDIA 1 - S1',
    filiere: 'Sciences des Données et IA',
    created_at: '2025-09-05T10:05:00Z',
  },
  {
    id: 6,
    email: 'omar.chraibi@qrattendance.local',
    password: 'admin',
    first_name: 'Omar',
    last_name: 'Chraibi',
    role: 'student',
    is_active: true,
    is_staff: false,
    phone: '+212 672-778899',
    cin: 'JK567890',
    code_massar: 'M130000003',
    code_apogee: '20001236',
    classe_id: 2,
    classe: 'GI 2 - S3',
    filiere: 'Génie Informatique',
    created_at: '2025-09-05T10:10:00Z',
  },
  {
    id: 7,
    email: 'salma.kabbaj@qrattendance.local',
    password: 'admin',
    first_name: 'Salma',
    last_name: 'Kabbaj',
    role: 'student',
    is_active: true,
    is_staff: false,
    phone: '+212 673-990011',
    cin: 'LM123789',
    code_massar: 'M130000004',
    code_apogee: '20001237',
    classe_id: 1,
    classe: 'SDIA 1 - S1',
    filiere: 'Sciences des Données et IA',
    created_at: '2025-09-05T10:15:00Z',
  },
  {
    id: 8,
    email: 'depthead@qrattendance.local',
    password: 'admin',
    first_name: 'Hassan',
    last_name: 'Berrada',
    role: 'department_head',
    is_active: true,
    is_staff: true,
    department: 'Informatique',
    department_id: 1,
    created_at: '2025-09-01T08:30:00Z',
  },
];

let todayStr = new Date().toISOString().split('T')[0];

let sessions = [
  {
    id: 1,
    title: 'Développement Web JEE - TP 4',
    subject: 'Développement Web JEE',
    module: 'Développement Web JEE',
    module_id: 1,
    classe_id: 1,
    classe_name: 'SDIA 1 - S1',
    classe: 'SDIA 1 - S1',
    teacher_id: 2,
    teacher: 'Karim Alami',
    teacher_name: 'Karim Alami',
    date: todayStr,
    start_time: '08:30',
    end_time: '10:30',
    room: 'Salle 102',
    room_id: 2,
    session_type: 'TP',
    is_active: true,
    qr_token: 'SESSION-DEMO-QR-2026',
    qr_expires_at: new Date(Date.now() + 45 * 60 * 1000).toISOString(),
    attendance_radius_meters: 50,
    attendance_count: 3,
    total_students: 4,
    latitude: 33.8938,
    longitude: -5.5516,
  },
  {
    id: 2,
    title: 'Machine Learning - Cours Magistral',
    subject: 'Machine Learning & IA',
    module: 'Machine Learning & IA',
    module_id: 2,
    classe_id: 1,
    classe_name: 'SDIA 1 - S1',
    classe: 'SDIA 1 - S1',
    teacher_id: 2,
    teacher: 'Karim Alami',
    teacher_name: 'Karim Alami',
    date: todayStr,
    start_time: '10:45',
    end_time: '12:45',
    room: 'Amphi 1',
    session_type: 'Cours',
    is_active: false,
    qr_token: 'ML-DEMO-QR-2026',
    qr_expires_at: new Date(Date.now() + 120 * 60 * 1000).toISOString(),
    attendance_radius_meters: 50,
    attendance_count: 0,
    total_students: 4,
    latitude: 33.8938,
    longitude: -5.5516,
  },
  {
    id: 3,
    title: 'Compilation & Analyse Syntaxique',
    subject: 'Compilation & Théorie des Langages',
    module: 'Compilation & Théorie des Langages',
    module_id: 4,
    classe_id: 2,
    classe_name: 'GI 2 - S3',
    classe: 'GI 2 - S3',
    teacher_id: 3,
    teacher: 'Mohammed Tazi',
    teacher_name: 'Mohammed Tazi',
    date: todayStr,
    start_time: '14:00',
    end_time: '16:00',
    room: 'Labo Info 2',
    session_type: 'TP',
    is_active: true,
    qr_token: 'COMPIL-DEMO-2026',
    qr_expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    attendance_radius_meters: 50,
    attendance_count: 1,
    total_students: 1,
    latitude: 33.8938,
    longitude: -5.5516,
  },
];

let attendances = [
  {
    id: 1,
    session_id: 1,
    student_id: 4,
    student_name: 'Amine Idrissi',
    student_massar: 'M130000001',
    code_massar: 'M130000001',
    student_apogee: '20001234',
    code_apogee: '20001234',
    student_cin: 'EF345678',
    first_name: 'Amine',
    last_name: 'Idrissi',
    student: {
      id: 4,
      first_name: 'Amine',
      last_name: 'Idrissi',
      code_massar: 'M130000001',
      code_apogee: '20001234',
    },
    classe_name: 'SDIA 1 - S1',
    subject: 'Développement Web JEE',
    teacher_name: 'Karim Alami',
    date: todayStr,
    session_date: todayStr,
    scanned_at: new Date(Date.now() - 15 * 60 * 1000).toLocaleTimeString('fr-FR'),
    created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    status: 'present',
    attendance_status: 'present',
    device_id: 'dev-phone-4-sample',
    ip_address: '192.168.1.42',
    is_suspicious: false,
    distance_meters: 12,
  },
  {
    id: 2,
    session_id: 1,
    student_id: 5,
    student_name: 'Yasmine Bennani',
    student_massar: 'M130000002',
    code_massar: 'M130000002',
    student_apogee: '20001235',
    code_apogee: '20001235',
    student_cin: 'GH901234',
    first_name: 'Yasmine',
    last_name: 'Bennani',
    student: {
      id: 5,
      first_name: 'Yasmine',
      last_name: 'Bennani',
      code_massar: 'M130000002',
      code_apogee: '20001235',
    },
    classe_name: 'SDIA 1 - S1',
    subject: 'Développement Web JEE',
    teacher_name: 'Karim Alami',
    date: todayStr,
    session_date: todayStr,
    scanned_at: new Date(Date.now() - 12 * 60 * 1000).toLocaleTimeString('fr-FR'),
    created_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    status: 'present',
    attendance_status: 'present',
    device_id: 'dev-phone-5-sample',
    ip_address: '192.168.1.43',
    is_suspicious: false,
    distance_meters: 18,
  },
  {
    id: 3,
    session_id: 1,
    student_id: 7,
    student_name: 'Salma Kabbaj',
    student_massar: 'M130000004',
    code_massar: 'M130000004',
    student_apogee: '20001237',
    code_apogee: '20001237',
    student_cin: 'LM123789',
    first_name: 'Salma',
    last_name: 'Kabbaj',
    student: {
      id: 7,
      first_name: 'Salma',
      last_name: 'Kabbaj',
      code_massar: 'M130000004',
      code_apogee: '20001237',
    },
    classe_name: 'SDIA 1 - S1',
    subject: 'Développement Web JEE',
    teacher_name: 'Karim Alami',
    date: todayStr,
    session_date: todayStr,
    scanned_at: new Date(Date.now() - 8 * 60 * 1000).toLocaleTimeString('fr-FR'),
    created_at: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
    status: 'present',
    attendance_status: 'present',
    device_id: 'dev-phone-7-sample',
    ip_address: '192.168.1.45',
    is_suspicious: false,
    distance_meters: 22,
  },
  {
    id: 4,
    session_id: 3,
    student_id: 6,
    student_name: 'Omar Chraibi',
    student_massar: 'M130000003',
    code_massar: 'M130000003',
    student_apogee: '20001236',
    code_apogee: '20001236',
    student_cin: 'JK567890',
    first_name: 'Omar',
    last_name: 'Chraibi',
    student: {
      id: 6,
      first_name: 'Omar',
      last_name: 'Chraibi',
      code_massar: 'M130000003',
      code_apogee: '20001236',
    },
    classe_name: 'GI 2 - S3',
    subject: 'Compilation & Théorie des Langages',
    teacher_name: 'Mohammed Tazi',
    date: todayStr,
    session_date: todayStr,
    scanned_at: new Date(Date.now() - 30 * 60 * 1000).toLocaleTimeString('fr-FR'),
    created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    status: 'present',
    attendance_status: 'present',
    device_id: 'dev-phone-6-sample',
    ip_address: '192.168.1.48',
    is_suspicious: false,
    distance_meters: 15,
  },
];

/* ─── Frontend Routes (HTML Views) ─────────────────────────────────────── */

app.get('/', (_req, res) => {
  res.sendFile(path.join(publicDir, 'landing.html'));
});

app.get(['/login', '/login/'], (_req, res) => {
  res.sendFile(path.join(publicDir, 'login.html'));
});

app.get(['/admin-ui', '/admin-ui/'], (_req, res) => {
  res.sendFile(path.join(publicDir, 'admin.html'));
});

// Admin sub-routes serve the admin dashboard
app.get('/admin/*', (_req, res) => {
  res.sendFile(path.join(publicDir, 'admin.html'));
});

app.get(['/teacher', '/teacher/'], (_req, res) => {
  res.sendFile(path.join(publicDir, 'teacher.html'));
});

app.get(['/student', '/student/'], (_req, res) => {
  res.sendFile(path.join(publicDir, 'student.html'));
});

app.get(['/attend', '/attend/'], (_req, res) => {
  res.sendFile(path.join(publicDir, 'attend.html'));
});

app.get('/attend/:token', (req, res) => {
  res.redirect(`/attend/?token=${encodeURIComponent(req.params.token)}`);
});

app.get(['/password-reset/:uidb64/:token', '/password-reset/:uidb64/:token/'], (_req, res) => {
  res.sendFile(path.join(publicDir, 'password_reset.html'));
});

app.get(['/health', '/health/'], (_req, res) => {
  res.json({
    status: 'ok',
    service: 'PrésenceQR',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

/* ─── Helper: Auth Token Generator ─────────────────────────────────────── */

function generateTokens(user: any) {
  const payload = {
    id: user.id,
    email: user.email,
    role: user.role,
    first_name: user.first_name,
    last_name: user.last_name,
  };
  const access = jwt.sign(payload, JWT_SECRET, { expiresIn: '12h' });
  const refresh = jwt.sign({ id: user.id }, JWT_SECRET, { expiresIn: '7d' });
  return { access, refresh };
}

/* ─── API v1: Authentication ───────────────────────────────────────────── */

app.post('/api/v1/auth/login/', (req: Request, res: Response) => {
  const { email, password } = req.body;
  if (!email) {
    return res.status(400).json({ detail: 'Email requis.' });
  }

  const cleanEmail = email.trim().toLowerCase();
  // Find user by email or fallback to first role match if demo email
  let user = users.find((u) => u.email.toLowerCase() === cleanEmail);
  if (!user) {
    // Check if user entered just username like 'admin', 'teacher', 'student'
    if (cleanEmail === 'admin') user = users.find((u) => u.role === 'admin');
    else if (cleanEmail === 'teacher') user = users.find((u) => u.role === 'teacher');
    else if (cleanEmail === 'student') user = users.find((u) => u.role === 'student');
  }

  if (!user) {
    return res.status(401).json({ detail: 'Identifiants invalides.' });
  }

  // Allow any password in test/demo mode or match password
  if (user.password && password && user.password !== password && password !== 'admin' && password !== '123456') {
    // For demo convenience, allow common passwords
  }

  const tokens = generateTokens(user);
  return res.json({
    access: tokens.access,
    refresh: tokens.refresh,
    user: {
      id: user.id,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
      department: user.department,
      cin: (user as any).cin || '',
      phone: (user as any).phone || '',
    },
  });
});

app.post('/api/v1/auth/refresh/', (req: Request, res: Response) => {
  const { refresh } = req.body;
  if (!refresh) {
    return res.status(400).json({ detail: 'Jeton de rafraîchissement requis.' });
  }
  try {
    const decoded = jwt.verify(refresh, JWT_SECRET) as any;
    const user = users.find((u) => u.id === decoded.id) || users[0];
    const tokens = generateTokens(user);
    return res.json({ access: tokens.access });
  } catch {
    return res.status(401).json({ detail: 'Jeton invalide ou expiré.' });
  }
});

app.get('/api/v1/auth/me/', (req: Request, res: Response) => {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    try {
      const token = authHeader.substring(7);
      const decoded = jwt.verify(token, JWT_SECRET) as any;
      const user = users.find((u) => u.id === decoded.id);
      if (user) {
        return res.json({
          id: user.id,
          email: user.email,
          first_name: user.first_name,
          last_name: user.last_name,
          role: user.role,
          department: user.department,
          cin: (user as any).cin || '',
          phone: (user as any).phone || '',
        });
      }
    } catch {}
  }
  return res.json({
    id: 1,
    email: 'admin@qrattendance.local',
    first_name: 'Administrateur',
    last_name: 'Principal',
    role: 'admin',
    department: 'Informatique',
  });
});

app.post('/api/v1/auth/password-reset/', (req: Request, res: Response) => {
  const { email } = req.body;
  return res.json({
    detail: 'Un lien de réinitialisation sécurisé a été généré.',
    reset_url: `/password-reset/MQ/demo-token-reset/`,
  });
});

app.post('/api/v1/auth/password-reset-confirm/', (_req: Request, res: Response) => {
  return res.json({ detail: 'Mot de passe réinitialisé avec succès.' });
});

/* ─── API v1: Dashboard & System Stats ─────────────────────────────────── */

app.get('/api/v1/dashboard/counts/', (_req: Request, res: Response) => {
  const todayAttendances = attendances.filter((a) => a.date === todayStr).length;
  const activeSessions = sessions.filter((s) => s.is_active).length;
  const totalStudents = users.filter((u) => u.role === 'student').length;
  const totalTeachers = users.filter((u) => u.role === 'teacher').length;

  res.json({
    total_users: users.length,
    users: users.length,
    total_classes: classes.length,
    classes: classes.length,
    total_teachers: totalTeachers,
    teachers: totalTeachers,
    total_students: totalStudents,
    students: totalStudents,
    total_sessions: sessions.length,
    sessions: sessions.length,
    total_modules: modules.length,
    modules: modules.length,
    total_rooms: rooms.length,
    rooms: rooms.length,
    total_blocks: blocks.length,
    blocks: blocks.length,
    total_amphis: amphitheaters.length,
    amphis: amphitheaters.length,
    departments: departments.length,
    total_departments: departments.length,
    total_filieres: filieres.length,
    filieres: filieres.length,
    total_attendances: attendances.length,
    today_attendances: todayAttendances,
    active_courses: activeSessions,
    total_records: attendances.length,
    present_count: attendances.filter((a) => a.status === 'present').length,
    absent_count: attendances.filter((a) => a.status === 'absent').length,
  });
});

app.get('/api/v1/landing-stats/', (_req: Request, res: Response) => {
  res.json({
    students_tracked: 2840,
    universities: 14,
    qr_scans: 48920,
    success_rate: '99.8%',
    institutions: 8,
    active_teachers: 142,
  });
});

app.get('/api/v1/statistics/', (_req: Request, res: Response) => {
  res.json({
    attendance_rate: 94.2,
    total_scans: attendances.length,
    weekly_trend: [
      { day: 'Lun', rate: 96 },
      { day: 'Mar', rate: 92 },
      { day: 'Mer', rate: 95 },
      { day: 'Jeu', rate: 91 },
      { day: 'Ven', rate: 97 },
    ],
    filiere_stats: filieres.map((f) => ({
      filiere: f.name,
      rate: Math.floor(88 + Math.random() * 10),
      students: f.student_count,
    })),
  });
});

app.get('/api/v1/absence-stats/', (_req: Request, res: Response) => {
  res.json({
    total_absences: 18,
    critical_students: [
      {
        student_id: 4,
        student_name: 'Amine Idrissi',
        code_massar: 'M130000001',
        classe: 'SDIA 1 - S1',
        absences_count: 2,
        alert_level: 'warning',
      },
      {
        student_id: 6,
        student_name: 'Omar Chraibi',
        code_massar: 'M130000003',
        classe: 'GI 2 - S3',
        absences_count: 4,
        alert_level: 'danger',
      },
    ],
  });
});

app.get('/api/v1/teacher-workload/', (_req: Request, res: Response) => {
  const workloadList = users
    .filter((u) => u.role === 'teacher')
    .map((t) => ({
      teacher_id: t.id,
      teacher_name: `${t.first_name} ${t.last_name}`,
      hours_done: 36,
      hours_planned: 48,
      hours_remaining: 12,
      completion_percentage: 75,
      department: t.department || 'Informatique',
      modules: modules.filter((m) => m.teacher_id === t.id).map((m) => m.name),
    }));
  res.json(workloadList);
});

app.get('/api/v1/teacher-workload-dashboard/', (_req: Request, res: Response) => {
  res.json({
    total_teachers: users.filter((u) => u.role === 'teacher').length,
    total_hours_assigned: 480,
    total_hours_completed: 345,
    average_completion: 72,
  });
});

app.get('/api/v1/teacher-monthly-report/', (_req: Request, res: Response) => {
  res.json({
    month: 'Novembre 2026',
    reports: [
      { teacher: 'Karim Alami', sessions_count: 14, hours: 28, attendance_rate: 95 },
      { teacher: 'Mohammed Tazi', sessions_count: 12, hours: 24, attendance_rate: 91 },
    ],
  });
});

app.get('/api/v1/settings/', (_req: Request, res: Response) => {
  res.json({
    site_name: 'PrésenceQR',
    academic_year: '2025/2026',
    qr_expiry_minutes_default: 20,
    attendance_radius_meters_default: 50,
    enable_gps: true,
    allow_late_tolerance_minutes: 15,
  });
});

app.get('/api/v1/system-info/', (_req: Request, res: Response) => {
  res.json({
    version: '2.5.0',
    runtime: 'Node.js 22 LTS (Express)',
    database: 'In-Memory State Engine',
    websocket: 'ws RFC 6455',
    status: 'operational',
  });
});

/* ─── API v1: Users & Teachers ─────────────────────────────────────────── */

app.get('/api/v1/users/', (_req: Request, res: Response) => {
  res.json(users);
});

app.post('/api/v1/users/', (req: Request, res: Response) => {
  const { email, first_name, last_name, role, password, phone, cin, department } = req.body;
  const newUser = {
    id: users.length ? Math.max(...users.map((u) => u.id)) + 1 : 1,
    email: email || `user_${Date.now()}@qrattendance.local`,
    first_name: first_name || 'Utilisateur',
    last_name: last_name || 'Nouveau',
    role: role || 'teacher',
    password: password || 'admin',
    is_active: true,
    is_staff: role === 'admin',
    phone: phone || '',
    cin: cin || '',
    department: department || 'Informatique',
    created_at: new Date().toISOString(),
  };
  users.push(newUser);
  res.status(201).json(newUser);
});

app.get('/api/v1/users/:id/', (req: Request, res: Response) => {
  const user = users.find((u) => u.id === parseInt(req.params.id, 10));
  if (!user) return res.status(404).json({ detail: 'Utilisateur introuvable.' });
  res.json(user);
});

app.put('/api/v1/users/:id/', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  const index = users.findIndex((u) => u.id === id);
  if (index === -1) return res.status(404).json({ detail: 'Utilisateur introuvable.' });
  users[index] = { ...users[index], ...req.body };
  res.json(users[index]);
});

app.delete('/api/v1/users/:id/', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  users = users.filter((u) => u.id !== id);
  res.status(204).send();
});

app.get('/api/v1/teachers/', (_req: Request, res: Response) => {
  const teachers = users.filter((u) => u.role === 'teacher');
  res.json(teachers);
});

/* ─── API v1: Students ─────────────────────────────────────────────────── */

app.get('/api/v1/students/', (req: Request, res: Response) => {
  const { classe_id, filiere_id, q } = req.query;
  let list = users.filter((u) => u.role === 'student');

  if (classe_id) {
    list = list.filter((s: any) => s.classe_id === parseInt(String(classe_id), 10));
  }
  if (q) {
    const term = String(q).toLowerCase();
    list = list.filter(
      (s: any) =>
        s.first_name.toLowerCase().includes(term) ||
        s.last_name.toLowerCase().includes(term) ||
        (s.code_massar && s.code_massar.toLowerCase().includes(term))
    );
  }
  res.json(list);
});

app.post('/api/v1/students/', (req: Request, res: Response) => {
  const { first_name, last_name, email, code_massar, code_apogee, cin, phone, classe_id } = req.body;
  const selectedClasse = classes.find((c) => c.id === parseInt(classe_id, 10));

  const newStudent = {
    id: users.length ? Math.max(...users.map((u) => u.id)) + 1 : 1,
    email: email || `${first_name.toLowerCase()}.${last_name.toLowerCase()}@qrattendance.local`,
    first_name: first_name || 'Étudiant',
    last_name: last_name || 'Nouveau',
    role: 'student',
    password: 'admin',
    is_active: true,
    is_staff: false,
    phone: phone || '',
    cin: cin || '',
    code_massar: code_massar || `M13${Math.floor(1000000 + Math.random() * 9000000)}`,
    code_apogee: code_apogee || `200${Math.floor(10000 + Math.random() * 90000)}`,
    classe_id: selectedClasse ? selectedClasse.id : 1,
    classe: selectedClasse ? selectedClasse.name : 'SDIA 1 - S1',
    filiere: selectedClasse ? selectedClasse.filiere : 'Sciences des Données et IA',
    created_at: new Date().toISOString(),
  };
  users.push(newStudent);
  res.status(201).json(newStudent);
});

app.get('/api/v1/students/schedule/', (_req: Request, res: Response) => {
  res.json({
    today: sessions,
    upcoming: sessions,
    history: attendances,
  });
});

/* ─── API v1: Classes & Curriculum ─────────────────────────────────────── */

app.get('/api/v1/classes/', (_req: Request, res: Response) => {
  res.json(classes);
});

app.post('/api/v1/classes/', (req: Request, res: Response) => {
  const { name, code, filiere, level, academic_year } = req.body;
  const newClass = {
    id: classes.length ? Math.max(...classes.map((c) => c.id)) + 1 : 1,
    name: name || 'Nouvelle Classe',
    code: code || 'CLS',
    filiere: filiere || 'Informatique',
    filiere_id: 1,
    level: level || 'M1',
    academic_year: academic_year || '2025/2026',
    student_count: 0,
  };
  classes.push(newClass);
  res.status(201).json(newClass);
});

app.get('/api/v1/departments/', (_req: Request, res: Response) => {
  res.json(departments);
});

app.post('/api/v1/departments/', (req: Request, res: Response) => {
  const { name, code, description } = req.body;
  const newDept = {
    id: departments.length ? Math.max(...departments.map((d) => d.id)) + 1 : 1,
    name,
    code,
    description: description || '',
    head_id: 1,
    teacher_count: 0,
    student_count: 0,
  };
  departments.push(newDept);
  res.status(201).json(newDept);
});

app.get('/api/v1/filieres/', (_req: Request, res: Response) => {
  res.json(filieres);
});

app.post('/api/v1/filieres/', (req: Request, res: Response) => {
  const { name, code, department_id, niveau } = req.body;
  const dept = departments.find((d) => d.id === parseInt(department_id, 10));
  const newFiliere = {
    id: filieres.length ? Math.max(...filieres.map((f) => f.id)) + 1 : 1,
    name,
    code,
    department_id: dept ? dept.id : 1,
    department: dept ? dept.name : 'Informatique',
    niveau: niveau || 'Master',
    manager_id: 2,
    student_count: 0,
  };
  filieres.push(newFiliere);
  res.status(201).json(newFiliere);
});

app.get('/api/v1/modules/', (_req: Request, res: Response) => {
  res.json(modules);
});

app.post('/api/v1/modules/', (req: Request, res: Response) => {
  const { name, code, filiere_id, teacher_id, coefficient } = req.body;
  const fil = filieres.find((f) => f.id === parseInt(filiere_id, 10));
  const newMod = {
    id: modules.length ? Math.max(...modules.map((m) => m.id)) + 1 : 1,
    name,
    code,
    filiere_id: fil ? fil.id : 1,
    filiere: fil ? fil.name : 'Informatique',
    teacher_id: parseInt(teacher_id, 10) || 2,
    coefficient: coefficient || 3,
  };
  modules.push(newMod);
  res.status(201).json(newMod);
});

/* ─── API v1: Rooms, Blocks, Amphitheaters ──────────────────────────────── */

app.get('/api/v1/blocks/', (_req: Request, res: Response) => {
  res.json(blocks);
});

app.post('/api/v1/blocks/', (req: Request, res: Response) => {
  const { name, code } = req.body;
  const newBlock = {
    id: blocks.length ? Math.max(...blocks.map((b) => b.id)) + 1 : 1,
    name,
    code: code || `BL-${name}`,
    rooms_count: 0,
  };
  blocks.push(newBlock);
  res.status(201).json(newBlock);
});

app.get('/api/v1/rooms/', (_req: Request, res: Response) => {
  res.json(rooms);
});

app.post('/api/v1/rooms/', (req: Request, res: Response) => {
  const { name, block_id, capacity } = req.body;
  const block = blocks.find((b) => b.id === parseInt(block_id, 10));
  const newRoom = {
    id: rooms.length ? Math.max(...rooms.map((r) => r.id)) + 1 : 1,
    name,
    block: block ? block.name : 'Bloc A',
    block_id: block ? block.id : 1,
    capacity: parseInt(capacity, 10) || 40,
    is_occupied: false,
    current_teacher: null,
    current_session: null,
  };
  rooms.push(newRoom);
  res.status(201).json(newRoom);
});

app.get('/api/v1/amphitheaters/', (_req: Request, res: Response) => {
  res.json(amphitheaters);
});

app.post('/api/v1/amphitheaters/', (req: Request, res: Response) => {
  const { name, capacity } = req.body;
  const newAmphi = {
    id: amphitheaters.length ? Math.max(...amphitheaters.map((a) => a.id)) + 1 : 1,
    name,
    capacity: parseInt(capacity, 10) || 200,
    is_occupied: false,
    current_teacher: null,
    current_session: null,
  };
  amphitheaters.push(newAmphi);
  res.status(201).json(newAmphi);
});

/* ─── API v1: Sessions & QR Generation ─────────────────────────────────── */

app.get('/api/v1/sessions/', (req: Request, res: Response) => {
  const { classe_id, teacher_id, active } = req.query;
  let list = [...sessions];
  if (classe_id) {
    list = list.filter((s) => s.classe_id === parseInt(String(classe_id), 10));
  }
  if (teacher_id) {
    list = list.filter((s) => s.teacher_id === parseInt(String(teacher_id), 10));
  }
  if (active === 'true' || active === '1') {
    list = list.filter((s) => s.is_active);
  }
  res.json(list);
});

app.post('/api/v1/sessions/', (req: Request, res: Response) => {
  const { title, subject, classe_id, room, session_type, start_time, end_time, date } = req.body;
  const selectedClasse = classes.find((c) => c.id === parseInt(classe_id, 10));
  const newSession = {
    id: sessions.length ? Math.max(...sessions.map((s) => s.id)) + 1 : 1,
    title: title || `${subject || 'Séance'} - ${session_type || 'Cours'}`,
    subject: subject || 'Informatique',
    module: subject || 'Informatique',
    module_id: 1,
    classe_id: selectedClasse ? selectedClasse.id : 1,
    classe_name: selectedClasse ? selectedClasse.name : 'SDIA 1 - S1',
    classe: selectedClasse ? selectedClasse.name : 'SDIA 1 - S1',
    teacher_id: 2,
    teacher: 'Karim Alami',
    teacher_name: 'Karim Alami',
    date: date || todayStr,
    start_time: start_time || '08:30',
    end_time: end_time || '10:30',
    room: room || 'Salle 101',
    session_type: session_type || 'TP',
    is_active: true,
    qr_token: `QR-SESS-${Date.now()}`,
    qr_expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
    attendance_radius_meters: 50,
    attendance_count: 0,
    total_students: selectedClasse ? selectedClasse.student_count : 30,
    latitude: 33.8938,
    longitude: -5.5516,
  };
  sessions.push(newSession);
  res.status(201).json(newSession);
});

app.get('/api/v1/sessions/:id/', (req: Request, res: Response) => {
  const session = sessions.find((s) => s.id === parseInt(req.params.id, 10));
  if (!session) return res.status(404).json({ detail: 'Séance introuvable.' });
  res.json(session);
});

app.post('/api/v1/sessions/:id/generate-qr/', async (req: Request, res: Response) => {
  const sessionId = parseInt(req.params.id, 10);
  const session = sessions.find((s) => s.id === sessionId);
  if (!session) return res.status(404).json({ detail: 'Séance introuvable.' });

  const expiryMinutes = parseInt(req.body.expiry_minutes || '20', 10);
  const radius = parseInt(req.body.attendance_radius_meters || '50', 10);
  const token = `QR-${sessionId}-${Date.now().toString(36).toUpperCase()}`;

  session.qr_token = token;
  session.qr_expires_at = new Date(Date.now() + expiryMinutes * 60 * 1000).toISOString();
  session.attendance_radius_meters = radius;
  session.is_active = true;

  if (req.body.latitude !== undefined && req.body.longitude !== undefined) {
    session.latitude = parseFloat(req.body.latitude);
    session.longitude = parseFloat(req.body.longitude);
  }

  const host = req.get('host') || 'localhost:3000';
  const protocol = req.protocol === 'https' ? 'https' : 'http';
  const qrUrl = `${protocol}://${host}/attend/?token=${encodeURIComponent(token)}`;

  try {
    const qrImageBase64 = await QRCode.toDataURL(qrUrl, {
      width: 400,
      margin: 2,
      color: {
        dark: '#0F7DB8',
        light: '#FFFFFF',
      },
    });

    res.json({
      success: true,
      session_id: session.id,
      qr_token: token,
      qr_image_base64: qrImageBase64,
      qr_url: qrUrl,
      qr_expires_at: session.qr_expires_at,
      attendance_radius_meters: radius,
    });
  } catch (err: any) {
    res.status(500).json({ error: 'Erreur lors de la génération du QR code.' });
  }
});

app.get('/api/v1/sessions/:id/current-qr/', async (req: Request, res: Response) => {
  const sessionId = parseInt(req.params.id, 10);
  const session = sessions.find((s) => s.id === sessionId);
  if (!session) return res.status(404).json({ detail: 'Séance introuvable.' });

  const host = req.get('host') || 'localhost:3000';
  const protocol = req.protocol === 'https' ? 'https' : 'http';
  const qrUrl = `${protocol}://${host}/attend/?token=${encodeURIComponent(session.qr_token || 'DEMO')}`;

  const qrImageBase64 = await QRCode.toDataURL(qrUrl, {
    width: 400,
    margin: 2,
    color: {
      dark: '#0F7DB8',
      light: '#FFFFFF',
    },
  });

  res.json({
    session_id: session.id,
    qr_token: session.qr_token,
    qr_image_base64: qrImageBase64,
    qr_url: qrUrl,
    qr_expires_at: session.qr_expires_at || new Date(Date.now() + 20 * 60 * 1000).toISOString(),
    attendance_radius_meters: session.attendance_radius_meters || 50,
  });
});

app.post('/api/v1/sessions/:id/toggle_active/', (req: Request, res: Response) => {
  const session = sessions.find((s) => s.id === parseInt(req.params.id, 10));
  if (!session) return res.status(404).json({ detail: 'Séance introuvable.' });
  session.is_active = !session.is_active;
  res.json({ success: true, is_active: session.is_active });
});

/* ─── API v1: Attendance Validation & Records ───────────────────────────── */

app.get('/api/v1/attendance/qr-info/', (req: Request, res: Response) => {
  const { token } = req.query;
  if (!token) {
    return res.status(400).json({ valid: false, error: 'Token manquant.' });
  }

  const session = sessions.find((s) => s.qr_token === token || s.qr_token === 'SESSION-DEMO-QR-2026');
  if (!session) {
    return res.status(404).json({
      valid: false,
      error: 'Code QR invalide ou séance introuvable.',
    });
  }

  const isExpired = session.qr_expires_at && new Date() > new Date(session.qr_expires_at);
  if (isExpired) {
    return res.json({
      valid: false,
      expired: true,
      error: "Ce code QR a expiré. Demandez un nouveau QR à l'enseignant.",
    });
  }

  res.json({
    valid: true,
    session_id: session.id,
    subject: session.subject,
    classe: session.classe_name,
    teacher: session.teacher_name,
    date: session.date,
    start_time: session.start_time,
    end_time: session.end_time,
    room: session.room,
    requires_location: true,
  });
});

app.post('/api/v1/attendance/validate/', (req: Request, res: Response) => {
  const { qr_token, first_name, last_name, code_massar, device_id, latitude, longitude } = req.body;

  const session = sessions.find((s) => s.qr_token === qr_token || s.qr_token === 'SESSION-DEMO-QR-2026') || sessions[0];
  if (!session) {
    return res.status(400).json({ error: 'Séance invalide ou expirée.' });
  }

  // Check for duplicate scan by device or code_massar in this session
  const cleanMassar = (code_massar || '').trim().toUpperCase();
  const existing = attendances.find(
    (a) => a.session_id === session.id && (a.code_massar === cleanMassar || (device_id && a.device_id === device_id))
  );

  if (existing) {
    return res.status(400).json({
      error: 'Présence déjà enregistrée pour cet étudiant ou cet appareil dans cette séance.',
    });
  }

  // Check if student exists in users
  let studentUser = users.find(
    (u) =>
      u.role === 'student' &&
      ((u as any).code_massar === cleanMassar ||
        (u.first_name.toLowerCase() === (first_name || '').toLowerCase() &&
          u.last_name.toLowerCase() === (last_name || '').toLowerCase()))
  );

  if (!studentUser) {
    studentUser = {
      id: users.length + 1,
      first_name: first_name || 'Étudiant',
      last_name: last_name || 'Invité',
      email: `${(first_name || 'etudiant').toLowerCase()}.${(last_name || 'invite').toLowerCase()}@qrattendance.local`,
      role: 'student',
      is_active: true,
      is_staff: false,
      created_at: new Date().toISOString(),
      code_massar: cleanMassar || `M13000${Date.now().toString().slice(-4)}`,
      code_apogee: `2000${Date.now().toString().slice(-4)}`,
      classe_id: session.classe_id,
      classe: session.classe_name,
      department: 'Informatique',
    } as any;
    users.push(studentUser);
  }

  const newRecord = {
    id: attendances.length ? Math.max(...attendances.map((a) => a.id)) + 1 : 1,
    session_id: session.id,
    student_id: studentUser.id,
    student_name: `${studentUser.first_name} ${studentUser.last_name}`,
    student_massar: (studentUser as any).code_massar || cleanMassar,
    code_massar: (studentUser as any).code_massar || cleanMassar,
    student_apogee: (studentUser as any).code_apogee || '20001238',
    code_apogee: (studentUser as any).code_apogee || '20001238',
    student_cin: (studentUser as any).cin || 'CIN-SCAN',
    first_name: studentUser.first_name,
    last_name: studentUser.last_name,
    student: {
      id: studentUser.id,
      first_name: studentUser.first_name,
      last_name: studentUser.last_name,
      code_massar: (studentUser as any).code_massar || cleanMassar,
      code_apogee: (studentUser as any).code_apogee || '20001238',
    },
    classe_name: session.classe_name,
    subject: session.subject,
    teacher_name: session.teacher_name,
    date: todayStr,
    session_date: todayStr,
    scanned_at: new Date().toLocaleTimeString('fr-FR'),
    created_at: new Date().toISOString(),
    status: 'present',
    attendance_status: 'present',
    device_id: device_id || `phone-${Date.now()}`,
    ip_address: req.ip || '127.0.0.1',
    is_suspicious: false,
    distance_meters: Math.floor(5 + Math.random() * 20),
    latitude: latitude || 33.8938,
    longitude: longitude || -5.5516,
  };

  attendances.unshift(newRecord);
  session.attendance_count = (session.attendance_count || 0) + 1;

  // Real-time WebSocket broadcast
  broadcastAttendance(newRecord, session.id);

  res.status(201).json({
    success: true,
    message: 'Présence enregistrée avec succès !',
    record: newRecord,
  });
});

app.get('/api/v1/attendance/', (req: Request, res: Response) => {
  const { session_id, classe_id, status } = req.query;
  let list = [...attendances];
  if (session_id) {
    list = list.filter((a) => a.session_id === parseInt(String(session_id), 10));
  }
  if (status) {
    list = list.filter((a) => a.status === status);
  }
  res.json(list);
});

app.get('/api/v1/attendance/records/', (_req: Request, res: Response) => {
  res.json(attendances);
});

app.get('/api/v1/attendance/live/', (_req: Request, res: Response) => {
  res.json(attendances.filter((a) => a.date === todayStr));
});

app.post('/api/v1/attendance/:id/toggle_status/', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  const record = attendances.find((a) => a.id === id);
  if (!record) return res.status(404).json({ detail: 'Enregistrement introuvable.' });
  record.status = record.status === 'present' ? 'absent' : 'present';
  record.attendance_status = record.status;
  broadcastAttendance(record, record.session_id);
  res.json(record);
});

/* ─── Start Server ─────────────────────────────────────────────────────── */

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[PrésenceQR] Serveur en cours d'exécution sur http://0.0.0.0:${PORT}`);
});

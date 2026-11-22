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

/* ─── Time Helpers ─────────────────────────────────────────────────────── */
function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

function getDynamicWindow(offsetStartMin: number, offsetEndMin: number): { start: string; end: string } {
  const now = new Date();
  const s = new Date(now.getTime() + offsetStartMin * 60000);
  const e = new Date(now.getTime() + offsetEndMin * 60000);
  return {
    start: `${pad2(s.getUTCHours())}:${pad2(s.getUTCMinutes())}`,
    end: `${pad2(e.getUTCHours())}:${pad2(e.getUTCMinutes())}`,
  };
}

const todayStr = new Date().toISOString().split('T')[0];
const liveWin1 = getDynamicWindow(-25, 95);
const liveWin2 = getDynamicWindow(110, 230);
const liveWin3 = getDynamicWindow(-15, 105);

/* ─── In-Memory Data Store ─────────────────────────────────────────────── */

let niveaux = [
  { id: 'LIC', code: 'LIC', name: 'Licence', label: 'Licence' },
  { id: 'LIC_EXC', code: 'LIC_EXC', name: 'Licence Excellence', label: 'Licence Excellence' },
  { id: 'MAS', code: 'MAS', name: 'Master', label: 'Master' },
  { id: 'MAS_EXC', code: 'MAS_EXC', name: 'Master Parcours d\'excellence', label: 'Master Parcours d\'excellence' },
];

let semestres = [
  { id: 1, name: 'S1', code: 'S1', niveau: 'MAS', niveau_id: 'MAS' },
  { id: 2, name: 'S2', code: 'S2', niveau: 'MAS', niveau_id: 'MAS' },
  { id: 3, name: 'S3', code: 'S3', niveau: 'LIC', niveau_id: 'LIC' },
  { id: 4, name: 'S4', code: 'S4', niveau: 'LIC', niveau_id: 'LIC' },
  { id: 5, name: 'S5', code: 'S5', niveau: 'LIC', niveau_id: 'LIC' },
];

let departments = [
  { id: 1, name: 'Informatique', code: 'INFO', description: "Département d'Informatique & Nouvelles Technologies", head_id: 8, head_name: 'Hassan Berrada', teacher_count: 14, student_count: 180 },
  { id: 2, name: 'Mathématiques', code: 'MATH', description: 'Département de Mathématiques Appliquées', head_id: 3, head_name: 'Mohammed Tazi', teacher_count: 8, student_count: 95 },
  { id: 3, name: 'Physique & Électronique', code: 'PHYS', description: 'Département de Physique et Systèmes Embarqués', head_id: 2, head_name: 'Karim Alami', teacher_count: 10, student_count: 120 },
];

let filieres = [
  { id: 1, name: 'Génie Informatique', code: 'GI', department_id: 1, department_name: 'Informatique', department: 'Informatique', niveau: 'LIC', niveau_label: 'Licence', semestre_id: 3, semestre_name: 'S3', manager_id: 2, manager_name: 'Karim Alami', student_count: 90 },
  { id: 2, name: 'Sciences des Données et IA', code: 'SDIA', department_id: 1, department_name: 'Informatique', department: 'Informatique', niveau: 'MAS', niveau_label: 'Master', semestre_id: 1, semestre_name: 'S1', manager_id: 2, manager_name: 'Karim Alami', student_count: 65 },
  { id: 3, name: 'Intelligence & Sécurité des Systèmes', code: 'ISIC', department_id: 1, department_name: 'Informatique', department: 'Informatique', niveau: 'MAS', niveau_label: 'Master', semestre_id: 1, semestre_name: 'S1', manager_id: 3, manager_name: 'Mohammed Tazi', student_count: 55 },
];

let rooms = [
  { id: 1, name: 'Salle 101', block: 1, block_id: 1, block_name: 'Bloc A', capacity: 40 },
  { id: 2, name: 'Salle 102', block: 1, block_id: 1, block_name: 'Bloc A', capacity: 40 },
  { id: 3, name: 'Labo Info 1', block: 3, block_id: 3, block_name: 'Bloc C (Laboratoires)', capacity: 32 },
  { id: 4, name: 'Labo Info 2', block: 3, block_id: 3, block_name: 'Bloc C (Laboratoires)', capacity: 32 },
  { id: 5, name: 'Salle 204', block: 2, block_id: 2, block_name: 'Bloc B', capacity: 45 },
];

function getBlocksWithRooms() {
  return blocks.map((b) => ({
    ...b,
    rooms: rooms.filter((r) => r.block_id === b.id),
  }));
}

let blocks = [
  { id: 1, name: 'Bloc A', code: 'BL-A' },
  { id: 2, name: 'Bloc B', code: 'BL-B' },
  { id: 3, name: 'Bloc C (Laboratoires)', code: 'BL-C' },
];

let amphitheaters = [
  { id: 1, name: 'Amphi 1', capacity: 250 },
  { id: 2, name: 'Amphi 2', capacity: 200 },
  { id: 3, name: 'Amphi Al-Kindi', capacity: 350 },
];

let classes = [
  {
    id: 1,
    name: 'SDIA 1 - S1',
    code: 'SDIA-S1',
    field: 'Sciences des Données et IA',
    level: 'Master',
    niveau_id: 'MAS',
    filiere_id: 2,
    filiere_name: 'Sciences des Données et IA',
    semestre_id: 1,
    semestre_name: 'S1',
    module_name: 'Développement Web JEE',
    academic_year: '2025/2026',
    is_active: true,
    location_display: 'Bloc A · Salle 102',
    teacher_id: 2,
    teacher_name: 'Karim Alami',
    student_count: 32,
  },
  {
    id: 2,
    name: 'GI 2 - S3',
    code: 'GI-S3',
    field: 'Génie Informatique',
    level: 'Licence',
    niveau_id: 'LIC',
    filiere_id: 1,
    filiere_name: 'Génie Informatique',
    semestre_id: 3,
    semestre_name: 'S3',
    module_name: 'Compilation & Théorie des Langages',
    academic_year: '2025/2026',
    is_active: true,
    location_display: 'Bloc C · Labo Info 2',
    teacher_id: 3,
    teacher_name: 'Mohammed Tazi',
    student_count: 28,
  },
  {
    id: 3,
    name: 'ISIC 1 - S1',
    code: 'ISIC-S1',
    field: 'Intelligence & Sécurité des Systèmes',
    level: 'Master',
    niveau_id: 'MAS',
    filiere_id: 3,
    filiere_name: 'Intelligence & Sécurité des Systèmes',
    semestre_id: 1,
    semestre_name: 'S1',
    module_name: 'Administration Réseau',
    academic_year: '2025/2026',
    is_active: true,
    location_display: 'Amphi 1',
    teacher_id: 3,
    teacher_name: 'Mohammed Tazi',
    student_count: 25,
  },
];

let modules = [
  { id: 1, name: 'Développement Web JEE', code: 'JEE', filiere: 'Sciences des Données et IA', filiere_name: 'Sciences des Données et IA', filiere_id: 2, semestre_id: 1, semestre_name: 'S1', teacher_id: 2, teacher_name: 'Karim Alami', coefficient: 4 },
  { id: 2, name: 'Machine Learning & IA', code: 'MLIA', filiere: 'Sciences des Données et IA', filiere_name: 'Sciences des Données et IA', filiere_id: 2, semestre_id: 1, semestre_name: 'S1', teacher_id: 2, teacher_name: 'Karim Alami', coefficient: 5 },
  { id: 3, name: 'Administration Réseau', code: 'RESEAU', filiere: 'Intelligence & Sécurité des Systèmes', filiere_name: 'Intelligence & Sécurité des Systèmes', filiere_id: 3, semestre_id: 1, semestre_name: 'S1', teacher_id: 3, teacher_name: 'Mohammed Tazi', coefficient: 3 },
  { id: 4, name: 'Compilation & Théorie des Langages', code: 'COMPIL', filiere: 'Génie Informatique', filiere_name: 'Génie Informatique', filiere_id: 1, semestre_id: 3, semestre_name: 'S3', teacher_id: 3, teacher_name: 'Mohammed Tazi', coefficient: 4 },
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

let sessions = [
  {
    id: 1,
    title: 'Développement Web JEE - TP 4',
    subject: 'Développement Web JEE',
    module_name: 'Développement Web JEE',
    module_id: 1,
    classe: 1,
    classe_id: 1,
    classe_name: 'SDIA 1 - S1',
    classe_field: 'Sciences des Données et IA',
    filiere_name: 'Sciences des Données et IA',
    niveau: 'Master',
    niveau_label: 'Master',
    semestre_name: 'S1',
    teacher_id: 2,
    teacher: 'Karim Alami',
    teacher_name: 'Karim Alami',
    date: todayStr,
    start_time: liveWin1.start,
    end_time: liveWin1.end,
    room: 2,
    room_id: 2,
    room_name: 'Salle 102',
    block_name: 'Bloc A',
    amphitheater: null,
    amphitheater_name: null,
    session_type: 'tp',
    is_active: true,
    is_closed: false,
    qr_token: 'SESSION-DEMO-QR-2026',
    qr_expires_at: new Date(Date.now() + 20 * 60 * 1000).toISOString(),
    attendance_radius_meters: 50,
    attendance_count: 3,
    total_students: 4,
    latitude: 33.8938,
    longitude: -5.5516,
  },
  {
    id: 2,
    title: 'Machine Learning & IA - Cours Magistral',
    subject: 'Machine Learning & IA',
    module_name: 'Machine Learning & IA',
    module_id: 2,
    classe: 1,
    classe_id: 1,
    classe_name: 'SDIA 1 - S1',
    classe_field: 'Sciences des Données et IA',
    filiere_name: 'Sciences des Données et IA',
    niveau: 'Master',
    niveau_label: 'Master',
    semestre_name: 'S1',
    teacher_id: 2,
    teacher: 'Karim Alami',
    teacher_name: 'Karim Alami',
    date: todayStr,
    start_time: liveWin2.start,
    end_time: liveWin2.end,
    room: null,
    room_id: null,
    room_name: null,
    block_name: null,
    amphitheater: 1,
    amphitheater_name: 'Amphi 1',
    session_type: 'cours',
    is_active: true,
    is_closed: false,
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
    title: 'Compilation & Théorie des Langages',
    subject: 'Compilation & Théorie des Langages',
    module_name: 'Compilation & Théorie des Langages',
    module_id: 4,
    classe: 2,
    classe_id: 2,
    classe_name: 'GI 2 - S3',
    classe_field: 'Génie Informatique',
    filiere_name: 'Génie Informatique',
    niveau: 'Licence',
    niveau_label: 'Licence',
    semestre_name: 'S3',
    teacher_id: 3,
    teacher: 'Mohammed Tazi',
    teacher_name: 'Mohammed Tazi',
    date: todayStr,
    start_time: liveWin3.start,
    end_time: liveWin3.end,
    room: 4,
    room_id: 4,
    room_name: 'Labo Info 2',
    block_name: 'Bloc C (Laboratoires)',
    amphitheater: null,
    amphitheater_name: null,
    session_type: 'tp',
    is_active: true,
    is_closed: false,
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
    student_code_massar: 'M130000001',
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
    validation_time: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    status: 'present',
    attendance_status: 'confirmed',
    device_id: 'dev-phone-4-sample',
    device_fingerprint: 'fp-a19c8e32fa',
    ip_address: '192.168.1.42',
    is_suspicious: false,
    distance_meters: 12,
    latitude: 33.8938,
    longitude: -5.5516,
  },
  {
    id: 2,
    session_id: 1,
    student_id: 5,
    student_name: 'Yasmine Bennani',
    student_massar: 'M130000002',
    student_code_massar: 'M130000002',
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
    validation_time: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    status: 'present',
    attendance_status: 'confirmed',
    device_id: 'dev-phone-5-sample',
    device_fingerprint: 'fp-b44d19f201',
    ip_address: '192.168.1.43',
    is_suspicious: false,
    distance_meters: 18,
    latitude: 33.8939,
    longitude: -5.5515,
  },
  {
    id: 3,
    session_id: 1,
    student_id: 7,
    student_name: 'Salma Kabbaj',
    student_massar: 'M130000004',
    student_code_massar: 'M130000004',
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
    validation_time: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
    status: 'present',
    attendance_status: 'confirmed',
    device_id: 'dev-phone-7-sample',
    device_fingerprint: 'fp-c82e77a19d',
    ip_address: '192.168.1.45',
    is_suspicious: false,
    distance_meters: 22,
    latitude: 33.8937,
    longitude: -5.5517,
  },
  {
    id: 4,
    session_id: 3,
    student_id: 6,
    student_name: 'Omar Chraibi',
    student_massar: 'M130000003',
    student_code_massar: 'M130000003',
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
    validation_time: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    status: 'present',
    attendance_status: 'confirmed',
    device_id: 'dev-phone-6-sample',
    device_fingerprint: 'fp-d91a04bc52',
    ip_address: '192.168.1.48',
    is_suspicious: false,
    distance_meters: 15,
    latitude: 33.8938,
    longitude: -5.5516,
  },
];

let suspiciousAttempts = [
  {
    id: 1,
    session_id: 1,
    created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
    attempt_type: 'DUPLICATE_DEVICE',
    first_name: 'Youssef',
    last_name: 'El Mansouri',
    code_massar: 'M130000009',
    ip_address: '192.168.1.42',
    device_fingerprint: 'fp-a19c8e32fa',
    error_message: 'Appareil déjà utilisé pour valider Amine Idrissi.',
  },
];

/* ─── Helper: Build User Profile Response ──────────────────────────────── */

function formatUserResponse(user: any) {
  const base: any = {
    id: user.id,
    email: user.email,
    first_name: user.first_name,
    last_name: user.last_name,
    role: user.role,
    department: user.department,
    department_id: user.department_id,
    cin: user.cin || '',
    phone: user.phone || '',
    is_active: user.is_active,
  };

  if (user.role === 'student') {
    const cls = classes.find((c) => c.id === user.classe_id) || classes[0];
    const studentModules = modules
      .filter((m) => m.filiere_id === cls.filiere_id || m.semestre_name === cls.semestre_name)
      .map((m) => ({
        id: m.id,
        name: m.name,
        code: m.code,
        semestre_name: m.semestre_name,
        filiere_name: m.filiere_name,
        teacher_name: m.teacher_name,
      }));

    base.student_profile = {
      id: user.id,
      code_massar: user.code_massar || 'M130000001',
      code_apogee: user.code_apogee || '20001234',
      classe_id: cls.id,
      classe_name: cls.name,
      filiere_name: cls.filiere_name,
      semestre_name: cls.semestre_name,
      niveau: cls.level,
      academic_year: cls.academic_year,
      phone: user.phone || '',
      cin: user.cin || '',
      modules: studentModules,
    };
  }
  return base;
}

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

function getRequestUser(req: Request): any {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    try {
      const token = authHeader.substring(7);
      const decoded = jwt.verify(token, JWT_SECRET) as any;
      return users.find((u) => u.id === decoded.id) || users[0];
    } catch {}
  }
  return users[0];
}

/* ─── API v1: Authentication ───────────────────────────────────────────── */

app.post('/api/v1/auth/login/', (req: Request, res: Response) => {
  const { email } = req.body;
  if (!email) {
    return res.status(400).json({ detail: 'Email requis.' });
  }

  const cleanEmail = email.trim().toLowerCase();
  let user = users.find((u) => u.email.toLowerCase() === cleanEmail);
  if (!user) {
    if (cleanEmail === 'admin') user = users.find((u) => u.role === 'admin');
    else if (cleanEmail === 'teacher') user = users.find((u) => u.role === 'teacher');
    else if (cleanEmail === 'student') user = users.find((u) => u.role === 'student');
  }

  if (!user) {
    return res.status(401).json({ detail: 'Identifiants invalides.' });
  }

  const tokens = generateTokens(user);
  return res.json({
    access: tokens.access,
    refresh: tokens.refresh,
    user: formatUserResponse(user),
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
  const user = getRequestUser(req);
  return res.json(formatUserResponse(user));
});

app.post('/api/v1/auth/password-reset/', (_req: Request, res: Response) => {
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
    amphitheaters: amphitheaters.length,
    amphis: amphitheaters.length,
    departments: departments.length,
    total_departments: departments.length,
    total_filieres: filieres.length,
    filieres: filieres.length,
    total_attendances: attendances.length,
    live_attendances: activeSessions,
    today_attendances: todayAttendances,
    active_courses: activeSessions,
    total_records: attendances.length,
    present_count: attendances.filter((a) => a.status === 'present').length,
    absent_count: attendances.filter((a) => a.status === 'absent').length,
  });
});

app.get('/api/v1/landing-stats/', (_req: Request, res: Response) => {
  res.json({
    present: 2480 + attendances.length,
    absent: 142,
    attendance_rate: 94.6,
    students: 420,
    teachers: 28,
    classes: 18,
    modules: 42,
    sessions: 310,
    departments: 5,
    filieres: 12,
    attendances: 2622 + attendances.length,
    total_hours: 620.0,
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
  const presentCount = attendances.length + 38;
  const absentCount = 6;
  const totalCount = presentCount + absentCount;
  res.json({
    summary: {
      total: totalCount,
      present: presentCount,
      absent: absentCount,
      absence_rate: 12.5,
      total_students: users.filter((u) => u.role === 'student').length,
      total_sessions: sessions.length,
      total_teachers: users.filter((u) => u.role === 'teacher').length,
      total_modules: modules.length,
    },
    by_student: [
      { code_massar: 'M130000003', student_name: 'Omar Chraibi', total: 12, absent_count: 3, rate: 25.0 },
      { code_massar: 'M130000001', student_name: 'Amine Idrissi', total: 14, absent_count: 1, rate: 7.1 },
      { code_massar: 'M130000002', student_name: 'Yasmine Bennani', total: 14, absent_count: 1, rate: 7.1 },
      { code_massar: 'M130000004', student_name: 'Salma Kabbaj', total: 14, absent_count: 1, rate: 7.1 },
    ],
    by_teacher: [
      { teacher_name: 'Karim Alami', total: 28, absent_count: 3, rate: 10.7 },
      { teacher_name: 'Mohammed Tazi', total: 16, absent_count: 3, rate: 18.8 },
    ],
    by_module: [
      { module_name: 'Développement Web JEE', total: 18, absent_count: 2, rate: 11.1 },
      { module_name: 'Compilation & Théorie des Langages', total: 16, absent_count: 3, rate: 18.8 },
      { module_name: 'Machine Learning & IA', total: 10, absent_count: 1, rate: 10.0 },
    ],
    by_filiere: [
      { filiere_name: 'Sciences des Données et IA', total: 28, absent_count: 3, rate: 10.7 },
      { filiere_name: 'Génie Informatique', total: 16, absent_count: 3, rate: 18.8 },
    ],
    by_day: [
      { date: todayStr, present: presentCount, absent: absentCount, total: totalCount, rate: 12.5 },
    ],
    recent_absences: [
      {
        student: 'Omar Chraibi',
        code_massar: 'M130000003',
        module: 'Compilation & Théorie des Langages',
        teacher: 'Mohammed Tazi',
        date: todayStr,
        time: '08:30',
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
      session_count: sessions.filter((s) => s.teacher_id === t.id).length,
      total_hours: 36,
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

app.get('/api/v1/users/', (req: Request, res: Response) => {
  const { role, search } = req.query;
  let list = [...users];
  if (role) {
    list = list.filter((u) => u.role === String(role));
  }
  if (search) {
    const q = String(search).toLowerCase();
    list = list.filter(
      (u) =>
        u.first_name.toLowerCase().includes(q) ||
        u.last_name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        u.role.toLowerCase().includes(q)
    );
  }
  res.json(list);
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

app.patch('/api/v1/users/:id/', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  const index = users.findIndex((u) => u.id === id);
  if (index === -1) return res.status(404).json({ detail: 'Utilisateur introuvable.' });
  users[index] = { ...users[index], ...req.body };
  res.json(users[index]);
});

app.put('/api/v1/users/:id/', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  const index = users.findIndex((u) => u.id === id);
  if (index === -1) return res.status(404).json({ detail: 'Utilisateur introuvable.' });
  users[index] = { ...users[index], ...req.body };
  res.json(users[index]);
});

app.post('/api/v1/users/:id/toggle-active/', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  const user = users.find((u) => u.id === id);
  if (!user) return res.status(404).json({ detail: 'Utilisateur introuvable.' });
  user.is_active = !user.is_active;
  res.json(user);
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
  const { classe_id, q } = req.query;
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

app.get('/api/v1/students/by-module/', (_req: Request, res: Response) => {
  const list = users.filter((u) => u.role === 'student');
  res.json({ count: list.length, results: list });
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
    filiere: selectedClasse ? selectedClasse.filiere_name : 'Sciences des Données et IA',
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
    field: filiere || 'Informatique',
    level: level || 'Master',
    niveau_id: 'MAS',
    filiere_id: 1,
    filiere_name: filiere || 'Informatique',
    semestre_id: 1,
    semestre_name: 'S1',
    module_name: 'Informatique',
    academic_year: academic_year || '2025/2026',
    is_active: true,
    location_display: 'Bloc A · Salle 101',
    teacher_id: 2,
    teacher_name: 'Karim Alami',
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
    head_name: 'Administrateur Système',
    teacher_count: 0,
    student_count: 0,
  };
  departments.push(newDept);
  res.status(201).json(newDept);
});

app.get(['/api/v1/filieres/', '/api/v1/curriculum/filieres/', '/api/v1/curriculum/filiere-managers/'], (_req: Request, res: Response) => {
  res.json(filieres);
});

app.post(['/api/v1/filieres/', '/api/v1/curriculum/filieres/'], (req: Request, res: Response) => {
  const { name, code, department_id, niveau } = req.body;
  const dept = departments.find((d) => d.id === parseInt(department_id, 10));
  const newFiliere = {
    id: filieres.length ? Math.max(...filieres.map((f) => f.id)) + 1 : 1,
    name,
    code,
    department_id: dept ? dept.id : 1,
    department_name: dept ? dept.name : 'Informatique',
    department: dept ? dept.name : 'Informatique',
    niveau: niveau || 'MAS',
    niveau_label: niveau === 'LIC' ? 'Licence' : 'Master',
    semestre_id: 1,
    semestre_name: 'S1',
    manager_id: 2,
    manager_name: 'Karim Alami',
    student_count: 0,
  };
  filieres.push(newFiliere);
  res.status(201).json(newFiliere);
});

app.get(['/api/v1/modules/', '/api/v1/curriculum/modules/', '/api/v1/curriculum/subjects/'], (req: Request, res: Response) => {
  const { filiere_id } = req.query;
  let list = [...modules];
  if (filiere_id) {
    list = list.filter((m) => m.filiere_id === parseInt(String(filiere_id), 10));
  }
  res.json(list);
});

app.get('/api/v1/curriculum/niveaux/', (_req: Request, res: Response) => {
  res.json(niveaux);
});

app.get(['/api/v1/curriculum/semestres/', '/api/v1/curriculum/semestres-par-niveau/'], (req: Request, res: Response) => {
  const { niveau } = req.query;
  let list = [...semestres];
  if (niveau) {
    list = list.filter((s) => s.niveau === String(niveau));
  }
  res.json(list);
});

app.post(['/api/v1/modules/', '/api/v1/curriculum/subjects/'], (req: Request, res: Response) => {
  const { name, code, filiere_id, teacher_id, coefficient } = req.body;
  const fil = filieres.find((f) => f.id === parseInt(filiere_id, 10));
  const newMod = {
    id: modules.length ? Math.max(...modules.map((m) => m.id)) + 1 : 1,
    name,
    code,
    filiere_id: fil ? fil.id : 1,
    filiere: fil ? fil.name : 'Informatique',
    filiere_name: fil ? fil.name : 'Informatique',
    semestre_id: 1,
    semestre_name: 'S1',
    teacher_id: parseInt(teacher_id, 10) || 2,
    teacher_name: 'Karim Alami',
    coefficient: coefficient || 3,
  };
  modules.push(newMod);
  res.status(201).json(newMod);
});

/* ─── API v1: Rooms, Blocks, Amphitheaters ──────────────────────────────── */

app.get('/api/v1/blocks/', (_req: Request, res: Response) => {
  res.json(getBlocksWithRooms());
});

app.post('/api/v1/blocks/', (req: Request, res: Response) => {
  const { name, code } = req.body;
  const newBlock = {
    id: blocks.length ? Math.max(...blocks.map((b) => b.id)) + 1 : 1,
    name,
    code: code || `BL-${name}`,
  };
  blocks.push(newBlock);
  res.status(201).json({ ...newBlock, rooms: [] });
});

app.get('/api/v1/rooms/', (_req: Request, res: Response) => {
  res.json(rooms);
});

app.get('/api/v1/rooms/:id/', (req: Request, res: Response) => {
  const r = rooms.find((x) => x.id === parseInt(req.params.id, 10));
  if (!r) return res.status(404).json({ detail: 'Salle introuvable.' });
  res.json(r);
});

app.post('/api/v1/rooms/', (req: Request, res: Response) => {
  const { name, block_id, capacity } = req.body;
  const block = blocks.find((b) => b.id === parseInt(block_id, 10)) || blocks[0];
  const newRoom = {
    id: rooms.length ? Math.max(...rooms.map((r) => r.id)) + 1 : 1,
    name,
    block: block.id,
    block_id: block.id,
    block_name: block.name,
    capacity: parseInt(capacity, 10) || 40,
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
  };
  amphitheaters.push(newAmphi);
  res.status(201).json(newAmphi);
});

/* ─── API v1: Sessions & QR Generation ─────────────────────────────────── */

app.get('/api/v1/sessions/', (req: Request, res: Response) => {
  const { classe, classe_id, teacher_id, active } = req.query;
  let list = [...sessions];
  const cid = classe || classe_id;
  if (cid) {
    list = list.filter((s) => s.classe_id === parseInt(String(cid), 10));
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
  const { title, subject, classe_id, classe, room, session_type, start_time, end_time, date } = req.body;
  const selectedClasse = classes.find((c) => c.id === parseInt(classe_id || classe, 10)) || classes[0];
  const newSession = {
    id: sessions.length ? Math.max(...sessions.map((s) => s.id)) + 1 : 1,
    title: title || `${subject || 'Séance'} - ${session_type || 'Cours'}`,
    subject: subject || 'Informatique',
    module_name: subject || 'Informatique',
    module_id: 1,
    classe: selectedClasse.id,
    classe_id: selectedClasse.id,
    classe_name: selectedClasse.name,
    classe_field: selectedClasse.filiere_name,
    filiere_name: selectedClasse.filiere_name,
    niveau: selectedClasse.level,
    niveau_label: selectedClasse.level,
    semestre_name: selectedClasse.semestre_name,
    teacher_id: 2,
    teacher: 'Karim Alami',
    teacher_name: 'Karim Alami',
    date: date || todayStr,
    start_time: start_time || liveWin1.start,
    end_time: end_time || liveWin1.end,
    room: typeof room === 'number' ? room : 1,
    room_id: typeof room === 'number' ? room : 1,
    room_name: 'Salle 101',
    block_name: 'Bloc A',
    amphitheater: null,
    amphitheater_name: null,
    session_type: session_type || 'tp',
    is_active: true,
    is_closed: false,
    qr_token: `QR-SESS-${Date.now()}`,
    qr_expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
    attendance_radius_meters: 50,
    attendance_count: 0,
    total_students: selectedClasse.student_count,
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
  } catch {
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
    room: session.room_name || session.amphitheater_name || 'Salle 102',
    requires_location: true,
  });
});

app.post('/api/v1/attendance/validate/', (req: Request, res: Response) => {
  const { qr_token, first_name, last_name, code_massar, device_id, device_fingerprint, latitude, longitude } = req.body;

  const session = sessions.find((s) => s.qr_token === qr_token || s.qr_token === 'SESSION-DEMO-QR-2026') || sessions[0];
  if (!session) {
    return res.status(400).json({ error: 'Séance invalide ou expirée.' });
  }

  const cleanMassar = (code_massar || '').trim().toUpperCase();
  const existing = attendances.find(
    (a) => a.session_id === session.id && (a.code_massar === cleanMassar || (device_id && a.device_id === device_id))
  );

  if (existing) {
    return res.status(400).json({
      error: 'Présence déjà enregistrée pour cet étudiant ou cet appareil dans cette séance.',
    });
  }

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

  const nowIso = new Date().toISOString();
  const newRecord = {
    id: attendances.length ? Math.max(...attendances.map((a) => a.id)) + 1 : 1,
    session_id: session.id,
    student_id: studentUser.id,
    student_name: `${studentUser.first_name} ${studentUser.last_name}`,
    student_massar: (studentUser as any).code_massar || cleanMassar,
    student_code_massar: (studentUser as any).code_massar || cleanMassar,
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
    validation_time: nowIso,
    created_at: nowIso,
    status: 'present',
    attendance_status: 'confirmed',
    device_id: device_id || `phone-${Date.now()}`,
    device_fingerprint: device_fingerprint || `fp-${Date.now().toString(16)}`,
    ip_address: req.ip || '127.0.0.1',
    is_suspicious: false,
    distance_meters: Math.floor(5 + Math.random() * 20),
    latitude: latitude || 33.8938,
    longitude: longitude || -5.5516,
  };

  attendances.unshift(newRecord);
  session.attendance_count = (session.attendance_count || 0) + 1;

  broadcastAttendance(newRecord, session.id);

  res.status(201).json({
    success: true,
    message: 'Présence enregistrée avec succès !',
    record: newRecord,
  });
});

app.get('/api/v1/attendance/session/:id/', (req: Request, res: Response) => {
  const sid = parseInt(req.params.id, 10);
  const rows = attendances.filter((a) => a.session_id === sid);
  res.json(rows);
});

app.get('/api/v1/attendance/session/:id/stats/', (req: Request, res: Response) => {
  const sid = parseInt(req.params.id, 10);
  const session = sessions.find((s) => s.id === sid) || sessions[0];
  const rows = attendances.filter((a) => a.session_id === sid);
  const total = session ? session.total_students || 4 : 4;
  res.json({
    attendance_count: rows.length,
    attendance_rate: total ? Math.round((rows.length / total) * 100) : 100,
    unique_devices: new Set(rows.map((r) => r.device_id)).size,
    duplicate_attempts: suspiciousAttempts.filter((x) => x.session_id === sid).length,
    geofence_violations: 0,
    locations: rows.map((r) => ({
      latitude: r.latitude,
      longitude: r.longitude,
      student_name: r.student_name,
      code_massar: r.code_massar,
    })),
  });
});

app.get('/api/v1/attendance/session/:id/suspicious/', (req: Request, res: Response) => {
  const sid = parseInt(req.params.id, 10);
  res.json(suspiciousAttempts.filter((x) => x.session_id === sid));
});

app.get('/api/v1/attendance/my-schedule/', (req: Request, res: Response) => {
  const { module_id } = req.query;
  let list = sessions.map((s) => ({
    ...s,
    status: s.id === 1 || s.id === 3 ? 'en_cours' : 'a_venir',
    qr_open: s.is_active,
  }));
  if (module_id) {
    list = list.filter((s) => s.module_id === parseInt(String(module_id), 10));
  }
  res.json(list);
});

app.get('/api/v1/attendance/my/', (req: Request, res: Response) => {
  const user = getRequestUser(req);
  const myRecords = attendances.filter((a) => a.student_id === user.id || user.role !== 'student');
  res.json(myRecords.length ? myRecords : attendances.slice(0, 2));
});

app.get('/api/v1/attendance/', (req: Request, res: Response) => {
  const { session_id, status } = req.query;
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
  record.attendance_status = record.status === 'present' ? 'confirmed' : 'absent';
  broadcastAttendance(record, record.session_id);
  res.json(record);
});

/* ─── Start Server ─────────────────────────────────────────────────────── */

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[PrésenceQR] Serveur en cours d'exécution sur http://0.0.0.0:${PORT}`);
});

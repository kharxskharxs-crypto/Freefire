// ===== ไฟล์ตั้งค่า Firebase (โปรเจกต์ใหม่) =====
// แก้เฉพาะข้อความในเครื่องหมายคำพูด โดยเอาค่าจริงจาก Firebase > Project settings > Your apps > Config
// ห้ามลบเครื่องหมาย " หรือ , ท้ายบรรทัด (บรรทัด appId ไม่มี , ท้ายบรรทัด)
export const firebaseConfig = {
  apiKey: "AIzaSyCrnWxLHaEA-dbz1AdN3SQwdFsqbkfGmsY",
  authDomain: "freefrie-831b0.firebaseapp.com",
  projectId: "freefrie-831b0",
  storageBucket: "freefrie-831b0.firebasestorage.app",
  messagingSenderId: "116245826333",
  appId: "1:116245826333:web:798ca05d6c6e285aabeff4"
};

// (ไม่บังคับ) ลิงก์ Google Apps Script สำหรับแจ้งเตือนเข้า Telegram ถ้ายังไม่ใช้ปล่อยว่างไว้
export const telegramRelayUrl = "";

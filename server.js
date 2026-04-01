import express from 'express';
import cors from 'cors';
import Database from 'better-sqlite3';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import crypto from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

const db = new Database(join(__dirname, 'ket-app.db'));

function initDB() {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      avatar_emoji TEXT DEFAULT '😊',
      xp INTEGER DEFAULT 0,
      streak INTEGER DEFAULT 0,
      last_login_date TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS vocab_progress (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      word_id INTEGER NOT NULL,
      rating TEXT CHECK(rating IN ('hard', 'ok', 'easy')),
      last_reviewed TEXT DEFAULT CURRENT_TIMESTAMP,
      review_count INTEGER DEFAULT 0,
      UNIQUE(user_id, word_id),
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS reading_progress (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      set_id INTEGER NOT NULL,
      score INTEGER NOT NULL,
      total INTEGER NOT NULL,
      completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS listening_progress (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      set_id INTEGER NOT NULL,
      score INTEGER NOT NULL,
      total INTEGER NOT NULL,
      completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS writing_progress (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      prompt_id INTEGER NOT NULL,
      word_count INTEGER NOT NULL,
      completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS learning_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      activity_type TEXT NOT NULL,
      xp_gain INTEGER DEFAULT 0,
      details TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);

  console.log('Database initialized');
}

initDB();

function hashPassword(password) {
  return crypto.createHash('sha256').update(password + 'ket_salt_2024').digest('hex');
}

function verifyPassword(password, hash) {
  return hashPassword(password) === hash;
}

// Register new user
app.post('/api/register', (req, res) => {
  try {
    const { username, email, password, avatarEmoji = '😊' } = req.body;

    if (!username || !email || !password) {
      return res.status(400).json({ error: '用户名、邮箱和密码不能为空' });
    }

    if (password.length < 6) {
      return res.status(400).json({ error: '密码至少6位' });
    }

    const existingUser = db.prepare('SELECT id FROM users WHERE email = ? OR username = ?').get(email, username);
    if (existingUser) {
      return res.status(400).json({ error: '用户名或邮箱已被注册' });
    }

    const hashedPassword = hashPassword(password);

    const stmt = db.prepare(`
      INSERT INTO users (username, email, password, avatar_emoji)
      VALUES (?, ?, ?, ?)
    `);
    const result = stmt.run(username, email, hashedPassword, avatarEmoji);

    res.status(201).json({
      success: true,
      user: {
        id: result.lastInsertRowid,
        username,
        email,
        avatarEmoji
      }
    });
  } catch (error) {
    console.error('Register error:', error);
    res.status(500).json({ error: '注册失败，请稍后重试' });
  }
});

// Login
app.post('/api/login', (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: '邮箱和密码不能为空' });
    }

    const user = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
    if (!user) {
      return res.status(401).json({ error: '邮箱或密码错误' });
    }

    const validPassword = verifyPassword(password, user.password);
    if (!validPassword) {
      return res.status(401).json({ error: '邮箱或密码错误' });
    }

    const today = new Date().toISOString().split('T')[0];
    const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];

    if (user.last_login_date === yesterday) {
      db.prepare('UPDATE users SET streak = streak + 1, last_login_date = ? WHERE id = ?').run(today, user.id);
    } else if (user.last_login_date !== today) {
      db.prepare('UPDATE users SET streak = 1, last_login_date = ? WHERE id = ?').run(today, user.id);
    }

    const updatedUser = db.prepare('SELECT * FROM users WHERE id = ?').get(user.id);

    res.json({
      success: true,
      user: {
        id: updatedUser.id,
        username: updatedUser.username,
        email: updatedUser.email,
        avatarEmoji: updatedUser.avatar_emoji,
        xp: updatedUser.xp,
        streak: updatedUser.streak
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: '登录失败，请稍后重试' });
  }
});

// Get user data
app.get('/api/user/:id', (req, res) => {
  try {
    const user = db.prepare('SELECT id, username, email, avatar_emoji, xp, streak, created_at FROM users WHERE id = ?').get(req.params.id);
    if (!user) {
      return res.status(404).json({ error: '用户不存在' });
    }
    res.json({ success: true, user });
  } catch (error) {
    console.error('Get user error:', error);
    res.status(500).json({ error: '获取用户信息失败' });
  }
});

// Get user progress summary
app.get('/api/user/:id/progress', (req, res) => {
  try {
    const userId = req.params.id;

    const vocabProgress = db.prepare(`
      SELECT COUNT(*) as total,
             SUM(CASE WHEN rating = 'easy' THEN 1 ELSE 0 END) as mastered
      FROM vocab_progress WHERE user_id = ?
    `).get(userId);

    const readingProgress = db.prepare(`
      SELECT COUNT(*) as total,
             AVG(score * 100.0 / total) as avg_score
      FROM reading_progress WHERE user_id = ?
    `).get(userId);

    const listeningProgress = db.prepare(`
      SELECT COUNT(*) as total,
             AVG(score * 100.0 / total) as avg_score
      FROM listening_progress WHERE user_id = ?
    `).get(userId);

    const writingProgress = db.prepare(`
      SELECT COUNT(*) as total
      FROM writing_progress WHERE user_id = ?
    `).get(userId);

    const recentActivity = db.prepare(`
      SELECT activity_type, xp_gain, details, created_at
      FROM learning_log
      WHERE user_id = ?
      ORDER BY created_at DESC
      LIMIT 10
    `).all(userId);

    res.json({
      success: true,
      progress: {
        vocab: vocabProgress,
        reading: readingProgress,
        listening: listeningProgress,
        writing: writingProgress,
        recentActivity
      }
    });
  } catch (error) {
    console.error('Get progress error:', error);
    res.status(500).json({ error: '获取进度失败' });
  }
});

// Save vocab progress
app.post('/api/vocab-progress', (req, res) => {
  try {
    const { userId, wordId, rating } = req.body;

    const existing = db.prepare('SELECT * FROM vocab_progress WHERE user_id = ? AND word_id = ?').get(userId, wordId);

    if (existing) {
      db.prepare(`
        UPDATE vocab_progress
        SET rating = ?, last_reviewed = CURRENT_TIMESTAMP, review_count = review_count + 1
        WHERE user_id = ? AND word_id = ?
      `).run(rating, userId, wordId);
    } else {
      db.prepare(`
        INSERT INTO vocab_progress (user_id, word_id, rating)
        VALUES (?, ?, ?)
      `).run(userId, wordId, rating);
    }

    const xpMap = { hard: 5, ok: 10, easy: 20 };
    const xpGain = xpMap[rating] || 10;
    db.prepare('UPDATE users SET xp = xp + ? WHERE id = ?').run(xpGain, userId);

    db.prepare(`
      INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
      VALUES (?, 'vocab', ?, ?)
    `).run(userId, xpGain, `Word ${wordId}: ${rating}`);

    res.json({ success: true, xpGain });
  } catch (error) {
    console.error('Save vocab progress error:', error);
    res.status(500).json({ error: '保存词汇进度失败' });
  }
});

// Save reading progress
app.post('/api/reading-progress', (req, res) => {
  try {
    const { userId, setId, score, total } = req.body;

    db.prepare(`
      INSERT INTO reading_progress (user_id, set_id, score, total)
      VALUES (?, ?, ?, ?)
    `).run(userId, setId, score, total);

    const xpGain = score === total ? 50 : score >= total * 0.6 ? 30 : 10;
    db.prepare('UPDATE users SET xp = xp + ? WHERE id = ?').run(xpGain, userId);

    db.prepare(`
      INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
      VALUES (?, 'reading', ?, ?)
    `).run(userId, xpGain, `Reading set ${setId}: ${score}/${total}`);

    res.json({ success: true, xpGain });
  } catch (error) {
    console.error('Save reading progress error:', error);
    res.status(500).json({ error: '保存阅读进度失败' });
  }
});

// Save listening progress
app.post('/api/listening-progress', (req, res) => {
  try {
    const { userId, setId, score, total } = req.body;

    db.prepare(`
      INSERT INTO listening_progress (user_id, set_id, score, total)
      VALUES (?, ?, ?, ?)
    `).run(userId, setId, score, total);

    const xpGain = score === total ? 40 : score >= total * 0.6 ? 25 : 10;
    db.prepare('UPDATE users SET xp = xp + ? WHERE id = ?').run(xpGain, userId);

    db.prepare(`
      INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
      VALUES (?, 'listening', ?, ?)
    `).run(userId, xpGain, `Listening set ${setId}: ${score}/${total}`);

    res.json({ success: true, xpGain });
  } catch (error) {
    console.error('Save listening progress error:', error);
    res.status(500).json({ error: '保存听力进度失败' });
  }
});

// Save writing progress
app.post('/api/writing-progress', (req, res) => {
  try {
    const { userId, promptId, wordCount, targetMin, targetMax } = req.body;

    db.prepare(`
      INSERT INTO writing_progress (user_id, prompt_id, word_count)
      VALUES (?, ?, ?)
    `).run(userId, promptId, wordCount);

    let xpGain = 30;
    if (wordCount >= targetMin && wordCount <= targetMax) {
      xpGain = 40;
    } else if (wordCount < targetMin) {
      xpGain = 20;
    }

    db.prepare('UPDATE users SET xp = xp + ? WHERE id = ?').run(xpGain, userId);

    db.prepare(`
      INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
      VALUES (?, 'writing', ?, ?)
    `).run(userId, xpGain, `Writing prompt ${promptId}: ${wordCount} words`);

    res.json({ success: true, xpGain });
  } catch (error) {
    console.error('Save writing progress error:', error);
    res.status(500).json({ error: '保存写作进度失败' });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});

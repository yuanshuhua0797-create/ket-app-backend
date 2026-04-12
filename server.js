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
  // 建立用户表
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

  // 建立词汇进度表 (将 word_id 改为 word TEXT)
  // 注意：生产环境建议使用 ALTER TABLE，这里为了开发方便直接检查并尝试迁移
  try {
    const tableInfo = db.prepare("PRAGMA table_info(vocab_progress)").all();
    if (tableInfo.length > 0 && !tableInfo.find(c => c.name === 'word')) {
      // 如果旧表存在且没有 word 列，则重建
      db.exec("DROP TABLE vocab_progress");
    }
  } catch (e) {}

  db.exec(`
    CREATE TABLE IF NOT EXISTS vocab_progress (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      word TEXT NOT NULL,
      rating TEXT CHECK(rating IN ('hard', 'medium', 'easy')),
      last_reviewed TEXT DEFAULT CURRENT_TIMESTAMP,
      review_count INTEGER DEFAULT 0,
      UNIQUE(user_id, word),
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

// Helper to get normalized user ID and other fields
function getParams(req) {
  const body = req.body || {};
  return {
    userId: body.userId || body.user_id,
    ...body
  };
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

// Get user progress summary (enhanced for frontend updateProgressUI)
app.get('/api/user/:id/progress', (req, res) => {
  try {
    const userId = req.params.id;
    const todayStart = new Date().toISOString().split('T')[0] + ' 00:00:00';

    // 1. 用户基础信息 (XP, Streak)
    const user = db.prepare('SELECT xp, streak FROM users WHERE id = ?').get(userId);
    if (!user) return res.status(404).json({ error: '用户不存在' });

    // 2. 今日统计
    const todayStats = db.prepare(`
      SELECT SUM(xp_gain) as xp, COUNT(*) as activities
      FROM learning_log
      WHERE user_id = ? AND created_at >= ?
    `).get(userId, todayStart);

    const todayWords = db.prepare(`
      SELECT COUNT(DISTINCT word) as count
      FROM vocab_progress
      WHERE user_id = ? AND last_reviewed >= ?
    `).get(userId, todayStart);

    // 3. 计算各个模块的掌握程度 (百分比)
    // 词汇 (假设总量大概 500 个常用词，或根据实际 word count)
    const vocabCount = db.prepare("SELECT COUNT(*) as count FROM vocab_progress WHERE user_id = ? AND rating = 'easy'").get(userId);
    const vocabPercent = Math.min(100, Math.round((vocabCount.count / 200) * 100)); // 以 200 个词作为初级目标

    // 阅读/听力/写作 (简单根据练习次数计算，满分 10 组)
    const readingDone = db.prepare("SELECT COUNT(DISTINCT set_id) as count FROM reading_progress WHERE user_id = ?").get(userId);
    const readingPercent = Math.min(100, readingDone.count * 10);

    const listeningDone = db.prepare("SELECT COUNT(DISTINCT set_id) as count FROM listening_progress WHERE user_id = ?").get(userId);
    const listeningPercent = Math.min(100, listeningDone.count * 10);

    const writingDone = db.prepare("SELECT COUNT(DISTINCT prompt_id) as count FROM writing_progress WHERE user_id = ?").get(userId);
    const writingPercent = Math.min(100, writingDone.count * 20);

    // 总体进度
    const overall = Math.round((vocabPercent + readingPercent + listeningPercent + writingPercent) / 4);

    // 今日正确率 (从阅读和听力记录中计算)
    const accuracyStats = db.prepare(`
      SELECT SUM(score) as correct, SUM(total) as total
      FROM (
        SELECT score, total FROM reading_progress WHERE user_id = ? AND completed_at >= ?
        UNION ALL
        SELECT score, total FROM listening_progress WHERE user_id = ? AND completed_at >= ?
      )
    `).get(userId, todayStart, userId, todayStart);
    const accuracy = accuracyStats.total > 0 ? (accuracyStats.correct / accuracyStats.total) * 100 : 0;

    // 4. 最近活动记录
    const recent = db.prepare(`
      SELECT activity_type as type, xp_gain as xp, details as text, created_at as time
      FROM learning_log
      WHERE user_id = ?
      ORDER BY created_at DESC
      LIMIT 10
    `).all(userId);

    res.json({
      success: true,
      today_words: todayWords.count || 0,
      today_xp: todayStats.xp || 0,
      accuracy: accuracy,
      streak: user.streak,
      overall: overall,
      skills: {
        vocab: vocabPercent,
        reading: readingPercent,
        listening: listeningPercent,
        writing: writingPercent
      },
      recent: recent.map(r => ({
        ...r,
        time: new Date(r.time).toLocaleString('zh-CN', { hour12: false }).substring(5, 16)
      }))
    });
  } catch (error) {
    console.error('Get progress error:', error);
    res.status(500).json({ error: '获取进度失败' });
  }
});

// Save vocab progress
app.post('/api/vocab-progress', (req, res) => {
  try {
    const { userId, word, rating } = getParams(req);

    if (!userId || !word || !rating) {
      return res.status(400).json({ error: '缺失必要字段 (userId, word, rating)' });
    }

    const existing = db.prepare('SELECT * FROM vocab_progress WHERE user_id = ? AND word = ?').get(userId, word);

    if (existing) {
      db.prepare(`
        UPDATE vocab_progress
        SET rating = ?, last_reviewed = CURRENT_TIMESTAMP, review_count = review_count + 1
        WHERE user_id = ? AND word = ?
      `).run(rating, userId, word);
    } else {
      db.prepare(`
        INSERT INTO vocab_progress (user_id, word, rating)
        VALUES (?, ?, ?)
      `).run(userId, word, rating);
    }

    const xpMap = { hard: 5, medium: 10, easy: 20 };
    const xpGain = xpMap[rating] || 10;
    db.prepare('UPDATE users SET xp = xp + ? WHERE id = ?').run(xpGain, userId);

    db.prepare(`
      INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
      VALUES (?, 'vocab', ?, ?)
    `).run(userId, xpGain, `词汇学习: ${word} (${rating})`);

    res.json({ success: true, xpGain });
  } catch (error) {
    console.error('Save vocab progress error:', error);
    res.status(500).json({ error: '保存词汇进度失败' });
  }
});

// Save reading progress
app.post('/api/reading-progress', (req, res) => {
  try {
    const { userId, setId, score, total } = getParams(req);

    if (userId === undefined || setId === undefined || score === undefined) {
      return res.status(400).json({ error: '缺失必要字段 (userId, setId, score)' });
    }

    db.prepare(`
      INSERT INTO reading_progress (user_id, set_id, score, total)
      VALUES (?, ?, ?, ?)
    `).run(userId, setId, score, total || 1);

    const xpGain = score > 0 ? (score === total ? 50 : 20) : 5;
    db.prepare('UPDATE users SET xp = xp + ? WHERE id = ?').run(xpGain, userId);

    db.prepare(`
      INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
      VALUES (?, 'reading', ?, ?)
    `).run(userId, xpGain, `阅读练习 Set ${setId+1}: 得分 ${score}/${total}`);

    res.json({ success: true, xpGain });
  } catch (error) {
    console.error('Save reading progress error:', error);
    res.status(500).json({ error: '保存阅读进度失败' });
  }
});

// Save listening progress
app.post('/api/listening-progress', (req, res) => {
  try {
    const { userId, setId, score, total } = getParams(req);

    if (userId === undefined || setId === undefined || score === undefined) {
      return res.status(400).json({ error: '缺失必要字段 (userId, setId, score)' });
    }

    db.prepare(`
      INSERT INTO listening_progress (user_id, set_id, score, total)
      VALUES (?, ?, ?, ?)
    `).run(userId, setId, score, total || 1);

    const xpGain = score > 0 ? (score === total ? 40 : 20) : 5;
    db.prepare('UPDATE users SET xp = xp + ? WHERE id = ?').run(xpGain, userId);

    db.prepare(`
      INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
      VALUES (?, 'listening', ?, ?)
    `).run(userId, xpGain, `听力练习 Set ${setId+1}: 得分 ${score}/${total}`);

    res.json({ success: true, xpGain });
  } catch (error) {
    console.error('Save listening progress error:', error);
    res.status(500).json({ error: '保存听力进度失败' });
  }
});

// Save writing progress
app.post('/api/writing-progress', (req, res) => {
  try {
    const { userId, promptId, wordCount, targetMin = 20, targetMax = 40 } = getParams(req);

    if (userId === undefined || promptId === undefined) {
      return res.status(400).json({ error: '缺失必要字段 (userId, promptId)' });
    }

    db.prepare(`
      INSERT INTO writing_progress (user_id, prompt_id, word_count)
      VALUES (?, ?, ?)
    `).run(userId, promptId, wordCount);

    let xpGain = 15;
    if (wordCount >= targetMin && wordCount <= targetMax) {
      xpGain = 30;
    }

    db.prepare('UPDATE users SET xp = xp + ? WHERE id = ?').run(xpGain, userId);

    db.prepare(`
      INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
      VALUES (?, 'writing', ?, ?)
    `).run(userId, xpGain, `写作练习 Prompt ${promptId+1}: ${wordCount} 词`);

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

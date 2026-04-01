from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import hashlib
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), 'ket-app.db')

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
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
    ''')
    
    c.execute('''
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
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS reading_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            set_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS listening_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            set_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS writing_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt_id INTEGER NOT NULL,
            word_count INTEGER NOT NULL,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS learning_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            xp_gain INTEGER DEFAULT 0,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print('Database initialized')

def hash_password(password):
    """Hash password"""
    return hashlib.sha256((password + 'ket_salt_2024').encode()).hexdigest()

def verify_password(password, hash_val):
    """Verify password"""
    return hash_password(password) == hash_val

# API Routes

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        avatar_emoji = data.get('avatarEmoji', '😊')
        
        if not username or not email or not password:
            return jsonify({'error': '用户名、邮箱和密码不能为空'}), 400
        
        if len(password) < 6:
            return jsonify({'error': '密码至少6位'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT id FROM users WHERE email = ? OR username = ?', (email, username))
        if c.fetchone():
            return jsonify({'error': '用户名或邮箱已被注册'}), 400
        
        hashed_password = hash_password(password)
        c.execute(
            'INSERT INTO users (username, email, password, avatar_emoji) VALUES (?, ?, ?, ?)',
            (username, email, hashed_password, avatar_emoji)
        )
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'username': username,
                'email': email,
                'avatarEmoji': avatar_emoji
            }
        }), 201
    
    except Exception as e:
        print(f'Register error: {e}')
        return jsonify({'error': '注册失败，请稍后重试'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': '邮箱和密码不能为空'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        
        if not user:
            return jsonify({'error': '邮箱或密码错误'}), 401
        
        if not verify_password(password, user['password']):
            return jsonify({'error': '邮箱或密码错误'}), 401
        
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        if user['last_login_date'] == yesterday:
            c.execute('UPDATE users SET streak = streak + 1, last_login_date = ? WHERE id = ?', (today, user['id']))
        elif user['last_login_date'] != today:
            c.execute('UPDATE users SET streak = 1, last_login_date = ? WHERE id = ?', (today, user['id']))
        
        conn.commit()
        
        c.execute('SELECT * FROM users WHERE id = ?', (user['id'],))
        updated_user = c.fetchone()
        conn.close()
        
        return jsonify({
            'success': True,
            'user': {
                'id': updated_user['id'],
                'username': updated_user['username'],
                'email': updated_user['email'],
                'avatarEmoji': updated_user['avatar_emoji'],
                'xp': updated_user['xp'],
                'streak': updated_user['streak']
            }
        })
    
    except Exception as e:
        print(f'Login error: {e}')
        return jsonify({'error': '登录失败，请稍后重试'}), 500

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT id, username, email, avatar_emoji, xp, streak, created_at FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        return jsonify({
            'success': True,
            'user': dict(user)
        })
    
    except Exception as e:
        print(f'Get user error: {e}')
        return jsonify({'error': '获取用户信息失败'}), 500

@app.route('/api/user/<int:user_id>/progress', methods=['GET'])
def get_progress(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN rating = 'easy' THEN 1 ELSE 0 END) as mastered
            FROM vocab_progress WHERE user_id = ?
        ''', (user_id,))
        vocab_progress = dict(c.fetchone())
        
        c.execute('''
            SELECT COUNT(*) as total,
                   AVG(score * 100.0 / total) as avg_score
            FROM reading_progress WHERE user_id = ?
        ''', (user_id,))
        reading_progress = dict(c.fetchone())
        
        c.execute('''
            SELECT COUNT(*) as total,
                   AVG(score * 100.0 / total) as avg_score
            FROM listening_progress WHERE user_id = ?
        ''', (user_id,))
        listening_progress = dict(c.fetchone())
        
        c.execute('''
            SELECT COUNT(*) as total
            FROM writing_progress WHERE user_id = ?
        ''', (user_id,))
        writing_progress = dict(c.fetchone())
        
        c.execute('''
            SELECT activity_type, xp_gain, details, created_at
            FROM learning_log
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (user_id,))
        recent_activity = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'progress': {
                'vocab': vocab_progress,
                'reading': reading_progress,
                'listening': listening_progress,
                'writing': writing_progress,
                'recentActivity': recent_activity
            }
        })
    
    except Exception as e:
        print(f'Get progress error: {e}')
        return jsonify({'error': '获取进度失败'}), 500

@app.route('/api/vocab-progress', methods=['POST'])
def save_vocab_progress():
    try:
        data = request.json
        user_id = data.get('userId')
        word_id = data.get('wordId')
        rating = data.get('rating')
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT * FROM vocab_progress WHERE user_id = ? AND word_id = ?', (user_id, word_id))
        existing = c.fetchone()
        
        if existing:
            c.execute('''
                UPDATE vocab_progress
                SET rating = ?, last_reviewed = CURRENT_TIMESTAMP, review_count = review_count + 1
                WHERE user_id = ? AND word_id = ?
            ''', (rating, user_id, word_id))
        else:
            c.execute('''
                INSERT INTO vocab_progress (user_id, word_id, rating)
                VALUES (?, ?, ?)
            ''', (user_id, word_id, rating))
        
        xp_map = {'hard': 5, 'ok': 10, 'easy': 20}
        xp_gain = xp_map.get(rating, 10)
        
        c.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (xp_gain, user_id))
        
        c.execute('''
            INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
            VALUES (?, 'vocab', ?, ?)
        ''', (user_id, xp_gain, f'Word {word_id}: {rating}'))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'xpGain': xp_gain})
    
    except Exception as e:
        print(f'Save vocab progress error: {e}')
        return jsonify({'error': '保存词汇进度失败'}), 500

@app.route('/api/reading-progress', methods=['POST'])
def save_reading_progress():
    try:
        data = request.json
        user_id = data.get('userId')
        set_id = data.get('setId')
        score = data.get('score')
        total = data.get('total')
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO reading_progress (user_id, set_id, score, total)
            VALUES (?, ?, ?, ?)
        ''', (user_id, set_id, score, total))
        
        xp_gain = 50 if score == total else 30 if score >= total * 0.6 else 10
        c.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (xp_gain, user_id))
        
        c.execute('''
            INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
            VALUES (?, 'reading', ?, ?)
        ''', (user_id, xp_gain, f'Reading set {set_id}: {score}/{total}'))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'xpGain': xp_gain})
    
    except Exception as e:
        print(f'Save reading progress error: {e}')
        return jsonify({'error': '保存阅读进度失败'}), 500

@app.route('/api/listening-progress', methods=['POST'])
def save_listening_progress():
    try:
        data = request.json
        user_id = data.get('userId')
        set_id = data.get('setId')
        score = data.get('score')
        total = data.get('total')
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO listening_progress (user_id, set_id, score, total)
            VALUES (?, ?, ?, ?)
        ''', (user_id, set_id, score, total))
        
        xp_gain = 40 if score == total else 25 if score >= total * 0.6 else 10
        c.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (xp_gain, user_id))
        
        c.execute('''
            INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
            VALUES (?, 'listening', ?, ?)
        ''', (user_id, xp_gain, f'Listening set {set_id}: {score}/{total}'))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'xpGain': xp_gain})
    
    except Exception as e:
        print(f'Save listening progress error: {e}')
        return jsonify({'error': '保存听力进度失败'}), 500

@app.route('/api/writing-progress', methods=['POST'])
def save_writing_progress():
    try:
        data = request.json
        user_id = data.get('userId')
        prompt_id = data.get('promptId')
        word_count = data.get('wordCount')
        target_min = data.get('targetMin')
        target_max = data.get('targetMax')
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO writing_progress (user_id, prompt_id, word_count)
            VALUES (?, ?, ?)
        ''', (user_id, prompt_id, word_count))
        
        xp_gain = 30
        if target_min <= word_count <= target_max:
            xp_gain = 40
        elif word_count < target_min:
            xp_gain = 20
        
        c.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (xp_gain, user_id))
        
        c.execute('''
            INSERT INTO learning_log (user_id, activity_type, xp_gain, details)
            VALUES (?, 'writing', ?, ?)
        ''', (user_id, xp_gain, f'Writing prompt {prompt_id}: {word_count} words'))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'xpGain': xp_gain})
    
    except Exception as e:
        print(f'Save writing progress error: {e}')
        return jsonify({'error': '保存写作进度失败'}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=3001)

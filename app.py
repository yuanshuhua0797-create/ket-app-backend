from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import hashlib
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Admin password
ADMIN_PASSWORD = "ket-admin-2026"

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

    # Learning content tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS vocab_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            phonetic TEXT,
            translation TEXT NOT NULL,
            example TEXT,
            category TEXT DEFAULT '日常',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS reading_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part TEXT NOT NULL,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            answer INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS writing_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            prompt TEXT NOT NULL,
            word_min INTEGER DEFAULT 25,
            word_max INTEGER DEFAULT 40,
            tips TEXT,
            reference TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS listening_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialogue TEXT NOT NULL,
            audio_file TEXT,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            answer INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # User tables
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

    # Seed initial data if empty
    c.execute('SELECT COUNT(*) FROM vocab_items')
    if c.fetchone()[0] == 0:
        seed_initial_data(c)

    conn.commit()
    conn.close()
    print('Database initialized')

def seed_initial_data(c):
    """Seed initial learning data"""
    # Vocab - 200 items across 8 categories
    vocab_data = [
        # 日常生活 (40)
        ("morning", "/ˈmɔːnɪŋ/", "早晨", "I have breakfast every morning.", "日常"),
        ("evening", "/ˈiːvnɪŋ/", "傍晚", "The evening sky is beautiful.", "日常"),
        ("tonight", "/təˈnaɪt/", "今晚", "What are you doing tonight?", "日常"),
        ("yesterday", "/ˈjestədeɪ/", "昨天", "Yesterday was a sunny day.", "日常"),
        ("today", "/təˈdeɪ/", "今天", "Today is Monday.", "日常"),
        ("tomorrow", "/təˈmɒrəʊ/", "明天", "Tomorrow is my birthday.", "日常"),
        ("breakfast", "/ˈbrekfəst/", "早餐", "I eat breakfast at 7am.", "日常"),
        ("lunch", "/lʌntʃ/", "午餐", "Let's have lunch together.", "日常"),
        ("dinner", "/ˈdɪnə/", "晚餐", "We have dinner at 6pm.", "日常"),
        ("water", "/ˈwɔːtə/", "水", "Please drink more water.", "日常"),
        ("coffee", "/ˈkɒfi/", "咖啡", "I drink coffee every morning.", "日常"),
        ("tea", "/tiː/", "茶", "Would you like some tea?", "日常"),
        ("milk", "/mɪlk/", "牛奶", "Children need to drink milk.", "日常"),
        ("home", "/həʊm/", "家", "I'm going home now.", "日常"),
        ("house", "/haʊs/", "房子", "This is a beautiful house.", "日常"),
        ("room", "/ruːm/", "房间", "My room is on the second floor.", "日常"),
        ("bed", "/bed/", "床", "I go to bed at 10pm.", "日常"),
        ("sleep", "/sliːp/", "睡觉", "I sleep 8 hours every night.", "日常"),
        ("wake up", "/weɪk ʌp/", "醒来", "I wake up at 6am.", "日常"),
        ("walk", "/wɔːk/", "走路", "I walk to school every day.", "日常"),
        ("run", "/rʌn/", "跑步", "He runs in the park every morning.", "日常"),
        ("sit", "/sɪt/", "坐下", "Please sit here.", "日常"),
        ("stand", "/stænd/", "站立", "Don't stand in the rain.", "日常"),
        ("open", "/ˈəʊpən/", "打开", "Open the window please.", "日常"),
        ("close", "/kləʊz/", "关闭", "Close the door.", "日常"),
        ("read", "/riːd/", "阅读", "I like to read books.", "日常"),
        ("write", "/raɪt/", "写", "Please write your name.", "日常"),
        ("speak", "/spiːk/", "说话", "Can you speak English?", "日常"),
        ("listen", "/ˈlɪsən/", "听", "Listen to the music.", "日常"),
        ("look", "/lʊk/", "看", "Look at the blackboard.", "日常"),
        ("see", "/siː/", "看见", "I can see the mountains.", "日常"),
        ("watch", "/wɒtʃ/", "观看", "I watch TV in the evening.", "日常"),
        ("clean", "/kliːn/", "打扫", "I clean my room on weekends.", "日常"),
        ("wash", "/wɒʃ/", "洗", "Wash your hands before eating.", "日常"),
        ("cook", "/kʊk/", "做饭", "My mother cooks dinner.", "日常"),
        ("eat", "/iːt/", "吃", "We eat rice every day.", "日常"),
        ("drink", "/drɪŋk/", "喝", "What do you want to drink?", "日常"),
        ("walk", "/wɔːk/", "散步", "Let's take a walk after dinner.", "日常"),
        ("rest", "/rest/", "休息", "I need to rest for a while.", "日常"),
        # 学校 (25)
        ("school", "/skuːl/", "学校", "I go to school every day.", "学校"),
        ("teacher", "/ˈtiːtʃə/", "老师", "My teacher is very kind.", "学校"),
        ("student", "/ˈstjuːdənt/", "学生", "There are 30 students in my class.", "学校"),
        ("class", "/klɑːs/", "班级", "We are in the same class.", "学校"),
        ("lesson", "/ˈlesən/", "课程", "The English lesson starts at 9am.", "学校"),
        ("book", "/bʊk/", "书", "This is my favorite book.", "学校"),
        ("pen", "/pen/", "钢笔", "Please give me a pen.", "学校"),
        ("pencil", "/ˈpensəl/", "铅笔", "I write with a pencil.", "学校"),
        ("paper", "/ˈpeɪpə/", "纸", "Write your answer on paper.", "学校"),
        ("desk", "/desk/", "桌子", "The desk is near the window.", "学校"),
        ("chair", "/tʃeə/", "椅子", "Sit on the chair.", "学校"),
        ("blackboard", "/ˈblækbɔːd/", "黑板", "The teacher writes on the blackboard.", "学校"),
        ("homework", "/ˈhəʊmwɜːk/", "作业", "I finish my homework at 8pm.", "学校"),
        ("test", "/test/", "测试", "We have a math test tomorrow.", "学校"),
        ("exam", "/ɪɡˈzæm/", "考试", "The exam is next week.", "学校"),
        ("study", "/ˈstʌdi/", "学习", "I study English every day.", "学校"),
        ("learn", "/lɜːn/", "学习", "I learn new words every day.", "学校"),
        ("read", "/riːd/", "读", "I read English books.", "学校"),
        ("spell", "/spel/", "拼写", "Can you spell your name?", "学校"),
        ("answer", "/ˈɑːnsə/", "回答", "Please answer the question.", "学校"),
        ("question", "/ˈkwestʃən/", "问题", "I have a question.", "学校"),
        ("library", "/ˈlaɪbrəri/", "图书馆", "I go to the library to read.", "学校"),
        ("friend", "/frend/", "朋友", "My best friend is in my class.", "学校"),
        ("play", "/pleɪ/", "玩", "We play games at recess.", "学校"),
        ("time", "/taɪm/", "时间", "What time is it?", "学校"),
        # 旅行 (25)
        ("travel", "/ˈtrævəl/", "旅行", "I want to travel around Europe.", "旅行"),
        ("trip", "/trɪp/", "旅程", "We had a great trip.", "旅行"),
        ("tour", "/tʊə/", "旅游", "We took a tour of the city.", "旅行"),
        ("visit", "/ˈvɪzɪt/", "参观", "I want to visit Japan.", "旅行"),
        ("map", "/mæp/", "地图", "Can you show me on the map?", "旅行"),
        ("ticket", "/ˈtɪkɪt/", "票", "I bought a train ticket.", "旅行"),
        ("passport", "/ˈpɑːspɔːt/", "护照", "Don't forget your passport.", "旅行"),
        ("hotel", "/həʊˈtel/", "酒店", "The hotel is near the beach.", "旅行"),
        ("airport", "/ˈeəpɔːt/", "机场", "Meet me at the airport.", "旅行"),
        ("plane", "/pleɪn/", "飞机", "The plane takes off at 9am.", "旅行"),
        ("train", "/treɪn/", "火车", "We traveled by train.", "旅行"),
        ("bus", "/bʌs/", "公共汽车", "Take the bus to school.", "旅行"),
        ("taxi", "/ˈtæksi/", "出租车", "Let's take a taxi.", "旅行"),
        ("car", "/kɑː/", "汽车", "We drove by car.", "旅行"),
        ("ship", "/ʃɪp/", "船", "The ship arrived at the port.", "旅行"),
        ("beach", "/biːtʃ/", "海滩", "We played on the beach.", "旅行"),
        ("mountain", "/ˈmaʊntɪn/", "山", "The mountain is very high.", "旅行"),
        ("island", "/ˈaɪlənd/", "岛屿", "We visited a beautiful island.", "旅行"),
        ("camera", "/ˈkæmərə/", "相机", "I took many photos with my camera.", "旅行"),
        ("bag", "/bæɡ/", "包", "This is my travel bag.", "旅行"),
        ("suitcase", "/ˈsuːtkeɪs/", "行李箱", "My suitcase is very heavy.", "旅行"),
        ("guide", "/ɡaɪd/", "导游", "The guide spoke good English.", "旅行"),
        ("museum", "/mjuˈziːəm/", "博物馆", "We visited the museum.", "旅行"),
        ("photo", "/ˈfəʊtəʊ/", "照片", "May I take a photo?", "旅行"),
        ("weather", "/ˈweðə/", "天气", "What's the weather like today?", "旅行"),
        # 食物 (25)
        ("food", "/fuːd/", "食物", "I love Chinese food.", "食物"),
        ("rice", "/raɪs/", "米饭", "We eat rice every day.", "食物"),
        ("bread", "/bred/", "面包", "I have bread for breakfast.", "食物"),
        ("noodle", "/ˈnuːdl/", "面条", "I like chicken noodles.", "食物"),
        ("soup", "/suːp/", "汤", "This soup is delicious.", "食物"),
        ("meat", "/miːt/", "肉", "I prefer chicken meat.", "食物"),
        ("chicken", "/ˈtʃɪkɪn/", "鸡肉", "Grilled chicken is tasty.", "食物"),
        ("beef", "/biːf/", "牛肉", "I had beef for lunch.", "食物"),
        ("fish", "/fɪʃ/", "鱼", "Do you like fish?", "食物"),
        ("vegetable", "/ˈvedʒtəbəl/", "蔬菜", "Eat more vegetables.", "食物"),
        ("fruit", "/fruːt/", "水果", "An apple is a fruit.", "食物"),
        ("apple", "/ˈæpəl/", "苹果", "I ate an apple.", "食物"),
        ("banana", "/bəˈnɑːnə/", "香蕉", "Bananas are yellow.", "食物"),
        ("orange", "/ˈɒrɪndʒ/", "橙子", "I drink orange juice.", "食物"),
        ("egg", "/eɡ/", "鸡蛋", "I want two eggs.", "食物"),
        ("salt", "/sɔːlt/", "盐", "Add some salt.", "食物"),
        ("sugar", "/ˈʃʊɡə/", "糖", "Too much sugar is not good.", "食物"),
        ("taste", "/teɪst/", "味道", "The food tastes great.", "食物"),
        ("delicious", "/dɪˈlɪʃəs/", "美味的", "This dish is delicious.", "食物"),
        ("sweet", "/swiːt/", "甜的", "I like sweet food.", "食物"),
        ("salty", "/ˈsɔːlti/", "咸的", "This soup is too salty.", "食物"),
        ("hungry", "/ˈhʌŋɡri/", "饿的", "I'm very hungry.", "食物"),
        ("thirsty", "/ˈθɜːsti/", "渴的", "I'm thirsty. I need water.", "食物"),
        ("full", "/fʊl/", "饱的", "I'm full. Thank you.", "食物"),
        ("restaurant", "/ˈrestrɒnt/", "餐厅", "We ate at a restaurant.", "食物"),
        # 身体 (20)
        ("head", "/hed/", "头", "My head hurts.", "身体"),
        ("eye", "/aɪ/", "眼睛", "She has blue eyes.", "身体"),
        ("ear", "/ɪə/", "耳朵", "I can't hear with my left ear.", "身体"),
        ("nose", "/nəʊz/", "鼻子", "My nose is red.", "身体"),
        ("mouth", "/maʊθ/", "嘴巴", "Open your mouth.", "身体"),
        ("tooth", "/tuːθ/", "牙齿", "I brush my teeth twice a day.", "身体"),
        ("face", "/feɪs/", "脸", "Her face is pretty.", "身体"),
        ("hand", "/hænd/", "手", "Raise your hand.", "身体"),
        ("arm", "/ɑːm/", "手臂", "I hurt my arm.", "身体"),
        ("leg", "/leɡ/", "腿", "I broke my leg.", "身体"),
        ("foot", "/fʊt/", "脚", "I kicked the ball with my foot.", "身体"),
        ("body", "/ˈbɒdi/", "身体", "Exercise is good for your body.", "身体"),
        ("hair", "/heə/", "头发", "She has long hair.", "身体"),
        ("skin", "/skɪn/", "皮肤", "His skin is fair.", "身体"),
        ("health", "/helθ/", "健康", "Health is important.", "身体"),
        ("sick", "/sɪk/", "生病的", "I'm feeling sick.", "身体"),
        ("pain", "/peɪn/", "疼痛", "I have a pain in my back.", "身体"),
        ("doctor", "/ˈdɒktə/", "医生", "I need to see a doctor.", "身体"),
        ("medicine", "/ˈmedɪsɪn/", "药", "Take this medicine three times a day.", "身体"),
        ("hospital", "/ˈhɒspɪtəl/", "医院", "The hospital is near here.", "身体"),
        # 购物 (25)
        ("shop", "/ʃɒp/", "商店", "Let's go to the shop.", "购物"),
        ("store", "/stɔː/", "店铺", "The store opens at 9am.", "购物"),
        ("buy", "/baɪ/", "买", "I want to buy a new phone.", "购物"),
        ("sell", "/sel/", "卖", "This shop sells books.", "购物"),
        ("price", "/praɪs/", "价格", "What's the price?", "购物"),
        ("cheap", "/tʃiːp/", "便宜的", "This is very cheap.", "购物"),
        ("expensive", "/ɪkˈspensɪv/", "贵的", "That's too expensive.", "购物"),
        ("money", "/ˈmʌni/", "钱", "I don't have enough money.", "购物"),
        ("pay", "/peɪ/", "支付", "I'll pay by card.", "购物"),
        ("cost", "/kɒst/", "花费", "How much does it cost?", "购物"),
        ("size", "/saɪz/", "尺寸", "What size do you wear?", "购物"),
        ("color", "/ˈkʌlə/", "颜色", "I like the blue color.", "购物"),
        ("red", "/red/", "红色", "I want the red one.", "购物"),
        ("blue", "/bluː/", "蓝色", "The sky is blue.", "购物"),
        ("green", "/ɡriːn/", "绿色", "I like green tea.", "购物"),
        ("black", "/blæk/", "黑色", "I have a black bag.", "购物"),
        ("white", "/waɪt/", "白色", "The walls are white.", "购物"),
        ("small", "/smɔːl/", "小的", "This is too small for me.", "购物"),
        ("big", "/bɪɡ/", "大的", "I need a bigger size.", "购物"),
        ("new", "/njuː/", "新的", "I bought a new dress.", "购物"),
        ("old", "/əʊld/", "旧的", "This is an old building.", "购物"),
        ("nice", "/naɪs/", "好的", "That's a very nice shirt.", "购物"),
        ("try", "/traɪ/", "试穿", "Can I try it on?", "购物"),
        ("clothes", "/kləʊðz/", "衣服", "I need new clothes.", "购物"),
        ("shoes", "/ʃuːz/", "鞋子", "I like these shoes.", "购物"),
        # 职业 (25)
        ("doctor", "/ˈdɒktə/", "医生", "My mother is a doctor.", "职业"),
        ("nurse", "/nɜːs/", "护士", "The nurse is very kind.", "职业"),
        ("teacher", "/ˈtiːtʃə/", "教师", "He is a math teacher.", "职业"),
        ("student", "/ˈstjuːdənt/", "学生", "She is a university student.", "职业"),
        ("engineer", "/ˌendʒɪˈnɪə/", "工程师", "My father is an engineer.", "职业"),
        ("driver", "/ˈdraɪvə/", "司机", "The bus driver is friendly.", "职业"),
        ("cook", "/kʊk/", "厨师", "The cook made delicious food.", "职业"),
        ("worker", "/ˈwɜːkə/", "工人", "The factory worker is busy.", "职业"),
        ("farmer", "/ˈfɑːmə/", "农民", "The farmer grows vegetables.", "职业"),
        ("police", "/pəˈliːs/", "警察", "Call the police!", "职业"),
        ("soldier", "/ˈsəʊldʒə/", "士兵", "His brother is a soldier.", "职业"),
        ("artist", "/ˈɑːtɪst/", "艺术家", "She is a talented artist.", "职业"),
        ("musician", "/mjuˈzɪʃən/", "音乐家", "He wants to be a musician.", "职业"),
        ("writer", "/ˈraɪtə/", "作家", "She is a famous writer.", "职业"),
        ("singer", "/ˈsɪŋə/", "歌手", "The singer has a beautiful voice.", "职业"),
        ("actor", "/ˈæktə/", "演员", "He is a popular actor.", "职业"),
        ("manager", "/ˈmænɪdʒə/", "经理", "The manager is in a meeting.", "职业"),
        ("secretary", "/ˈsekrətəri/", "秘书", "His secretary is very efficient.", "职业"),
        ("businessman", "/ˈbɪznəsmæn/", "商人", "He is a successful businessman.", "职业"),
        ("waiter", "/ˈweɪtə/", "服务员", "The waiter brought the menu.", "职业"),
        ("shopkeeper", "/ˈʃɒpkiːpə/", "店主", "The shopkeeper is very honest.", "职业"),
        ("pilot", "/ˈpaɪlət/", "飞行员", "The pilot is very experienced.", "职业"),
        ("fireman", "/ˈfaɪəmən/", "消防员", "The fireman saved the child.", "职业"),
        ("postman", "/ˈpəʊstmən/", "邮递员", "The postman comes at 8am.", "职业"),
        ("job", "/dʒɒb/", "工作", "I found a part-time job.", "职业"),
        # 家庭 (20)
        ("family", "/ˈfæməli/", "家庭", "My family has five people.", "家庭"),
        ("father", "/ˈfɑːðə/", "父亲", "My father is 40 years old.", "家庭"),
        ("mother", "/ˈmʌðə/", "母亲", "My mother cooks very well.", "家庭"),
        ("parent", "/ˈpeərənt/", "父母", "My parents are very kind.", "家庭"),
        ("brother", "/ˈbrʌðə/", "兄弟", "I have an older brother.", "家庭"),
        ("sister", "/ˈsɪstə/", "姐妹", "My sister is a student.", "家庭"),
        ("son", "/sʌn/", "儿子", "Their son is very clever.", "家庭"),
        ("daughter", "/ˈdɔːtə/", "女儿", "Their daughter is 10 years old.", "家庭"),
        ("grandfather", "/ˈɡrænfɑːðə/", "祖父", "My grandfather is 70.", "家庭"),
        ("grandmother", "/ˈɡrænmʌðə/", "祖母", "My grandmother tells great stories.", "家庭"),
        ("grandparent", "/ˈɡrænpeərənt/", "祖父母", "I visit my grandparents on weekends.", "家庭"),
        ("uncle", "/ˈʌŋkəl/", "叔叔", "My uncle lives in Beijing.", "家庭"),
        ("aunt", "/ɑːnt/", "阿姨", "My aunt is a teacher.", "家庭"),
        ("cousin", "/ˈkʌzən/", "表兄妹", "My cousin is my age.", "家庭"),
        ("baby", "/ˈbeɪbi/", "婴儿", "The baby is sleeping.", "家庭"),
        ("child", "/tʃaɪld/", "孩子", "They have three children.", "家庭"),
        ("children", "/ˈtʃɪldrən/", "孩子们", "The children are playing outside.", "家庭"),
        ("husband", "/ˈhʌzbənd/", "丈夫", "Her husband is a doctor.", "家庭"),
        ("wife", "/waɪf/", "妻子", "His wife is very beautiful.", "家庭"),
        ("marriage", "/ˈmærɪdʒ/", "婚姻", "Marriage is important.", "家庭"),
    ]

    for item in vocab_data:
        c.execute(
            'INSERT INTO vocab_items (word, phonetic, translation, example, category) VALUES (?, ?, ?, ?, ?)',
            item
        )

    # Reading items - 20 passages
    reading_data = [
        {"part": "Part 1", "title": "图书馆告示", "text": "NOTICE\n\nAll students must be quiet in the library.\nNo food or drinks allowed.\nBooks must be returned within 2 weeks.\nLate fees: 1 yuan per day.\n\nLibrary Hours:\nMonday-Friday: 8:00 AM - 9:00 PM\nSaturday-Sunday: 9:00 AM - 5:00 PM", "question": "When must books be returned?", "options": ["Within 1 week", "Within 2 weeks", "Within 3 weeks", "Any time"], "answer": 1},
        {"part": "Part 1", "title": "餐厅菜单", "text": "MENU\n\nBreakfast: 7:00 - 10:00\nLunch: 11:30 - 14:00\nDinner: 18:00 - 21:00\n\nSpecial: Kids eat free on Sundays!\n\nCall: 555-1234 for reservations", "question": "When can you get lunch?", "options": ["7:00 - 10:00", "11:30 - 14:00", "18:00 - 21:00", "All day"], "answer": 1},
        {"part": "Part 1", "title": "电影院公告", "text": "CINEMA RULES\n\n1. No running in the cinema\n2. Turn off your phone\n3. No flash photography\n4. Be quiet during the film\n\nTickets: Available at counter or online\nPrice: Adults 80 yuan, Students 50 yuan", "question": "How much is a student ticket?", "options": ["40 yuan", "50 yuan", "60 yuan", "80 yuan"], "answer": 1},
        {"part": "Part 1", "title": "公园指示牌", "text": "CITY PARK\n\nWelcome to City Park!\n\n- No swimming in the lake\n- Keep the park clean\n- Dogs must be on a leash\n- Park opens at 6:00 AM\n- Closes at 10:00 PM\n\nEnjoy your visit!", "question": "What time does the park close?", "options": ["6:00 AM", "10:00 PM", "10:00 AM", "6:00 PM"], "answer": 1},
        {"part": "Part 1", "title": "游泳池规定", "text": "SWIMMING POOL HOURS\n\nMonday - Friday: 6:00 AM - 8:00 PM\nSaturday - Sunday: 7:00 AM - 6:00 PM\n\nRULES:\n- Shower before entering\n- No diving in shallow area\n- Children under 12 must be with adult\n- Lockers available (10 yuan)", "question": "Who can use the pool without an adult?", "options": ["All children", "Children 12 and older", "Children under 6", "No one"], "answer": 1},
        {"part": "Part 2", "title": "朋友介绍", "text": "A: Hi Tom, this is my friend Lisa. She is a doctor.\nB: Nice to meet you, Lisa.\nC: Nice to meet you too, Tom.\nA: Lisa works at City Hospital. She helps many people.\nB: That's great! My mother is a nurse there.\nC: Really? Small world!", "question": "What does Lisa do?", "options": ["She is a teacher", "She is a doctor", "She is a nurse", "She is a student"], "answer": 1},
        {"part": "Part 2", "title": "购物对话", "text": "A: Can I help you?\nB: Yes, I'm looking for a jacket.\nA: What color do you like?\nB: I like blue or black.\nA: We have nice blue jackets over there. What size?\nB: Size M, please.\nA: Here you are. Try it on!", "question": "What does the customer want to buy?", "options": ["A shirt", "A jacket", "A dress", "Shoes"], "answer": 1},
        {"part": "Part 2", "title": "点餐对话", "text": "Waiter: Good evening. What would you like?\nCustomer: I'd like some rice and chicken, please.\nWaiter: Would you like something to drink?\nCustomer: Yes, a glass of orange juice.\nWaiter: Anything else?\nCustomer: No, that's all. Thank you.", "question": "What did the customer order?", "options": ["Rice and soup", "Rice and chicken", "Noodles and chicken", "Rice and vegetables"], "answer": 1},
        {"part": "Part 2", "title": "问路对话", "text": "A: Excuse me, where is the train station?\nB: Go straight and turn left at the second traffic light.\nA: Is it far?\nB: It's about 10 minutes' walk.\nA: Thank you!\nB: You're welcome!", "question": "How far is the train station?", "options": ["5 minutes", "10 minutes", "15 minutes", "20 minutes"], "answer": 1},
        {"part": "Part 2", "title": "预约医生", "text": "A: Good morning, City Hospital.\nB: Good morning. I'd like to make an appointment.\nA: What's your name?\nB: John Smith.\nA: When would you like to come?\nB: Tomorrow afternoon if possible.\nA: 3 PM. Is that okay?\nB: Perfect! Thank you.", "question": "When is the appointment?", "options": ["Today morning", "Today afternoon", "Tomorrow afternoon", "Day after tomorrow"], "answer": 2},
        {"part": "Part 3", "title": "学校公告", "text": "Dear Students,\n\nOur school will hold an English competition next Friday. All students are welcome to join. The topic this year is 'My Dream Job'. You need to give a 3-minute speech in English.\n\nSign up at the school office before Wednesday.\n\nGood luck!\nPrincipal Chen", "question": "What is the topic of the competition?", "options": ["My Hometown", "My Dream Job", "My Best Friend", "My School Life"], "answer": 1},
        {"part": "Part 3", "title": "生日聚会邀请", "text": "You're invited to Lisa's birthday party!\n\nDate: This Saturday\nTime: 3:00 PM - 6:00 PM\nPlace: Lisa's Home, 123 Green Street\n\nActivities: Games, Cake, Presents!\n\nPlease bring your favorite snack.\nRSVP by Friday: 555-6789\n\nSee you there!", "question": "What should guests bring?", "options": ["A gift", "A snack", "A game", "Nothing"], "answer": 1},
        {"part": "Part 3", "title": "旅行计划", "text": "Our family trip to Beijing\n\nDay 1: Arrive in Beijing, check into hotel\nDay 2: Visit the Great Wall\nDay 3: Visit the Palace Museum and Tiananmen Square\nDay 4: Go to Wangfujing Street for shopping\nDay 5: Return home\n\nBest season: Spring or Autumn", "question": "On which day do they visit the Great Wall?", "options": ["Day 1", "Day 2", "Day 3", "Day 4"], "answer": 1},
        {"part": "Part 3", "title": "健康小贴士", "text": "10 Tips for Staying Healthy\n\n1. Drink 8 glasses of water every day\n2. Eat more fruits and vegetables\n3. Exercise for 30 minutes daily\n4. Get enough sleep (8 hours)\n5. Wash your hands before eating\n6. Don't eat too much junk food\n7. Stay happy and relaxed\n8. Don't watch too much TV\n9. Take breaks during work\n10. Visit the doctor regularly", "question": "How much water should you drink daily?", "options": ["4 glasses", "6 glasses", "8 glasses", "10 glasses"], "answer": 2},
        {"part": "Part 3", "title": "环保倡议", "text": "Let's Save Our Planet!\n\n- Turn off lights when leaving a room\n- Use less plastic bags\n- Plant more trees\n- Don't waste water\n- Ride a bike or walk instead of driving\n- Recycle paper, plastic and glass\n- Turn off tap water while brushing teeth\n\nEvery small action makes a difference!", "question": "What should you do when leaving a room?", "options": ["Keep the lights on", "Turn off the lights", "Open the windows", "Lock the door"], "answer": 1},
        {"part": "Part 4", "title": "日记", "text": "March 15th, Saturday\n\nToday was a wonderful day! In the morning, I went to the park with my family. We had a picnic and played games. The weather was perfect - sunny but not too hot.\n\nIn the afternoon, I studied English for two hours. Then I called my grandmother. She told me about her garden. She planted some beautiful flowers.\n\nIn the evening, I watched a movie with my parents. It was very funny. What a great day!", "question": "What did the writer do in the afternoon?", "options": ["Went to the park", "Studied English", "Called grandmother", "Watched a movie"], "answer": 1},
        {"part": "Part 4", "title": "邮件回复", "text": "Hi Tom,\n\nThanks for your email! I'm so happy you want to visit me in Beijing.\n\nYes, you can stay at my house. My parents will be very happy to meet you.\n\nYou can come during the summer vacation. I'll show you around Beijing. We can visit the Great Wall, the Palace Museum, and many other interesting places.\n\nPlease let me know when you can come.\n\nBest wishes,\nLi Ming", "question": "When can Tom visit?", "options": ["During winter vacation", "During summer vacation", "During spring", "Any time"], "answer": 1},
        {"part": "Part 4", "title": "自我介绍", "text": "Hello, my name is Wang Mei. I'm 12 years old. I'm a student at Beijing International School.\n\nI have many hobbies. I like reading, swimming, and playing the piano. My favorite subject is English because I want to travel around the world one day.\n\nI have a small dog named Lucky. He is very cute. We go for a walk together every morning.\n\nI want to be a teacher when I grow up. What about you?", "question": "What does Wang Mei want to be?", "options": ["A doctor", "A teacher", "A writer", "A musician"], "answer": 1},
        {"part": "Part 5", "title": "选词填空", "text": "My School Life\n\nI (1)_____ to a big school in Beijing. Every day, I (2)_____ up at 6:30 and (3)_____ to school by bus. Classes start at 8:00.\n\nMy favorite subject is Math. I (4)_____ it very interesting. After school, I usually (5)_____ with my friends.\n\n(1) A. go B. goes C. going D. went\n(2) A. wake B. wakes C. waking D. woken\n(3) A. walk B. walks C. walking D. walked\n(4) A. think B. thinks C. thinking D. thought\n(5) A. play B. plays C. playing D. played", "options": ["A, B, A, A, A", "A, A, A, A, A", "B, B, B, B, B", "A, A, A, A, B"], "answer": 1},
        {"part": "Part 5", "title": "语法填空", "text": "My Best Friend\n\nI have a best friend (1)_____ name is Lily. She (2)_____ 13 years old. We (3)_____ in the same class.\n\nLily is tall (4)_____ long black hair. She likes (5)_____ books. We often study together after school.\n\n(1) A. who B. whose C. which D. that\n(2) A. is B. are C. be D. been\n(3) A. study B. studies C. studying D. studied\n(4) A. for B. with C. and D. but\n(5) A. read B. reads C. reading D. to read", "options": ["B, A, B, B, C", "B, A, A, B, C", "A, A, A, C, C", "B, A, A, C, C"], "answer": 1},
    ]

    for item in reading_data:
        c.execute(
            'INSERT INTO reading_items (part, title, text, question, options, answer) VALUES (?, ?, ?, ?, ?, ?)',
            (item['part'], item['title'], item['text'], item['question'], json.dumps(item['options']), item['answer'])
        )

    # Writing items - 20 prompts
    writing_data = [
        {"type": "邮件", "prompt": "你的朋友 John 想了解你的学校生活。请你给他写一封邮件，介绍你的学校、老师和最喜欢的学科。", "word_min": 25, "word_max": 35, "tips": json.dumps(["介绍学校名称和位置", "描述至少一位老师", "说明最喜欢的学科及原因"]), "reference": "Dear John,\n\nMy name is Li Ming. I'm happy to tell you about my school.\n\nI study at Beijing International School. It's very big and beautiful. There are many trees and flowers in the campus.\n\nMy English teacher is Mr. Wang. He is very kind and his classes are fun. My favorite subject is Math because I think it's interesting and useful.\n\nWhat about your school? Please write to me!\n\nBest wishes,\nLi Ming"},
        {"type": "邮件", "prompt": "你的笔友 Mary 想了解你的周末生活。请给她写一封邮件，描述你通常如何度过周末。", "word_min": 25, "word_max": 35, "tips": json.dumps(["说明周六和周日分别做什么", "提到至少一个具体活动", "表达对周末的感受"]), "reference": "Dear Mary,\n\nThank you for your last letter. Now let me tell you about my weekend.\n\nOn Saturday morning, I usually sleep late because I'm tired after school. In the afternoon, I play basketball with my friends in the park. Sunday is my family day. We often have lunch together and sometimes go shopping.\n\nI really enjoy my weekends because I can relax and spend time with my family.\n\nWhat do you usually do on weekends?\n\nLove,\nLi Ming"},
        {"type": "邮件", "prompt": "你感冒了不能去上学，给老师写一封邮件请假，并说明原因。", "word_min": 20, "word_max": 30, "tips": json.dumps(["说明生病的情况", "表示歉意", "承诺会补上功课"]), "reference": "Dear Mr. Wang,\n\nI'm sorry to tell you that I can't go to school today because I have a cold and fever. I went to the doctor this morning and he said I need to rest at home.\n\nI'm very sorry for missing your class. I will ask my classmate for the homework and make sure to catch up.\n\nThank you for your understanding.\n\nBest regards,\nLi Ming"},
        {"type": "邮件", "prompt": "你的英国朋友 Tom 想了解中国的传统节日。请你给他介绍一个你喜欢的中国节日。", "word_min": 25, "word_max": 35, "tips": json.dumps(["介绍节日名称和时间", "描述节日活动和食物", "说明为什么喜欢这个节日"]), "reference": "Dear Tom,\n\nI'm glad to tell you about Spring Festival, the most important holiday in China.\n\nSpring Festival is in January or February. Before the festival, we clean our houses and buy new clothes. On New Year's Eve, our family has a big dinner together. We eat dumplings and fish. We also watch CCTV New Year's Gala.\n\nI love Spring Festival because I can be with my family and get red packets with lucky money!\n\nWhat's your favorite holiday?\n\nBest,\nLi Ming"},
        {"type": "邮件", "prompt": "你上周参加了学校组织的郊游活动，给你不在本地的叔叔写一封信分享这次经历。", "word_min": 25, "word_max": 35, "tips": json.dumps(["介绍郊游的地点和时间", "描述活动中最有趣的部分", "分享你的感受"]), "reference": "Dear Uncle,\n\nI hope you are well. I want to tell you about our school trip last week.\n\nWe went to the Beijing Wildlife Park. It was so exciting! I saw many animals like pandas, lions and elephants. The panda was my favorite because it was so cute and lazy!\n\nWe had a picnic lunch in the park. The food tasted great in the open air. I took many photos there.\n\nI wish you could have been with us!\n\nLove,\nLi Ming"},
        {"type": "便条", "prompt": "你出门时妈妈还没回来，给她留一张便条，告诉她你去了哪里以及预计什么时候回家。", "word_min": 20, "word_max": 30, "tips": json.dumps(["说明你去了哪里", "告诉妈妈你会什么时候回", "留一个联系电话"]), "reference": "Dear Mom,\n\nI went to the library to study with Lily. I'll be back around 5 PM.\n\nThere's a math test tomorrow so we need to prepare. Please don't worry about me.\n\nIf you need me, call my phone: 138-xxxx-xxxx.\n\nSee you soon!\nLi Ming"},
        {"type": "便条", "prompt": "你的好朋友要转学了，给他/她留一张便条，表达你的不舍和祝福。", "word_min": 20, "word_max": 30, "tips": json.dumps(["表达不舍之情", "回忆一起度过的美好时光", "送上祝福"]), "reference": "Dear Tom,\n\nI'm so sad to hear that you're moving to Shanghai. You are my best friend and I'll miss you a lot.\n\nI still remember the day we played soccer together and you helped me win the game. Those are happy memories I'll never forget.\n\nI hope you'll make new friends in Shanghai and come back to visit me during holidays.\n\nGood luck, my friend!\nLi Ming"},
        {"type": "便条", "prompt": "你邀请朋友来家里参加你的生日聚会，给他/她写一张便条告知聚会的时间、地点和活动内容。", "word_min": 20, "word_max": 30, "tips": json.dumps(["说明聚会的时间和地点", "告诉朋友活动安排", "提醒朋友带什么东西"]), "reference": "Dear Lily,\n\nI'm having a birthday party this Saturday! I really want you to come.\n\nTime: 3 PM - 6 PM\nPlace: My home, Room 501, Building 3, Sunshine Community\n\nWe'll have cake, play games and open presents together. Please bring your favorite song for karaoke!\n\nI hope you can make it!\nLi Ming"},
        {"type": "便条", "prompt": "你的室友每天晚上都很吵，你给他/她写一张便条，请他/她保持安静。", "word_min": 15, "word_max": 25, "tips": json.dumps(["礼貌地说明问题", "说明这对你的影响", "提出具体的请求"]), "reference": "Dear roommate,\n\nI'm writing this because I have trouble sleeping at night. The noise from your room makes it hard for me to rest.\n\nI know we all have different schedules, but could you please keep the volume down after 10 PM? I have classes in the morning.\n\nThank you for your understanding!\nLi Ming"},
        {"type": "便条", "prompt": "你借了同学的自行车但不小心弄坏了，给他/她写一张道歉便条，说明情况并表示会修理或赔偿。", "word_min": 15, "word_max": 25, "tips": json.dumps(["真诚道歉", "说明发生的事情", "提出解决方案"]), "reference": "Dear Jack,\n\nI'm so sorry! When I was riding your bike yesterday, I accidentally hit a stone and the wheel was damaged.\n\nI've already sent it to the repair shop. The bike will be fixed by tomorrow and the cost is on me.\n\nI'm really sorry for this mistake. I'll be more careful next time.\n\nLi Ming"},
        {"type": "故事", "prompt": "图片描述：一只小狗在公园里迷路了，看图写一个30-40词的故事。", "word_min": 30, "word_max": 40, "tips": json.dumps(["描述图片中的场景", "讲述故事的起因、经过和结果", "故事要有完整性"]), "reference": "One sunny afternoon, a little dog was playing in the park. He ran after a butterfly and got lost. He looked around but couldn't find his owner. He sat down and felt sad. Just then, a kind girl helped him call the police. Finally, the dog was reunited with his owner."},
        {"type": "故事", "prompt": "图片描述：下雨天，一个小男孩把伞借给了陌生的老奶奶。写一个30-40词的故事。", "word_min": 30, "word_max": 40, "tips": json.dumps(["描述下雨的场景", "小男孩看到老奶奶后的反应", "故事的结局和道理"]), "reference": "It was raining heavily on my way home from school. I saw an old grandmother standing under a tree, looking worried. I ran to her and shared my umbrella. She smiled and thanked me. I felt very happy because I helped someone in need."},
        {"type": "故事", "prompt": "图片描述：一个小女孩在海边捡到一只受伤的海豚。写一个30-40词的故事。", "word_min": 30, "word_max": 40, "tips": json.dumps(["描述发现海豚的场景", "小女孩如何帮助海豚", "故事的结尾"]), "reference": "Last summer, a little girl found a hurt dolphin on the beach. She called the animal rescue center immediately. The workers came and took the dolphin away. A week later, the girl visited the dolphin. It was healthy again and swam happily in the water."},
        {"type": "描述", "prompt": "介绍一下你的卧室。要求：30-40词，包含房间里的主要物品和你的感受。", "word_min": 30, "word_max": 40, "tips": json.dumps(["描述卧室的位置和大小", "列举主要家具物品", "说说你为什么喜欢这个房间"]), "reference": "My bedroom is on the second floor of my house. It's not big but very cozy. There is a soft bed, a wooden desk and a big bookshelf. I put many photos on the wall. I love my bedroom because it's my favorite place to relax and read."},
        {"type": "描述", "prompt": "介绍一下你最喜欢的季节，说说为什么喜欢它，包含天气、活动和感受。", "word_min": 30, "word_max": 40, "tips": json.dumps(["说明是哪个季节", "描述这个季节的天气特点", "介绍在这个季节常做的事情", "表达你的感受"]), "reference": "My favorite season is spring. The weather is warm and sunny. Flowers bloom and trees turn green. I often go to the park to fly kites with my family. Spring makes me feel happy and energetic. I love the beautiful colors of nature in spring."},
        {"type": "卡片", "prompt": "给即将过生日的爷爷写一张生日卡片，表达你的祝福。", "word_min": 20, "word_max": 30, "tips": json.dumps(["称呼爷爷", "送上生日祝福", "表达爱意"]), "reference": "Dear Grandpa,\n\nHappy Birthday! 🎂\n\nI wish you health and happiness on your special day. Thank you for always loving me and telling me wonderful stories. You are the best grandpa in the world!\n\nI love you so much!\nYour grandchild,\nLi Ming"},
        {"type": "卡片", "prompt": "给帮助过你的老师写一张感谢卡片，表达你的感激之情。", "word_min": 20, "word_max": 30, "tips": json.dumps(["称呼老师", "具体说明感谢的原因", "送上祝福"]), "reference": "Dear Ms. Liu,\n\nThank you so much for helping me with my English. You were so patient when I couldn't understand the grammar rules. Because of your help, I got a high score on my exam!\n\nYou are the best teacher!\nWith gratitude,\nLi Ming"},
        {"type": "卡片", "prompt": "给你的好朋友写一张鼓励卡片，在他/她遇到困难时给予支持。", "word_min": 20, "word_max": 30, "tips": json.dumps(["鼓励朋友", "肯定朋友的能力", "表达支持"]), "reference": "Dear Lily,\n\nI heard you didn't do well on the test. Don't be sad! I know you worked really hard. Sometimes we fail but that doesn't mean we're not smart.\n\nI believe in you! You're my best friend and I'm proud of you.\n\nLet's study together and do better next time!\nLove,\nMing"},
        {"type": "邮件", "prompt": "你计划暑假去北京旅游，给当地的朋友写一封邮件，询问旅游建议。", "word_min": 25, "word_max": 35, "tips": json.dumps(["介绍你的旅行计划", "询问值得参观的景点", "询问当地美食推荐"]), "reference": "Dear Wang Wei,\n\nI'm planning to visit Beijing this summer vacation. Can you give me some suggestions?\n\nI want to visit the Great Wall and the Palace Museum. What other places do you think I shouldn't miss? Also, do you have any food recommendations?\n\nI'm really excited about this trip!\n\nBest,\nTom"},
        {"type": "邮件", "prompt": "你的网友想了解你最喜欢的运动，给你远在美国的网友写一封邮件介绍你喜欢的运动。", "word_min": 25, "word_max": 35, "tips": json.dumps(["介绍是什么运动", "为什么喜欢这项运动", "你通常在哪里做这项运动"]), "reference": "Dear Mike,\n\nYou asked about my favorite sport in your last email. It's basketball!\n\nI started playing basketball two years ago. I love it because it's exciting and I can play with my friends. We usually play in the school gym after class.\n\nI really enjoy the feeling when I score a point!\n\nWhat's your favorite sport?\n\nCheers,\nLi Ming"},
    ]

    for item in writing_data:
        c.execute(
            'INSERT INTO writing_items (type, prompt, word_min, word_max, tips, reference) VALUES (?, ?, ?, ?, ?, ?)',
            (item['type'], item['prompt'], item['word_min'], item['word_max'], item['tips'], item['reference'])
        )

    # Listening items - 20 dialogues
    listening_data = [
        {"dialogue": "What time does the library open? It opens at nine. And when does it close? It closes at five.", "audio_file": "audio/listening1.mp3", "question": "图书馆什么时候关闭？", "options": json.dumps(["九点", "五点", "六点", "七点"]), "answer": 1},
        {"dialogue": "Where is the nearest bus stop? It's on Main Street. Is it far from here? No, it's just five minutes' walk.", "audio_file": "audio/listening2.mp3", "question": "公交站在哪里？", "options": json.dumps(["公园旁边", "主街上", "学校旁边", "医院旁边"]), "answer": 1},
        {"dialogue": "What would you like for lunch? I'll have some noodles. Anything to drink? Yes, a glass of orange juice please.", "audio_file": "audio/listening3.mp3", "question": "顾客点了什么？", "options": json.dumps(["米饭和咖啡", "面条和橙汁", "三明治和水", "面条和牛奶"]), "answer": 1},
        {"dialogue": "How much is this shirt? It's 80 yuan. And this one? The blue one? Yes, that's 120 yuan.", "audio_file": "audio/listening4.mp3", "question": "这件衬衫多少钱？", "options": json.dumps(["80元", "120元", "100元", "60元"]), "answer": 0},
        {"dialogue": "What's your favorite color? I like blue best. Why? Because it's the color of the sky.", "audio_file": "audio/listening5.mp3", "question": "他最喜欢什么颜色？", "options": json.dumps(["红色", "蓝色", "绿色", "黄色"]), "answer": 1},
        {"dialogue": "When is your birthday? It's on June 15th. And your sister's? Her birthday is on December 3rd.", "audio_file": "audio/listening6.mp3", "question": "说话人的生日是什么时候？", "options": json.dumps(["6月3日", "6月15日", "12月3日", "12月15日"]), "answer": 1},
        {"dialogue": "How many people are there in your family? There are five. My parents, my grandparents, and me.", "audio_file": "audio/listening7.mp3", "question": "家里有几口人？", "options": json.dumps(["三口", "四口", "五口", "六口"]), "answer": 2},
        {"dialogue": "What subject do you like best? I like English best. Why? Because it's interesting and useful.", "audio_file": "audio/listening8.mp3", "question": "他最喜欢什么学科？", "options": json.dumps(["数学", "语文", "英语", "科学"]), "answer": 2},
        {"dialogue": "Where did you go last weekend? I went to the park. Did you have fun? Yes, it was great!", "audio_file": "audio/listening9.mp3", "question": "他上周末去了哪里？", "options": json.dumps(["图书馆", "公园", "商场", "电影院"]), "answer": 1},
        {"dialogue": "What day is it today? It's Wednesday. And tomorrow? Tomorrow is Thursday.", "audio_file": "audio/listening10.mp3", "question": "今天是星期几？", "options": json.dumps(["星期二", "星期三", "星期四", "星期五"]), "answer": 1},
        {"dialogue": "Can you speak English? Yes, I can speak a little. How long have you learned it? For three years.", "audio_file": "audio/listening11.mp3", "question": "他学英语多长时间了？", "options": json.dumps(["一年", "两年", "三年", "四年"]), "answer": 2},
        {"dialogue": "What's the weather like today? It's sunny and warm. Is it suitable for outdoor activities? Yes, perfect!", "audio_file": "audio/listening12.mp3", "question": "今天天气怎么样？", "options": json.dumps(["下雨天", "下雪天", "晴天暖和", "阴天"]), "answer": 2},
        {"dialogue": "How do you usually go to school? I usually go by bus. Do you like it? Yes, but sometimes I walk.", "audio_file": "audio/listening13.mp3", "question": "他通常怎么去学校？", "options": json.dumps(["步行", "骑自行车", "坐公共汽车", "开车"]), "answer": 2},
        {"dialogue": "What would you like to be in the future? I want to be a doctor. Why? Because I want to help people.", "audio_file": "audio/listening14.mp3", "question": "她想做什么职业？", "options": json.dumps(["老师", "医生", "工程师", "警察"]), "answer": 1},
        {"dialogue": "How much water do you drink every day? About eight glasses. That's a good habit!", "audio_file": "audio/listening15.mp3", "question": "他每天喝多少水？", "options": json.dumps(["四杯", "六杯", "八杯", "十杯"]), "answer": 2},
        {"dialogue": "What's your telephone number? It's 555-1234. And your address? 123 Main Street.", "audio_file": "audio/listening16.mp3", "question": "他的电话号码是什么？", "options": json.dumps(["555-1234", "555-4321", "555-1111", "555-2222"]), "answer": 0},
        {"dialogue": "What did you do yesterday evening? I watched a movie. Was it good? Yes, it was very interesting.", "audio_file": "audio/listening17.mp3", "question": "她昨晚做了什么？", "options": json.dumps(["看书", "看电影", "玩游戏", "做作业"]), "answer": 1},
        {"dialogue": "Which sport do you like best? I like swimming best. How often do you swim? Twice a week.", "audio_file": "audio/listening18.mp3", "question": "她多长时间游泳一次？", "options": json.dumps(["每周一次", "每周两次", "每周三次", "每月两次"]), "answer": 1},
        {"dialogue": "How long have you lived here? I've lived here for ten years. Do you like this place? Yes, very much.", "audio_file": "audio/listening19.mp3", "question": "他在这里住了多久？", "options": json.dumps(["五年", "八年", "十年", "十二年"]), "answer": 2},
        {"dialogue": "What time do you usually go to bed? I usually go to bed at ten. And wake up? At six in the morning.", "audio_file": "audio/listening20.mp3", "question": "他通常几点起床？", "options": json.dumps(["五点", "六点", "七点", "八点"]), "answer": 1},
    ]

    for item in listening_data:
        c.execute(
            'INSERT INTO listening_items (dialogue, audio_file, question, options, answer) VALUES (?, ?, ?, ?, ?)',
            (item['dialogue'], item['audio_file'], item['question'], item['options'], item['answer'])
        )

def hash_password(password):
    """Hash password"""
    return hashlib.sha256((password + 'ket_salt_2024').encode()).hexdigest()

def verify_password(password, hash_val):
    """Verify password"""
    return hash_password(password) == hash_val

# ==================== Admin API ====================

def verify_admin(password):
    """Verify admin password"""
    return password == ADMIN_PASSWORD

@app.route('/api/admin/verify', methods=['POST'])
def admin_verify():
    """Verify admin password"""
    data = request.json
    password = data.get('password')
    if verify_admin(password):
        return jsonify({'success': True})
    return jsonify({'error': '密码错误'}), 401

@app.route('/api/admin/vocab', methods=['GET'])
def admin_get_vocab():
    """Get all vocab items"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM vocab_items ORDER BY id')
    items = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'success': True, 'data': items})

@app.route('/api/admin/vocab', methods=['POST'])
def admin_add_vocab():
    """Add a vocab item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO vocab_items (word, phonetic, translation, example, category) VALUES (?, ?, ?, ?, ?)',
        (data['word'], data.get('phonetic', ''), data['translation'], data.get('example', ''), data.get('category', '日常'))
    )
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': item_id})

@app.route('/api/admin/vocab/<int:item_id>', methods=['PUT'])
def admin_update_vocab(item_id):
    """Update a vocab item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'UPDATE vocab_items SET word=?, phonetic=?, translation=?, example=?, category=? WHERE id=?',
        (data['word'], data.get('phonetic', ''), data['translation'], data.get('example', ''), data.get('category', '日常'), item_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/vocab/<int:item_id>', methods=['DELETE'])
def admin_delete_vocab(item_id):
    """Delete a vocab item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM vocab_items WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/reading', methods=['GET'])
def admin_get_reading():
    """Get all reading items"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM reading_items ORDER BY id')
    items = []
    for row in c.fetchall():
        item = dict(row)
        item['options'] = json.loads(item['options'])
        items.append(item)
    conn.close()
    return jsonify({'success': True, 'data': items})

@app.route('/api/admin/reading', methods=['POST'])
def admin_add_reading():
    """Add a reading item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO reading_items (part, title, text, question, options, answer) VALUES (?, ?, ?, ?, ?, ?)',
        (data['part'], data['title'], data['text'], data['question'], json.dumps(data['options']), data['answer'])
    )
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': item_id})

@app.route('/api/admin/reading/<int:item_id>', methods=['PUT'])
def admin_update_reading(item_id):
    """Update a reading item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'UPDATE reading_items SET part=?, title=?, text=?, question=?, options=?, answer=? WHERE id=?',
        (data['part'], data['title'], data['text'], data['question'], json.dumps(data['options']), data['answer'], item_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/reading/<int:item_id>', methods=['DELETE'])
def admin_delete_reading(item_id):
    """Delete a reading item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM reading_items WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/writing', methods=['GET'])
def admin_get_writing():
    """Get all writing items"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM writing_items ORDER BY id')
    items = []
    for row in c.fetchall():
        item = dict(row)
        item['tips'] = json.loads(item['tips']) if item['tips'] else []
        items.append(item)
    conn.close()
    return jsonify({'success': True, 'data': items})

@app.route('/api/admin/writing', methods=['POST'])
def admin_add_writing():
    """Add a writing item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO writing_items (type, prompt, word_min, word_max, tips, reference) VALUES (?, ?, ?, ?, ?, ?)',
        (data['type'], data['prompt'], data.get('word_min', 25), data.get('word_max', 40), json.dumps(data.get('tips', [])), data.get('reference', ''))
    )
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': item_id})

@app.route('/api/admin/writing/<int:item_id>', methods=['PUT'])
def admin_update_writing(item_id):
    """Update a writing item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'UPDATE writing_items SET type=?, prompt=?, word_min=?, word_max=?, tips=?, reference=? WHERE id=?',
        (data['type'], data['prompt'], data.get('word_min', 25), data.get('word_max', 40), json.dumps(data.get('tips', [])), data.get('reference', ''), item_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/writing/<int:item_id>', methods=['DELETE'])
def admin_delete_writing(item_id):
    """Delete a writing item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM writing_items WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/listening', methods=['GET'])
def admin_get_listening():
    """Get all listening items"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM listening_items ORDER BY id')
    items = []
    for row in c.fetchall():
        item = dict(row)
        item['options'] = json.loads(item['options'])
        items.append(item)
    conn.close()
    return jsonify({'success': True, 'data': items})

@app.route('/api/admin/listening', methods=['POST'])
def admin_add_listening():
    """Add a listening item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO listening_items (dialogue, audio_file, question, options, answer) VALUES (?, ?, ?, ?, ?)',
        (data['dialogue'], data.get('audio_file', ''), data['question'], json.dumps(data['options']), data['answer'])
    )
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': item_id})

@app.route('/api/admin/listening/<int:item_id>', methods=['PUT'])
def admin_update_listening(item_id):
    """Update a listening item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'UPDATE listening_items SET dialogue=?, audio_file=?, question=?, options=?, answer=? WHERE id=?',
        (data['dialogue'], data.get('audio_file', ''), data['question'], json.dumps(data['options']), data['answer'], item_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/listening/<int:item_id>', methods=['DELETE'])
def admin_delete_listening(item_id):
    """Delete a listening item"""
    password = request.headers.get('X-Admin-Password')
    if not verify_admin(password):
        return jsonify({'error': '未授权'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM listening_items WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ==================== Public API ====================

@app.route('/api/vocab', methods=['GET'])
def get_vocab():
    """Get all vocab items (public)"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM vocab_items ORDER BY id')
    items = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'success': True, 'data': items})

@app.route('/api/reading', methods=['GET'])
def get_reading():
    """Get all reading items (public)"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM reading_items ORDER BY id')
    items = []
    for row in c.fetchall():
        item = dict(row)
        item['options'] = json.loads(item['options'])
        items.append(item)
    conn.close()
    return jsonify({'success': True, 'data': items})

@app.route('/api/writing', methods=['GET'])
def get_writing():
    """Get all writing items (public)"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM writing_items ORDER BY id')
    items = []
    for row in c.fetchall():
        item = dict(row)
        item['tips'] = json.loads(item['tips']) if item['tips'] else []
        items.append(item)
    conn.close()
    return jsonify({'success': True, 'data': items})

@app.route('/api/listening', methods=['GET'])
def get_listening():
    """Get all listening items (public)"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM listening_items ORDER BY id')
    items = []
    for row in c.fetchall():
        item = dict(row)
        item['options'] = json.loads(item['options'])
        items.append(item)
    conn.close()
    return jsonify({'success': True, 'data': items})

# ==================== User API ====================

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

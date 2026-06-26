import logging
import sqlite3
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# -------------------- НАСТРОЙКИ --------------------
TOKEN = '8801956759:AAG6OhDZd_yjGQD4qhB2UliPLG9wuYdV3cA'

# Состояния для анкеты
NAME, GENDER, BIRTHDATE, FAMILY_STATUS, CHILDREN, LOCATION = range(6)

# Состояния для редактирования
EDIT_CHOICE, EDIT_NAME, EDIT_GENDER, EDIT_BIRTHDATE, EDIT_FAMILY_STATUS, EDIT_CHILDREN, EDIT_LOCATION = range(6, 13)

# Состояние для настройки времени
SET_TIME = 13

# -------------------- ОПРЕДЕЛЕНИЕ ЧАСОВОГО ПОЯСА (ЛОКАЛЬНАЯ ТАБЛИЦА) --------------------
def get_timezone_by_city(city_name):
    city_clean = city_name.split(',')[0].strip().lower()
    timezone_map = {
        'калининград': 2,
        'москва': 3, 'санкт-петербург': 3, 'мурманск': 3, 'архангельск': 3,
        'волгоград': 3, 'воронеж': 3, 'ярославль': 3, 'рязань': 3, 'тула': 3,
        'тверь': 3, 'калуга': 3, 'смоленск': 3, 'псков': 3, 'великий новгород': 3,
        'белгород': 3, 'курск': 3, 'орёл': 3, 'брянск': 3, 'липецк': 3,
        'тамбов': 3, 'иваново': 3, 'владимир': 3, 'кострома': 3, 'нижний новгород': 3,
        'чебоксары': 3, 'йошкар-ола': 3, 'саранск': 3, 'киров': 3, 'казань': 3,
        'ульяновск': 3, 'самара': 3, 'саратов': 3, 'пенза': 3, 'набережные челны': 3,
        'сочи': 3, 'краснодар': 3, 'новороссийск': 3, 'ставрополь': 3, 'махачкала': 3,
        'грозный': 3, 'владикавказ': 3, 'нальчик': 3, 'черкесск': 3, 'майкоп': 3,
        'элиста': 3, 'астрахань': 3, 'симферополь': 3, 'севастополь': 3,
        'ижевск': 4, 'пермь': 4,
        'екатеринбург': 5, 'челябинск': 5, 'тюмень': 5, 'курган': 5, 'сургут': 5, 'нижневартовск': 5,
        'омск': 6,
        'красноярск': 7, 'новосибирск': 7, 'томск': 7, 'кемерово': 7, 'новокузнецк': 7, 'барнаул': 7, 'абакан': 7, 'кызыл': 7,
        'иркутск': 8, 'улан-удэ': 8,
        'якутск': 9, 'чита': 9,
        'владивосток': 10, 'хабаровск': 10, 'южно-сахалинск': 10,
        'магадан': 11,
        'петропавловск-камчатский': 12, 'анадырь': 12,
        'киев': 2, 'харьков': 2, 'одесса': 2, 'днепр': 2, 'донецк': 3, 'луганск': 3, 'львов': 2, 'запорожье': 2,
        'минск': 3, 'гомель': 3, 'брест': 3, 'витебск': 3, 'гродно': 3, 'могилёв': 3,
        'астана': 5, 'алматы': 5, 'караганда': 5, 'шимкент': 5,
        'ташкент': 5, 'самарканд': 5, 'бухара': 5,
        'ереван': 4, 'баку': 4, 'тбилиси': 4, 'кишинёв': 2,
        'бишкек': 6, 'душанбе': 5, 'ашхабад': 5,
        'рига': 2, 'вильнюс': 2, 'таллин': 2,
    }
    for key, offset in timezone_map.items():
        if key in city_clean or city_clean in key:
            return offset
    return None

def get_local_delivery_time(city_name):
    offset = get_timezone_by_city(city_name)
    if offset is None:
        return '08:00'
    utc_hour = 8 - offset
    if utc_hour < 0:
        utc_hour += 24
    elif utc_hour >= 24:
        utc_hour -= 24
    return f"{int(utc_hour):02d}:00"

def calculate_age(birthdate_str):
    try:
        birthdate = datetime.strptime(birthdate_str, '%d.%m.%Y')
        today = datetime.now()
        age = today.year - birthdate.year
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age -= 1
        return age
    except:
        return None

def is_birthday_today(birthdate_str):
    try:
        birthdate = datetime.strptime(birthdate_str, '%d.%m.%Y')
        today = datetime.now()
        return birthdate.day == today.day and birthdate.month == today.month
    except:
        return False

# -------------------- БАЗА ДАННЫХ --------------------
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            gender TEXT,
            birthdate TEXT,
            family_status TEXT,
            children TEXT,
            location TEXT,
            delivery_time TEXT DEFAULT '08:00',
            last_bible_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user(user_id, name, gender, birthdate, family_status, children, location):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    delivery_time = get_local_delivery_time(location)
    c.execute('''
        INSERT OR REPLACE INTO users (user_id, name, gender, birthdate, family_status, children, location, delivery_time, last_bible_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, gender, birthdate, family_status, children, location, delivery_time, None))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id, name, gender, birthdate, family_status, children, location, delivery_time FROM users')
    users = c.fetchall()
    conn.close()
    return users

def update_delivery_time(user_id, delivery_time):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET delivery_time = ? WHERE user_id = ?', (delivery_time, user_id))
    conn.commit()
    conn.close()

def update_last_bible_date(user_id, date_str):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET last_bible_date = ? WHERE user_id = ?', (date_str, user_id))
    conn.commit()
    conn.close()

def user_exists(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def get_user_time(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT delivery_time FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else '08:00'

# -------------------- БИБЛИОТЕКА СТИХОВ (РАСШИРЕННАЯ) --------------------
BIBLE_VERSES = [
    # Универсальные (all)
    {"text": "Притчи 3:5-6: Надейся на Господа всем сердцем твоим, и не полагайся на разум твой. Во всех путях твоих познавай Его, и Он направит стези твои.", "tags": ["all"]},
    {"text": "Иеремия 29:11: Ибо только Я знаю намерения, какие имею о вас, говорит Господь, намерения во благо, а не на зло, чтобы дать вам будущность и надежду.", "tags": ["all"]},
    {"text": "Псалом 90:11-12: Ибо Ангелам Своим заповедает о тебе – охранять тебя на всех путях твоих. На руках понесут тебя, да не преткнешься о камень ногою твоею.", "tags": ["all"]},
    {"text": "Римлянам 8:28: Притом знаем, что любящим Бога, призванным по Его изволению, всё содействует ко благу.", "tags": ["all"]},
    {"text": "Филиппийцам 4:13: Всё могу в укрепляющем меня Иисусе Христе.", "tags": ["all"]},
    {"text": "Иисус Навин 1:9: Будь тверд и мужествен, не страшись и не ужасайся; ибо с тобою Господь Бог твой везде, куда ни пойдешь.", "tags": ["all"]},
    {"text": "Псалом 22:1-4: Господь – Пастырь мой; я ни в чем не буду нуждаться. Если я пойду и долиною смертной тени, не убоюсь зла, потому что Ты со мной.", "tags": ["all"]},
    {"text": "Исаия 41:10: Не бойся, ибо Я с тобою; не смущайся, ибо Я Бог твой; Я укреплю тебя, и помогу тебе, и поддержу тебя десницею правды Моей.", "tags": ["all"]},
    {"text": "Матфея 11:28-30: Придите ко Мне все труждающиеся и обремененные, и Я успокою вас; возьмите иго Мое на себя и научитесь от Меня, ибо Я кроток и смирен сердцем, и найдете покой душам вашим.", "tags": ["all"]},
    {"text": "Псалом 36:4: Утешайся Господом, и Он исполнит желания сердца твоего.", "tags": ["all"]},
    {"text": "Ефесянам 3:20: А Тому, Кто действующею в нас силою может сделать несравненно больше всего, чего мы просим, или о чем помышляем...", "tags": ["all"]},
    {"text": "Колоссянам 3:15: И да владычествует в сердцах ваших мир Божий, к которому вы и призваны в одном теле, и будьте дружелюбны.", "tags": ["all"]},
    {"text": "Псалом 55:23: Возложи на Господа заботы твои, и Он поддержит тебя. Никогда не даст Он поколебаться праведнику.", "tags": ["all"]},
    {"text": "2 Коринфянам 12:9: Довольно для тебя благодати Моей, ибо сила Моя совершается в немощи.", "tags": ["all"]},
    {"text": "Притчи 16:3: Предай Господу дела твои, и предприятия твои совершатся.", "tags": ["all"]},
    {"text": "Псалом 33:2-3: Благословлю Господа во всякое время; хвала Ему непрестанно в устах моих. Господом будет хвалиться душа моя; услышат кроткие и возвеселятся.", "tags": ["all"]},
    {"text": "Исаия 43:2: Будешь ли переходить через воды, Я с тобою, – через реки ли, они не потопят тебя; пойдешь ли через огонь, не обожжешься, и пламя не опалит тебя.", "tags": ["all"]},
    {"text": "Иоанна 14:27: Мир оставляю вам, мир Мой даю вам; не так, как мир дает, Я даю вам. Да не смущается сердце ваше и да не устрашается.", "tags": ["all"]},
    {"text": "Псалом 138:14: Славлю Тебя, потому что я дивно устроен. Дивны дела Твои, и душа моя вполне сознает это.", "tags": ["all"]},
    {"text": "Иакова 1:17: Всякое даяние доброе и всякий дар совершенный нисходит свыше, от Отца светов, у Которого нет изменения и ни тени перемены.", "tags": ["all"]},
    {"text": "2 Коринфянам 1:3-4: Благословен Бог и Отец Господа нашего Иисуса Христа, Отец милосердия и Бог всякого утешения, утешающий нас во всякой скорби.", "tags": ["all"]},
    {"text": "Псалом 102:1-4: Благослови, душа моя, Господа, и вся внутренность моя – святое имя Его. Благослови, душа моя, Господа и не забывай всех благодеяний Его.", "tags": ["all"]},
    {"text": "Михея 6:8: О, человек! сказано тебе, что – добро и чего требует от тебя Господь: действовать справедливо, любить дела милосердия и смиренномудренно ходить пред Богом твоим.", "tags": ["all"]},
    {"text": "Луки 6:38: Давайте, и дастся вам; мерою доброю, утрясенною, нагнетенною и переполненною отсыплют вам в лоно ваше.", "tags": ["all"]},
    {"text": "Евреям 13:16: Не забывайте также благотворения и общительности, ибо таковые жертвы благоугодны Богу.", "tags": ["all"]},

    # ---------- СЕМЬЯ / БРАК ----------
    {"text": "Ефесянам 5:25: Мужья, любите своих жен, как и Христос возлюбил Церковь и предал Себя за нее.", "tags": ["married", "family"]},
    {"text": "Бытие 2:18: Не хорошо быть человеку одному; сотворим ему помощника, соответственного ему.", "tags": ["married", "family"]},
    {"text": "Псалом 127:1: Если Господь не созиждет дома, напрасно трудятся строящие его.", "tags": ["family"]},
    {"text": "1 Тимофею 5:8: Если же кто о своих и особенно о домашних не печется, тот отрекся от веры и хуже неверного.", "tags": ["family"]},
    {"text": "Екклесиаст 4:9-10: Двоим лучше, нежели одному; потому что у них есть доброе вознаграждение в труде их: ибо если упадет один, то другой поднимет товарища своего.", "tags": ["married", "family"]},
    {"text": "Колоссянам 3:18-19: Жены, повинуйтесь мужьям, как прилично в Господе. Мужья, любите своих жен и не будьте к ним суровы.", "tags": ["married", "family"]},
    {"text": "Притчи 18:22: Кто нашел добрую жену, тот нашел благо и получил благословение от Господа.", "tags": ["married", "family"]},
    {"text": "Притчи 31:10-12: Кто найдет добродетельную жену? цена ее выше жемчугов. Уверено в ней сердце мужа ее, и он не останется без прибытка.", "tags": ["married", "family"]},
    {"text": "Иисус Навин 24:15: А я и дом мой будем служить Господу.", "tags": ["family"]},
    {"text": "1 Петра 3:7: Также и вы, мужья, обращайтесь благоразумно с женами, как с немощнейшим сосудом, оказывая им честь, как сонаследницам благодатной жизни.", "tags": ["married", "family"]},

    # ---------- ДЕТИ ----------
    {"text": "Псалом 127:3: Вот наследие от Господа: дети; награда от Него – плод чрева.", "tags": ["children"]},
    {"text": "Притчи 22:6: Наставь юношу при начале пути его; он не уклонится от него, когда и состарится.", "tags": ["children"]},
    {"text": "Ефесянам 6:4: И вы, отцы, не раздражайте детей ваших, но воспитывайте их в учении и наставлении Господнем.", "tags": ["children"]},
    {"text": "Марка 10:14: Пустите детей приходить ко Мне, не препятствуйте им, ибо таковых есть Царствие Божие.", "tags": ["children"]},
    {"text": "Псалом 112:9: Он неплодную вселяет в дом матерью, радующеюся о детях.", "tags": ["children"]},
    {"text": "Исаия 54:13: И все сыновья твои будут научены Господом, и великий мир будет у сыновей твоих.", "tags": ["children"]},
    {"text": "Притчи 20:7: Праведник ходит в своей непорочности; блаженны дети его после него!", "tags": ["children"]},
    {"text": "Второзаконие 6:6-7: Да будут слова сии, которые Я заповедую тебе сегодня, в сердце твоем; и внушай их детям твоим.", "tags": ["children"]},
    {"text": "Колосянам 3:20: Дети, будьте послушны родителям вашим во всем, ибо это благоугодно Господу.", "tags": ["children"]},
    {"text": "Псалом 103:15: ...и вино, которое веселит сердце человека, и елей, от которого блистает лице его, и хлеб, который укрепляет сердце человека.", "tags": ["children"]},

    # ---------- ОДИНОКИЕ / НАДЕЖДА ----------
    {"text": "Бытие 2:18: И сказал Господь Бог: не хорошо быть человеку одному; сотворим ему помощника, соответственного ему.", "tags": ["single"]},
    {"text": "Псалом 67:7: Бог одиноких вводит в дом, освобождает узников от оков.", "tags": ["single"]},
    {"text": "Исаия 54:5: Ибо твой Творец есть супруг твой; Господь Саваоф – имя Его.", "tags": ["single"]},
    {"text": "Псалом 33:19: Близок Господь к сокрушенным сердцем и смиренных духом спасет.", "tags": ["single"]},
    {"text": "Иеремия 31:3: Любовью вечною Я возлюбил тебя, потому и простер к тебе благоволение.", "tags": ["single"]},
    {"text": "Римлянам 8:38-39: Ни смерть, ни жизнь, ни настоящее, ни будущее... не может отлучить нас от любви Божией во Христе Иисусе.", "tags": ["single"]},
    {"text": "Псалом 146:3: Он исцеляет сокрушенных сердцем и врачует скорби их.", "tags": ["single"]},
    {"text": "Софония 3:17: Господь Бог твой среди тебя, Он силен спасти тебя; возвеселится о тебе радостью.", "tags": ["single"]},

    # ---------- ПАСХА ----------
    {"text": "Матфея 28:6: Его нет здесь – Он воскрес, как сказал. Подойдите, посмотрите место, где лежал Господь.", "tags": ["easter"]},
    {"text": "1 Коринфянам 15:20: Но Христос воскрес из мертвых, первенец из умерших.", "tags": ["easter"]},
    {"text": "Иоанна 11:25: Я есмь воскресение и жизнь; верующий в Меня, если и умрет, оживет.", "tags": ["easter"]},
    {"text": "Римлянам 6:9: Зная, что Христос, воскреснув из мертвых, уже не умирает: смерть уже не имеет над Ним власти.", "tags": ["easter"]},
    {"text": "1 Петра 1:3: Благословен Бог и Отец Господа нашего Иисуса Христа, по великой Своей милости возродивший нас воскресением Иисуса Христа из мертвых.", "tags": ["easter"]},
    {"text": "Откровение 1:18: И живый во веки веков; имею ключи ада и смерти.", "tags": ["easter"]},
    {"text": "Луки 24:6-7: Его нет здесь; Он воскрес. Вспомните, как Он говорил вам, когда был еще в Галилее.", "tags": ["easter"]},
    {"text": "Евреям 13:20-21: Бог же мира, воздвигший из мертвых Пастыря овец великого, Кровию завета вечного, Господа нашего Иисуса Христа...", "tags": ["easter"]},

    # ---------- РОЖДЕСТВО ----------
    {"text": "Луки 2:11: Ныне родился вам в городе Давидовом Спаситель, Который есть Христос Господь.", "tags": ["christmas"]},
    {"text": "Матфея 1:23: Се, Дева во чреве приимет и родит Сына, и нарекут имя Ему Еммануил, что значит: с нами Бог.", "tags": ["christmas"]},
    {"text": "Исаия 9:6: Младенец родился нам – Сын дан нам; владычество на раменах Его, и нарекут имя Ему: Чудный, Советник, Бог крепкий, Отец вечности, Князь мира.", "tags": ["christmas"]},
    {"text": "Иоанна 1:14: И Слово стало плотию, и обитало с нами, полное благодати и истины.", "tags": ["christmas"]},
    {"text": "Михея 5:2: И ты, Вифлеем, дом Евфрафов, мал ли ты между тысячами Иудиными? из тебя произойдет Мне Тот, Который должен быть Владыкою в Израиле.", "tags": ["christmas"]},
    {"text": "Луки 1:35: Дух Святый найдет на Тебя, и сила Всевышнего осенит Тебя; посему и рождаемое Святое наречется Сыном Божиим.", "tags": ["christmas"]},
    {"text": "Галатам 4:4-5: Когда наступила полнота времени, Бог послал Сына Своего, Который родился от жены, подчинился закону, чтобы искупить подзаконных.", "tags": ["christmas"]},

    # ---------- КРЕЩЕНИЕ (Богоявление) ----------
    {"text": "Матфея 3:16-17: И вот, отверзлись Ему небеса, и увидел Иоанн Духа Божия, Который сходил, как голубь, и ниспускался на Него. И се, глас с небес глаголющий: Сей есть Сын Мой Возлюбленный.", "tags": ["baptism"]},
    {"text": "Марка 1:10-11: Когда выходил из воды, увидел разверзающиеся небеса и Духа, как голубя, сходящего на Него. И глас был с небес: Ты Сын Мой Возлюбленный.", "tags": ["baptism"]},
    {"text": "Иоанна 1:32-34: Я видел Духа, сходящего с неба, как голубя, и пребывающего на Нем. И я видел и засвидетельствовал, что Сей есть Сын Божий.", "tags": ["baptism"]},
    {"text": "Титу 3:5-6: Он спас нас не по делам праведности, которые бы мы сотворили, а по Своей милости, банею возрождения и обновления Святым Духом.", "tags": ["baptism"]},
    {"text": "Римлянам 6:4: Мы погреблись с Ним крещением в смерть, дабы, как Христос воскрес из мертвых славою Отца, так и нам ходить в обновленной жизни.", "tags": ["baptism"]},

    # ---------- ВОЗНЕСЕНИЕ ----------
    {"text": "Деяния 1:9-11: Он поднялся в глазах их, и облако взяло Его из вида их. Сей Иисус, вознесшийся от вас на небо, придет таким же образом, как вы видели Его восходящим на небо.", "tags": ["ascension"]},
    {"text": "Марка 16:19: И так Господь, после беседования с ними, вознесся на небо и воссел одесную Бога.", "tags": ["ascension"]},
    {"text": "Луки 24:51: И когда благословлял их, стал отдаляться от них и возноситься на небо.", "tags": ["ascension"]},
    {"text": "Ефесянам 4:8-10: Восшед на высоту, пленил плен и дал дары человекам. Нисшедший Он же есть и восшедший превыше всех небес, дабы наполнить всё.", "tags": ["ascension"]},
    {"text": "Евреям 4:14: Итак, имея Первосвященника великого, прошедшего небеса, Иисуса Сына Божия, будем твердо держаться исповедания нашего.", "tags": ["ascension"]},

    # ---------- ТРОИЦА (Пятидесятница) ----------
    {"text": "Деяния 2:4: И исполнились все Духа Святаго, и начали говорить на иных языках, как Дух давал им провещевать.", "tags": ["trinity"]},
    {"text": "Иоанна 14:16-17: И Я умолю Отца, и даст вам другого Утешителя, да пребудет с вами вовек, Духа истины.", "tags": ["trinity"]},
    {"text": "Иоиль 2:28: И будет после того, излию от Духа Моего на всякую плоть, и будут пророчествовать сыны ваши и дочери ваши.", "tags": ["trinity"]},
    {"text": "Римлянам 5:5: Любовь Божия излилась в сердца наши Духом Святым, данным нам.", "tags": ["trinity"]},
    {"text": "2 Коринфянам 13:13: Благодать Господа нашего Иисуса Христа, и любовь Бога Отца, и общение Святаго Духа со всеми вами.", "tags": ["trinity"]},
    {"text": "Галатам 5:22-23: Плод же духа: любовь, радость, мир, долготерпение, благость, милосердие, вера, кротость, воздержание.", "tags": ["trinity"]},

    # ---------- ПРЕОБРАЖЕНИЕ ----------
    {"text": "Матфея 17:2: И преобразился пред ними: и просияло лице Его, как солнце, одежды же Его сделались белыми, как свет.", "tags": ["transfiguration"]},
    {"text": "Марка 9:2-3: И преобразился пред ними. Одежды Его сделались блистающими, весьма белыми, как снег, как на земле белильщик не может выбелить.", "tags": ["transfiguration"]},
    {"text": "Луки 9:29: И когда молился, вид лица Его изменился, и одежда Его сделалась белою, блистающею.", "tags": ["transfiguration"]},
    {"text": "2 Петра 1:17-18: Ибо Он принял от Бога Отца честь и славу, когда от велелепной славы донесся к Нему глас: Сей есть Сын Мой возлюбленный.", "tags": ["transfiguration"]},

    # ---------- ПРАЗДНИК ЖАТВЫ (Собирания плодов и благодарение) ----------
    {"text": "Исход 23:16: И праздник жатвы первых плодов труда твоего, что ты сеял на поле; и праздник собирания плодов в исходе года, когда уберешь с поля работу свою.", "tags": ["harvest"]},
    {"text": "Левит 23:39-40: А в пятнадцатый день седьмого месяца, когда вы собираете произведения земли, празднуйте праздник Господень семь дней: в первый день покой и в восьмой день покой. В первый день возьмите себе ветви красивых дерев, ветви пальмовые и ветви дерев широколиственных и верб речных, и веселитесь пред Господом Богом вашим семь дней.", "tags": ["harvest"]},
    {"text": "Второзаконие 16:13-15: Праздник кущей совершай у себя семь дней, когда уберешь с гумна твоего и из точила твоего. И веселись в праздник твой ты и сын твой, и дочь твоя, и раб твой, и раба твоя, и левит, и пришелец, и сирота, и вдова, которые в жилищах твоих. Семь дней празднуй Господу Богу твоему на месте, которое изберет Господь Бог твой; ибо благословит тебя Господь Бог твой во всех произведениях твоих и во всяком деле рук твоих, и ты будешь только веселиться.", "tags": ["harvest"]},
    {"text": "Псалом 126:5: Блажен человек, который наполнил колчан свой детьми! Не останутся они в стыде, когда будут говорить с врагами у ворот.", "tags": ["harvest"]},
    {"text": "Иоиль 2:23-24: И вы, чада Сиона, радуйтесь и веселитесь о Господе Боге вашем; ибо Он даст вам дождь в меру и будет ниспосылать вам дождь, дождь ранний и поздний, как прежде. И наполнятся гумна хлебом, и переполнятся точила виноградным соком и елеем.", "tags": ["harvest"]},
    {"text": "Захария 14:16-17: Затем все остальные из всех народов, приходивших против Иерусалима, будут приходить из года в год для поклонения Царю, Господу Саваофу, и для празднования праздника кущей. И будет: если какое из племен земных не пойдет в Иерусалим для поклонения Царю, Господу Саваофу, то не будет дождя у них.", "tags": ["harvest"]},
    {"text": "Псалом 64:10-13: Ты посещаешь землю и утучняешь её, обильно обогащаешь её: поток Божий полон воды; Ты приготовляешь хлеб, ибо так устроил её; напояешь борозды её, уравниваешь гряды её; размягчаешь её каплями дождя; благословляешь произрастания её. Венчаешь лето благости Твоей, и стези Твои источают тук; источают тук на обитаемые степи пустыни, и холмы препоясываются радостью; луга одеваются стадами, и долины покрываются хлебом; восклицают и поют.", "tags": ["harvest", "thanksgiving"]},
    {"text": "Псалом 67:10-11: Обильный дождь проливал Ты, Боже, на наследие Твоё, и когда оно изнемогало от жажды, Ты подкреплял его. Народ Твой обитал там; по благости Твоей, Боже, Ты ниспосылал обильный дождь для бедного.", "tags": ["harvest", "thanksgiving"]},
    {"text": "Псалом 85:12: Буду восхвалять Тебя, Господи, Боже мой, всем сердцем моим и славить имя Твоё вовек.", "tags": ["thanksgiving"]},
    {"text": "Псалом 106:1: Славьте Господа, ибо Он благ, ибо вовек милость Его.", "tags": ["thanksgiving"]},
    {"text": "Псалом 106:37-38: И засевают поля, и насаждают виноградники, которые приносят им обильные плоды. Он благословляет их, и они весьма размножаются, и скота их не умаляет.", "tags": ["harvest", "thanksgiving"]},
    {"text": "Псалом 113:25-26: Небо – небо Господу, а землю Он дал сынам человеческим. Не мёртвые восхвалят Господа, ни все нисходящие в могилу; но мы, живые, будем благословлять Господа отныне и вовек.", "tags": ["thanksgiving"]},
    {"text": "Псалом 135:25: Даёт хлеб всякой плоти; ибо вовек милость Его.", "tags": ["harvest", "thanksgiving"]},
    {"text": "Псалом 147:7-9: Славь, Иерусалим, Господа; хвали, Сион, Бога твоего; ибо Он укрепляет вереи ворот твоих, благословляет сынов твоих среди тебя; утверждает в пределах твоих мир и туком пшеницы насыщает тебя.", "tags": ["harvest", "thanksgiving"]},
    {"text": "Иеремия 5:24: И не скажут в сердце своём: «Убоимся Господа Бога нашего, Который даёт нам дождь ранний и поздний в своё время, хранит нам седмицы, назначенные для жатвы».", "tags": ["harvest"]},
    {"text": "Иоиль 2:26: И досыта будете есть, и насытитесь, и будете славить имя Господа Бога вашего, Который сотворит с вами дивное, и не посрамится народ Мой вовеки.", "tags": ["harvest", "thanksgiving"]},
    {"text": "Матфея 6:26: Взгляните на птиц небесных: они ни сеют, ни жнут, ни собирают в житницы; и Отец ваш Небесный питает их. Вы не гораздо ли лучше их?", "tags": ["harvest"]},
    {"text": "2 Коринфянам 9:10-11: Дающий же семя сеющему и хлеб в пищу подаст обилие посеянному вами и умножит плоды правды вашей, так чтобы вы всем богаты были на всякое благотворение.", "tags": ["harvest", "thanksgiving"]},
    {"text": "Колоссянам 3:17: И всё, что вы делаете словом или делом, всё делайте во имя Господа Иисуса Христа, благодаря через Него Бога и Отца.", "tags": ["thanksgiving"]},
    {"text": "1 Фессалоникийцам 5:16-18: Всегда радуйтесь. Непрестанно молитесь. За всё благодарите: ибо такова о вас воля Божия во Христе Иисусе.", "tags": ["thanksgiving"]},
]

BIRTHDAY_VERSES = [
    "🎂 С днём рождения! 🎉\n\nБлагословляю тебя в этот особенный день!\n\n«Да благословит тебя Господь и сохранит тебя! Да призрит на тебя Господь светлым лицем Своим и помилует тебя!» (Числа 6:24-26)\n\nПусть этот год принесёт много радости, мира и Божьей благодати! 🙏",
    "🎁 С днём рождения!\n\n«Ибо Я знаю намерения, какие имею о вас, говорит Господь, намерения во благо, а не на зло, чтобы дать вам будущность и надежду.» (Иеремия 29:11)\n\nПусть Бог исполнит все добрые намерения о тебе в этом году! ✨",
    "🌸 С днём рождения!\n\n«Благословлю Господа, вразумившего меня; даже и ночью учит меня внутренность моя. Всегда видел я пред собою Господа, ибо Он одесную меня; не поколеблюсь.» (Псалом 15:7-8)\n\nПусть Господь ведёт тебя каждый день этого года! 🤍",
]

def get_verse_for_user(user):
    family_status = user[4] if len(user) > 4 else ''
    children = user[5] if len(user) > 5 else ''
    
    tags = ['all']
    if family_status == 'Женат/Замужем':
        tags.append('married')
        tags.append('family')
    elif family_status == 'Не женат/Не замужем':
        tags.append('single')
    elif family_status == 'Разведён(а)':
        tags.append('single')
    if children == 'Есть дети':
        tags.append('children')
    
    # Определение праздников по дате
    today = datetime.now()
    is_harvest_day = False
    
    # Праздник жатвы — последнее воскресенье сентября
    if today.month == 9 and today.weekday() == 6:
        last_sunday = None
        for day in range(30, 23, -1):
            if datetime(today.year, 9, day).weekday() == 6:
                last_sunday = day
                break
        if last_sunday and today.day == last_sunday:
            is_harvest_day = True
            tags.append('harvest')
            tags.append('thanksgiving')
    
    # Другие праздники
    if today.month == 1 and today.day in (6, 7):
        tags.append('christmas')
    elif today.month == 1 and today.day == 19:
        tags.append('baptism')
    elif today.month == 4 and 1 <= today.day <= 10:
        tags.append('easter')
    elif today.month == 5 and 25 <= today.day <= 31:
        tags.append('ascension')
    elif today.month == 6 and 15 <= today.day <= 25:
        tags.append('trinity')
    elif today.month == 8 and today.day == 19:
        tags.append('transfiguration')
    
    # Если сегодня Праздник жатвы – отправляем два стиха
    if is_harvest_day:
        harvest_verses = [v['text'] for v in BIBLE_VERSES if 'harvest' in v['tags']]
        thanksgiving_verses = [v['text'] for v in BIBLE_VERSES if 'thanksgiving' in v['tags']]
        message = "🌾🎉 **Праздник жатвы!** 🎉🌾\n\n"
        if harvest_verses:
            message += f"📖 **О жатве:**\n{random.choice(harvest_verses)}\n\n"
        if thanksgiving_verses:
            message += f"🙏 **Благодарение:**\n{random.choice(thanksgiving_verses)}"
        return message
    
    # Обычный день – выбираем один стих по тегам
    suitable = [v for v in BIBLE_VERSES if any(tag in v['tags'] for tag in tags)]
    if not suitable:
        suitable = [v for v in BIBLE_VERSES if 'all' in v['tags']]
    return random.choice(suitable)['text']

# -------------------- ОБРАБОТЧИКИ АНКЕТЫ --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_exists(user_id):
        current_time = get_user_time(user_id)
        await update.message.reply_text(
            f"📖 Ты уже заполнил анкету!\n\n"
            f"⏰ Твоё текущее время получения стиха (по UTC): {current_time}\n\n"
            f"🔧 Что хочешь сделать?\n"
            f"• /edit – изменить данные анкеты\n"
            f"• /settime – изменить время получения стиха\n\n"
            f"🌟 Сегодняшний стих я пришлю тебе в 8:00 по твоему времени.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🙏 Привет! Я бот, который будет каждый день присылать тебе Слово из Библии.\n\n"
        "Давай познакомимся. Как тебя зовут?",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    reply_keyboard = [['Мужской', 'Женский']]
    await update.message.reply_text(
        "Укажи свой пол:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return GENDER

async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['gender'] = update.message.text
    await update.message.reply_text(
        "Укажи дату рождения в формате: ДД.ММ.ГГГГ\n\nНапример: 15.03.1990\n\nЭто нужно, чтобы я мог поздравить тебя с днём рождения 🎂",
        reply_markup=ReplyKeyboardRemove()
    )
    return BIRTHDATE

async def birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    birthdate_str = update.message.text.strip()
    try:
        birthdate = datetime.strptime(birthdate_str, '%d.%m.%Y')
        if birthdate > datetime.now():
            await update.message.reply_text("Дата рождения не может быть в будущем. Пожалуйста, введи корректную дату.")
            return BIRTHDATE
        context.user_data['birthdate'] = birthdate_str
    except ValueError:
        await update.message.reply_text("Неверный формат. Пожалуйста, введи дату в формате ДД.ММ.ГГГГ (например: 15.03.1990)")
        return BIRTHDATE
    reply_keyboard = [['Женат/Замужем', 'Не женат/Не замужем', 'Разведён(а)']]
    await update.message.reply_text(
        "Твоё семейное положение?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return FAMILY_STATUS

async def family_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['family_status'] = update.message.text
    reply_keyboard = [['Есть дети', 'Нет детей']]
    await update.message.reply_text(
        "Есть ли у тебя дети?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHILDREN

async def children(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['children'] = update.message.text
    await update.message.reply_text(
        "Из какого ты города? (например: Москва, Санкт-Петербург, Киев, Минск, Алматы)\n\n"
        "Это нужно, чтобы присылать стих ровно в 8 утра по твоему времени.",
        reply_markup=ReplyKeyboardRemove()
    )
    return LOCATION

async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['location'] = update.message.text
    user_id = update.effective_user.id
    save_user(
        user_id,
        context.user_data['name'],
        context.user_data['gender'],
        context.user_data['birthdate'],
        context.user_data['family_status'],
        context.user_data['children'],
        context.user_data['location']
    )
    age = calculate_age(context.user_data['birthdate'])
    offset = get_timezone_by_city(context.user_data['location'])
    offset_text = f"UTC+{offset}" if offset is not None and offset >= 0 else f"UTC{offset}" if offset is not None else "не определён (используется UTC+3)"
    verse = get_verse_for_user((
        user_id, context.user_data['name'], context.user_data['gender'],
        context.user_data['birthdate'], context.user_data['family_status'],
        context.user_data['children'], context.user_data['location']
    ))
    await update.message.reply_text(
        f"✅ Спасибо, {context.user_data['name']}! Анкета заполнена.\n\n"
        f"📍 Твой город: {context.user_data['location']}\n"
        f"🎂 Дата рождения: {context.user_data['birthdate']} ({age} лет)\n"
        f"🕐 Твой часовой пояс: {offset_text}\n"
        f"⏰ Я настроил отправку так, чтобы стих приходил в 8:00 по твоему времени.\n\n"
        f"📖 Вот твой первый стих:\n\n{verse}\n\n"
        f"🌟 Каждый день в 8:00 по твоему времени я буду присылать тебе Слово Божье.\n"
        f"🎂 А в твой день рождения тебя ждёт особое поздравление!\n\n"
        f"⏰ Чтобы изменить время, используй команду /settime\n"
        f"✏️ Чтобы изменить данные анкеты, используй /edit",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❌ Анкетирование отменено. Ты можешь начать заново командой /start.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# -------------------- РЕДАКТИРОВАНИЕ АНКЕТЫ --------------------
async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT name, gender, birthdate, family_status, children, location FROM users WHERE user_id = ?', (user_id,))
    user_data = c.fetchone()
    conn.close()
    if not user_data:
        await update.message.reply_text("❓ Ты ещё не заполнил анкету. Используй /start.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    context.user_data['old_name'], context.user_data['old_gender'], context.user_data['old_birthdate'], \
    context.user_data['old_family_status'], context.user_data['old_children'], context.user_data['old_location'] = user_data
    reply_keyboard = [
        ['📝 Имя', '🚻 Пол'],
        ['🎂 Дата рождения', '💑 Семейное положение'],
        ['👶 Дети', '📍 Город'],
        ['❌ Отмена']
    ]
    await update.message.reply_text(
        "✏️ Редактирование анкеты\n\n📋 Текущие данные:\n"
        f"• Имя: {user_data[0]}\n• Пол: {user_data[1]}\n• Дата рождения: {user_data[2]}\n"
        f"• Семейное положение: {user_data[3]}\n• Дети: {user_data[4]}\n• Город: {user_data[5]}\n\nЧто хочешь изменить?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return EDIT_CHOICE

async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == '❌ Отмена':
        await update.message.reply_text("❌ Редактирование отменено.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    if choice in ['📝 Имя', 'Имя']:
        await update.message.reply_text("✏️ Введи новое имя:", reply_markup=ReplyKeyboardRemove())
        return EDIT_NAME
    if choice in ['🚻 Пол', 'Пол']:
        reply_keyboard = [['Мужской', 'Женский']]
        await update.message.reply_text("✏️ Выбери новый пол:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return EDIT_GENDER
    if choice in ['🎂 Дата рождения', 'Дата рождения']:
        await update.message.reply_text("✏️ Введи новую дату рождения в формате ДД.ММ.ГГГГ:", reply_markup=ReplyKeyboardRemove())
        return EDIT_BIRTHDATE
    if choice in ['💑 Семейное положение', 'Семейное положение']:
        reply_keyboard = [['Женат/Замужем', 'Не женат/Не замужем', 'Разведён(а)']]
        await update.message.reply_text("✏️ Выбери новое семейное положение:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return EDIT_FAMILY_STATUS
    if choice in ['👶 Дети', 'Дети']:
        reply_keyboard = [['Есть дети', 'Нет детей']]
        await update.message.reply_text("✏️ Выбери новый статус детей:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return EDIT_CHILDREN
    if choice in ['📍 Город', 'Город']:
        await update.message.reply_text("✏️ Введи новый город:", reply_markup=ReplyKeyboardRemove())
        return EDIT_LOCATION
    await update.message.reply_text("⚠️ Пожалуйста, выбери пункт из меню.")
    return EDIT_CHOICE

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text
    user_id = update.effective_user.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET name = ? WHERE user_id = ?', (new_name, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Имя изменено на «{new_name}».")
    return ConversationHandler.END

async def edit_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_gender = update.message.text
    user_id = update.effective_user.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET gender = ? WHERE user_id = ?', (new_gender, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Пол изменён на «{new_gender}».", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def edit_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_birthdate = update.message.text.strip()
    try:
        datetime.strptime(new_birthdate, '%d.%m.%Y')
        user_id = update.effective_user.id
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('UPDATE users SET birthdate = ? WHERE user_id = ?', (new_birthdate, user_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Дата рождения изменена на {new_birthdate}.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи дату в формате ДД.ММ.ГГГГ")
        return EDIT_BIRTHDATE

async def edit_family_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_status = update.message.text
    user_id = update.effective_user.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET family_status = ? WHERE user_id = ?', (new_status, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Семейное положение изменено на «{new_status}».", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def edit_children(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_children = update.message.text
    user_id = update.effective_user.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET children = ? WHERE user_id = ?', (new_children, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Статус детей изменён на «{new_children}».", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def edit_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_location = update.message.text
    user_id = update.effective_user.id
    new_delivery_time = get_local_delivery_time(new_location)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET location = ?, delivery_time = ? WHERE user_id = ?', (new_location, new_delivery_time, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Город изменён на «{new_location}». Время доставки обновлено.")
    return ConversationHandler.END

async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Редактирование отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# -------------------- НАСТРОЙКА ВРЕМЕНИ --------------------
async def settime_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not user_exists(user_id):
        await update.message.reply_text("❓ Сначала заполни анкету командой /start", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    current_time = get_user_time(user_id)
    reply_keyboard = [
        ['06:00', '07:00', '08:00', '09:00'],
        ['10:00', '11:00', '12:00', '13:00'],
        ['14:00', '15:00', '16:00', '17:00'],
        ['18:00', '19:00', '20:00', '21:00'],
        ['❌ Отмена', '🔄 Сбросить на авто']
    ]
    await update.message.reply_text(
        f"⏰ Твоё текущее время получения стиха (по UTC): {current_time}\n\n"
        f"Выбери новое время (по UTC). Стих будет приходить каждый день в выбранный час UTC.\n\n"
        f"«Сбросить на авто» – вернуть автоматический расчёт (8:00 по твоему местному времени)",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SET_TIME

async def settime_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == '❌ Отмена':
        await update.message.reply_text("❌ Настройка времени отменена.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    if choice == '🔄 Сбросить на авто':
        user_id = update.effective_user.id
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT location FROM users WHERE user_id = ?', (user_id,))
        location = c.fetchone()[0]
        conn.close()
        auto_time = get_local_delivery_time(location)
        update_delivery_time(user_id, auto_time)
        await update.message.reply_text(f"✅ Время сброшено на автоматическое. Стих будет приходить в 8:00 по твоему местному времени.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    if ':' in choice and len(choice) == 5:
        hour, minute = choice.split(':')
        if hour.isdigit() and minute.isdigit() and 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59:
            user_id = update.effective_user.id
            update_delivery_time(user_id, choice)
            await update.message.reply_text(f"✅ Время получения стиха изменено на {choice} UTC.", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    await update.message.reply_text("⚠️ Пожалуйста, выбери время из предложенных вариантов.")
    return SET_TIME

async def settime_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Настройка времени отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# -------------------- ЕЖЕДНЕВНАЯ РАССЫЛКА --------------------
async def check_and_send(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    today_str = now.date().isoformat()
    users = get_all_users()
    for user in users:
        user_id = user[0]
        name = user[1]
        birthdate = user[3]
        delivery_time = user[7] if len(user) > 7 else '08:00'
        if current_time_str == delivery_time:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT last_bible_date FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            last_date = result[0] if result else None
            conn.close()
            if last_date != today_str:
                if is_birthday_today(birthdate):
                    age = calculate_age(birthdate)
                    birthday_text = random.choice(BIRTHDAY_VERSES)
                    message = f"🎉🎂 **С днём рождения, {name}!** 🎂🎉\n\n"
                    if age:
                        message += f"Тебе исполняется {age} лет! 🥳\n\n"
                    message += birthday_text
                    verse = message
                else:
                    verse = get_verse_for_user(user)
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🌟 Доброе утро!\n\n{verse}\n\n---\n⏰ Сменить время: /settime\n✏️ Изменить анкету: /edit"
                    )
                    update_last_bible_date(user_id, today_str)
                    logging.info(f"Стих отправлен пользователю {user_id} в {current_time_str} UTC")
                except Exception as e:
                    logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

# -------------------- ЗАПУСК БОТА --------------------
def main():
    init_db()
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender)],
            BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, birthdate)],
            FAMILY_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, family_status)],
            CHILDREN: [MessageHandler(filters.TEXT & ~filters.COMMAND, children)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    edit_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('edit', edit_start)],
        states={
            EDIT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_choice)],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            EDIT_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_gender)],
            EDIT_BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_birthdate)],
            EDIT_FAMILY_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_family_status)],
            EDIT_CHILDREN: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_children)],
            EDIT_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_location)],
        },
        fallbacks=[CommandHandler('cancel', edit_cancel)],
    )
    settime_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('settime', settime_start)],
        states={SET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, settime_set)]},
        fallbacks=[CommandHandler('cancel', settime_cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(edit_conv_handler)
    application.add_handler(settime_conv_handler)

    # Запускаем пинг-сервер для cron-job.org в отдельном потоке
    import threading
    ping_thread = threading.Thread(target=run_ping_server, daemon=True)
    ping_thread.start()

    print("🤖 Бот запущен...")
    application.run_polling(poll_interval=1, timeout=30)

# -------------------- ПРОСТАЯ СТРАНИЦА ДЛЯ ПИНГА --------------------
from http.server import HTTPServer, BaseHTTPRequestHandler

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_ping_server():
    port = 10000
    server = HTTPServer(('0.0.0.0', port), PingHandler)
    print(f"✅ Пинг-сервер запущен на порту {port}")
    server.serve_forever()

if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    main()
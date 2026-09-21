import psycopg as sql
from psycopg_pool import AsyncConnectionPool
import datetime
from dotenv import load_dotenv
import os

load_dotenv()

connection_string = os.getenv('SUPA_CONNECTION_STRING')
db_pool = AsyncConnectionPool(conninfo=connection_string,
                              open=False, 
                              min_size=1, 
                              max_size=10,
                              kwargs={"prepare_threshold": None}
                              )

async def setup_db():
   """Create attendance and session tables in supabase"""
   await db_pool.open()
   async with db_pool.connection() as conn:
        async with conn.cursor() as cursor:
            await  cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance 
                (id SERIAL PRIMARY KEY, 
                session_id TEXT NOT NULL,
                user_id BIGINT,
                name TEXT NOT NULL, 
                timestamp TEXT, 
                feedback TEXT,
                status TEXT NOT NULL)
                ''')
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS session
                (id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                is_active INTEGER,
                timestamp TEXT NOT NULL,
                coach_name TEXT,
                topic TEXT,
                coach_notes TEXT)
                ''')
            await conn.commit()
            print('Setup Complete')


async def attend(user_id, name, timestamp, feedback): 
    """Log valid attendance into the table, return whether or not the attendance attempt was valid"""
    async with db_pool.connection() as conn:
        session_id = await active_session(conn)
        if not session_id:
            return 'no prac'
        else:
            status = 'PRESENT'
        validation_status, validation_bool = await validate_attendance(conn, user_id, feedback, session_id)
        if not validation_bool:    
            return validation_status
        async with conn.cursor() as cursor:
            query = 'INSERT INTO attendance (user_id, name, timestamp, feedback, session_id, status) VALUES (%s, %s, %s, %s, %s, %s)'
            await cursor.execute(query, (user_id, name, timestamp, feedback, session_id, status))
            await conn.commit()  
            return validation_status

async def validate_attendance(conn, user_id, feedback, session_id):
    """Check whether the attendance attempt is a duplicate, or an excess attempt"""
    async with conn.cursor() as cursor:
        query = 'SELECT feedback FROM attendance WHERE user_id = %s ORDER BY id DESC LIMIT 1'
        await cursor.execute(query, (user_id,))
        last_row = await cursor.fetchone()
        if last_row and last_row[0] == feedback:
            return 'duplicate', False
        query = 'SELECT COUNT(id), session_id, user_id FROM attendance WHERE user_id = %s AND session_id = %s GROUP BY user_id, session_id'
        await cursor.execute(query, (user_id, session_id))
        submissions = await cursor.fetchone()
        if submissions and submissions[0] > 0:
            return 'excess', False
        return 'success', True

async def log_practice(term, type, is_active, timestamp, topic):
    """Log the session ID into the session table once a window is opened"""
    async with db_pool.connection() as conn:
        if await active_session(conn):
            return False
        async with conn.cursor() as cursor:
            session_id = await gen_session_id(term, type, conn)
            query = 'INSERT INTO session (session_id, is_active, timestamp, topic) VALUES (%s, %s, %s, %s)'
            await cursor.execute(query, (session_id, is_active, timestamp, topic)) 
            await conn.commit() 
            return True
         

async def gen_session_id(term, type, conn):
    """Generate a session ID from the coach input"""
    async with conn.cursor() as cursor:
        query = ('SELECT session_id FROM session WHERE session_id LIKE %s ORDER BY id DESC')
        await cursor.execute(query, (f'{term}_%',))
        prev_session_id = await cursor.fetchone()
        if not prev_session_id:
            return f'{term}_01_{type}'
        prev_increment = int(prev_session_id[0].split('_')[1]) + 1
        return f'{term}_{prev_increment:02d}_{type}'


async def active_session(conn):
    """If a session is active, returns the session_id"""
    async with conn.cursor() as cursor:
        await cursor.execute('SELECT session_id FROM session WHERE is_active = 1')
        active_row = await cursor.fetchone()
        if not active_row:
            return None
        return active_row[0]

async def log_notes(coach_name, coach_notes):
    """Logs a coach's notes into the session table, and closes the window"""
    async with db_pool.connection() as conn:
        if not await active_session(conn): 
            return False
        async with conn.cursor() as cursor:
            query = 'UPDATE session SET coach_name = %s, coach_notes = %s, is_active = 0 WHERE is_active = 1'
            await cursor.execute(query, (coach_name, coach_notes))
            await conn.commit()
            return True

async def absence_roundup():
    """Logs absent for all athletes who did not attend practice"""
    async with db_pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('SELECT DISTINCT user_id, name FROM attendance')
            roster = await cursor.fetchall()
            await cursor.execute('SELECT DISTINCT attendance.user_id, attendance.name FROM attendance JOIN session ON attendance.session_id = session.session_id WHERE is_active = 1')
            present = dict(await cursor.fetchall())
            await cursor.execute('SELECT session_id FROM session WHERE is_active = 1')
            session_id = await cursor.fetchone()
            query = ('INSERT INTO attendance (user_id, name, session_id, status) VALUES (%s, %s, %s, %s)')
            if session_id:
                for user_id, name in roster:
                    if user_id not in present:
                        await cursor.execute(query, (user_id, name, session_id[0], 'UNEXCUSED'))
                await conn.commit()

async def check_window(current):
    """Boolean check to see if a window has been active for longer than 3 hours"""
    async with db_pool.connection() as conn:
        async with conn.cursor() as cursor:
            session_id = await active_session(conn)
            if not session_id:
                return False
            await cursor.execute('SELECT timestamp FROM session WHERE session_id = %s', (session_id,))
            timestamp = await cursor.fetchone()
            prior = datetime.datetime.fromisoformat(timestamp[0])
            time_diff = current - prior
            if time_diff.total_seconds() > 30:
                return True
            return False

async def mean_count(timeframe, user_id, type):
    """Returns the number of attended practices, the total practices that have occurred since joining the team, and the total attendance percentage for a given athlete"""
    async with db_pool.connection() as conn:
        async with conn.cursor() as cursor:
            if '-' in timeframe:
                query = "SELECT COUNT(DISTINCT session_id) FROM attendance WHERE timestamp LIKE %s AND user_id = %s AND status IN ('PRESENT', 'EXCUSED') AND session_id LIKE %s"
                await cursor.execute(query, (f'{timeframe}%', user_id, f'%{type}%'))
                attended = await cursor.fetchone()
                attended = int(attended[0])
                query = 'SELECT COUNT(DISTINCT session_id) FROM attendance WHERE timestamp LIKE %s and user_id = %s AND session_id LIKE %s'
                await cursor.execute(query, (f'{timeframe}%', user_id, f'%{type}%'))
                total = await cursor.fetchone()
            elif timeframe == 'ALL':
                query = "SELECT COUNT(DISTINCT session_id) FROM attendance WHERE user_id = %s and STATUS IN ('PRESENT', 'EXCUSED') AND session_id LIKE %s"
                await cursor.execute(query, (user_id, f'%{type}%'))
                attended = await cursor.fetchone()
                attended = int(attended[0])
                query = 'SELECT COUNT(DISTINCT session_id) FROM attendance WHERE user_id = %s and session_id LIKE %s'
                await cursor.execute(query, (user_id, f'%{type}%'))
                total = await cursor.fetchone()
            else:
                query = "SELECT COUNT(DISTINCT session_id) FROM attendance WHERE session_id LIKE %s and user_id = %s AND STATUS IN ('PRESENT', 'EXCUSED') AND session_id LIKE %s"
                await cursor.execute(query, (f'{timeframe}%', user_id, f'%{type}%'))
                attended = await cursor.fetchone()
                attended = int(attended[0])
                query = 'SELECT COUNT(DISTINCT session_id) FROM attendance WHERE session_id LIKE %s and user_id = %s AND session_id LIKE %s'
                await cursor.execute(query, (f'{timeframe}%', user_id, f'%{type}%'))
                total = await cursor.fetchone()
            total = int(total[0])
            if total == 0:
                return 0, 0, '0%'
            attendance_percent = f'{round(attended/total, 2) * 100}%'
            return attended, total, attendance_percent

async def get_percentages(timeframe, user_id, type):
    """Returns a dictionary containing the attendance percent of an athlete throughout the year since joining the team"""
    async with db_pool.connection() as conn:
        async with conn.cursor() as cursor: 
            attended = 0
            percentages = {}
            if '-' in timeframe:
                query = "SELECT session_id FROM attendance WHERE timestamp LIKE %s and user_id = %s AND status IN ('PRESENT', 'EXCUSED') AND session_id LIKE %s GROUP BY session_id ORDER BY MIN(timestamp)"
                await cursor.execute(query, (f'{timeframe}%', user_id, f'%{type}%'))
                attended_sessions = await cursor.fetchall()
                query = "SELECT session_id FROM attendance WHERE timestamp LIKE %s AND user_id = %s AND session_id LIKE %s GROUP BY session_id ORDER BY MIN(timestamp)"
                await cursor.execute(query, (f'{timeframe}%', user_id, f'%{type}%'))
                total_sessions = await cursor.fetchall()
            elif timeframe == 'ALL':
                query = "SELECT session_id FROM attendance WHERE user_id = %s and STATUS IN ('PRESENT', 'EXCUSED') AND session_id LIKE %s GROUP BY session_id ORDER BY MIN(timestamp)"
                await cursor.execute(query, (user_id, f'%{type}%'))
                attended_sessions = await cursor.fetchall()
                query = 'SELECT session_id FROM attendance WHERE user_id = %s and session_id LIKE %s GROUP BY session_id ORDER BY MIN(timestamp)'
                await cursor.execute(query, (user_id, f'%{type}%'))
                total_sessions = await cursor.fetchall()
            else:
                query = "SELECT session_id FROM attendance where session_id LIKE %s and user_id = %s AND STATUS IN ('PRESENT', 'EXCUSED') AND session_id LIKE %s GROUP BY session_id ORDER BY MIN(timestamp)"
                await cursor.execute(query, (f'{timeframe}%', user_id, f'%{type}%'))
                attended_sessions = await cursor.fetchall()
                query = "SELECT session_id FROM attendance where session_id LIKE %s and user_id = %s AND session_id LIKE %s GROUP BY session_id ORDER BY MIN(timestamp)"
                await cursor.execute(query, (f'{timeframe}%', user_id, f'%{type}%'))
                total_sessions = await cursor.fetchall()
            for i in range(len(total_sessions)):
                if total_sessions[i] in attended_sessions:
                    attended += 1
                total = i + 1
                percent = attended/total * 100
                percentages[total_sessions[i][0]] = percent
            return percentages

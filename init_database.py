import sqlite3


def init_db():
    conn = sqlite3.connect('memory_store.db')
    cursor = conn.cursor()

    # Create main requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id TEXT PRIMARY KEY,
            raw_input TEXT,
            input_type TEXT,
            timestamp TEXT,
            classification TEXT,
            agent_results TEXT,
            actions TEXT,
            action_results TEXT
        )
    ''')

    # Create supporting tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_sample TEXT,
            classification_result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent TEXT,
            determined_actions TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_name TEXT,
            result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")
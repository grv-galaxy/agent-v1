import sqlite3
c = sqlite3.connect('C:/Users/kumar/Documents/agent-v1/backend/data/ltm_memory.db')
print([x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])

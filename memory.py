"""Lokales, dauerhaftes Gedächtnis (SQLite). Alles einsehbar und löschbar."""
import sqlite3
import threading
import time
from pathlib import Path

TABLES = ("facts", "notes", "todos", "feedback", "actions")
EXPECTED = ["id", "text", "extra", "ts"]


class Memory:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        try:
            self._open()
        except sqlite3.Error:
            # Defekte/fremde Datei: beiseitelegen und neu beginnen
            try:
                self.db.close()
            except Exception:
                pass
            self.path.replace(self.path.with_name(self.path.name + f".kaputt_{int(time.time())}"))
            self._open()

    def _open(self):
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        with self.lock:
            for t in TABLES:
                cols = [r[1] for r in self.db.execute(f"PRAGMA table_info({t})").fetchall()]
                if cols and cols != EXPECTED:
                    self.db.execute(f"ALTER TABLE {t} RENAME TO {t}_alt_{int(time.time())}")
                self.db.execute(
                    f"CREATE TABLE IF NOT EXISTS {t}("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, "
                    "extra INTEGER DEFAULT 0, ts REAL)"
                )
            self.db.commit()

    @staticmethod
    def _check(table):
        if table not in TABLES:
            raise ValueError("Unbekannte Tabelle")
        return table

    def add(self, table, text, extra=0):
        self._check(table)
        with self.lock:
            cur = self.db.execute(f"INSERT INTO {table}(text,extra,ts) VALUES(?,?,?)", (text.strip()[:2000], extra, time.time()))
            self.db.commit()
            return cur.lastrowid

    def list(self, table, limit=300):
        self._check(table)
        with self.lock:
            return self.db.execute(
                f"SELECT id,text,extra FROM {table} ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    def delete(self, table, row_id):
        self._check(table)
        with self.lock:
            self.db.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
            self.db.commit()

    def delete_like(self, table, needle):
        self._check(table)
        with self.lock:
            cur = self.db.execute(f"DELETE FROM {table} WHERE lower(text) LIKE ?", (f"%{needle.lower()}%",))
            self.db.commit()
            return cur.rowcount

    def search(self, table, needle):
        self._check(table)
        with self.lock:
            return self.db.execute(
                f"SELECT id,text,extra FROM {table} WHERE lower(text) LIKE ? ORDER BY id DESC LIMIT 20",
                (f"%{needle.lower()}%",),
            ).fetchall()

    def set_extra(self, table, row_id, value):
        self._check(table)
        with self.lock:
            self.db.execute(f"UPDATE {table} SET extra=? WHERE id=?", (value, row_id))
            self.db.commit()

    def clear(self, table=None):
        with self.lock:
            for t in ([self._check(table)] if table else TABLES):
                self.db.execute(f"DELETE FROM {t}")
            self.db.commit()

    # Bequemlichkeiten
    def facts(self):
        return [t for _, t, _ in self.list("facts", 50)]

    def open_todos(self):
        return [(i, t) for i, t, e in self.list("todos") if not e]

    def lessons(self, n=6):
        return [t for _, t, e in self.list("feedback", 30) if e == 0][:n]

    def log(self, text):
        self.add("actions", text)
        with self.lock:
            self.db.execute("DELETE FROM actions WHERE id NOT IN (SELECT id FROM actions ORDER BY id DESC LIMIT 300)")
            self.db.commit()

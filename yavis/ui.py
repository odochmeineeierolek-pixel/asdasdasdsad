"""Oberfläche im Stil des Entwurfs: Seitenleiste, Home, Chat mit Kreis, Projekte, Dateien, Wissen, Tools,
Automatisierungen, Einstellungen. Farben, Lautstärken, Sortierung und Kategorien sind frei einstellbar."""
import math
import os
import random
import sys
import tempfile
import threading
import urllib.request

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QColorDialog, QComboBox,
                               QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
                               QSlider, QSpinBox, QStackedWidget, QSystemTrayIcon, QTabWidget, QTextEdit,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import programs, voices
from .assistant import Assistant, Hooks
from .config import home_dir

ROLE = Qt.ItemDataRole.UserRole

PRESETS = {
    "Rot · Schwarz · Gelb": dict(accent="#ffd400", primary="#e10600", bg="#0a0a0a", panel="#121212", text="#f2f2f2"),
    "Blau · Cyan": dict(accent="#00e5ff", primary="#2962ff", bg="#080b12", panel="#0f1520", text="#eaf2ff"),
    "Grün · Lime": dict(accent="#b6ff00", primary="#00a651", bg="#07100a", panel="#0e1a12", text="#eafff0"),
    "Lila · Pink": dict(accent="#ff4fd8", primary="#7c3aed", bg="#0d0814", panel="#16101f", text="#f6eaff"),
    "Hell": dict(accent="#b45309", primary="#c62828", bg="#f4f1ea", panel="#ffffff", text="#1a1a1a"),
}

STYLE_TPL = """
QWidget{background:%(bg)s;color:%(text)s;font-family:'Segoe UI','Segoe UI Emoji';font-size:%(fs)dpx}
QLabel,QCheckBox{background:transparent}
QFrame#side{background:%(bg)s;border-right:1px solid %(border)s}
QFrame#header{background:%(bg)s;border-bottom:2px solid %(primary)s}
QFrame#panel,QFrame#card{background:%(panel)s;border:1px solid %(border)s;border-radius:12px}
QFrame#card:hover{border:1px solid %(accent)s}
QFrame#inputbox{background:%(panel)s;border:2px solid %(primary)s;border-radius:14px}
QPushButton{background:%(panel)s;border:1px solid %(border)s;color:%(accent)s;padding:7px 12px;border-radius:8px}
QPushButton:hover{background:%(primary)s;color:%(bg)s}
QPushButton#nav{border:1px solid transparent;text-align:left;padding:10px 14px;color:%(text)s;background:transparent}
QPushButton#nav:hover{background:%(panel)s;color:%(accent)s}
QPushButton#nav:checked{background:%(soft)s;border:1px solid %(accent)s;color:%(accent)s}
QPushButton#send{background:%(accent)s;color:%(bg)s;border-radius:18px;min-width:36px;max-width:36px;min-height:36px;max-height:36px;font-weight:bold}
QPushButton#stop{background:%(primary)s;color:%(bg)s;font-weight:bold}
QPushButton#link{border:none;background:transparent;color:%(accent)s;text-align:left;padding:4px}
QPushButton#row{text-align:left;color:%(text)s}
QLineEdit#bare{border:none;background:transparent;padding:6px}
QLineEdit,QTextEdit,QPlainTextEdit,QListWidget,QTreeWidget,QComboBox,QSpinBox{background:%(panel)s;border:1px solid %(border)s;border-radius:6px;padding:5px;selection-background-color:%(accent)s;selection-color:%(bg)s}
QTabWidget::pane{border:1px solid %(border)s;border-radius:8px}
QTabBar::tab{background:%(panel)s;color:%(accent)s;padding:8px 14px;border:1px solid %(border)s}
QTabBar::tab:selected{background:%(primary)s;color:%(bg)s;font-weight:bold}
QSlider::groove:horizontal{height:6px;background:%(border)s;border-radius:3px}
QSlider::handle:horizontal{background:%(accent)s;width:16px;margin:-6px 0;border-radius:8px}
QLabel#h1{font-size:%(h1)dpx;font-weight:bold}
QLabel#sect{font-weight:bold}
QLabel#muted{color:#9a9a9a}
QLabel#status{color:%(accent)s}
QLabel#mono{font-family:Consolas,monospace;font-size:12px;letter-spacing:1px}
QScrollArea{border:none}
"""

STATUS_TEXT = {"idle": "Bereit – sag „YAVIS“", "listening": "Ich höre zu …", "thinking": "Ich denke nach …",
               "speaking": "", "muted": "Mikrofon aus", "loading": "Lade Spracherkennung …", "error": "Fehler – siehe Verlauf"}
NAV = [("Home", "🏠"), ("Chat", "💬"), ("Projekte", "📁"), ("Dateien", "📄"), ("Wissen", "📖"), ("Tools", "🛠"),
       ("Automatisierungen", "⚡"), ("Einstellungen", "⚙")]


def build_style(t, fs):
    d = dict(t)
    d.update(fs=fs, h1=int(fs * 2.1), border=QColor(t["primary"]).darker(230).name(), soft=QColor(t["accent"]).darker(330).name())
    return STYLE_TPL % d


def contrast(c):
    return "#000000" if QColor(c).lightness() > 128 else "#ffffff"


def btn(text, fn, name=None):
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    b.clicked.connect(lambda _=False: fn())
    return b


def lab(text, name=None, wrap=False):
    l = QLabel(text)
    if name:
        l.setObjectName(name)
    l.setWordWrap(wrap)
    return l


def panel(title, edit_fn=None):
    f = QFrame()
    f.setObjectName("panel")
    lay = QVBoxLayout(f)
    head = QHBoxLayout()
    head.addWidget(lab(title, "sect"))
    head.addStretch(1)
    if edit_fn:
        head.addWidget(btn("Bearbeiten", edit_fn, "link"))
    lay.addLayout(head)
    return f, lay


def clear_layout(lay):
    while lay.count():
        it = lay.takeAt(0)
        if it.widget():
            it.widget().deleteLater()


def make_icon():
    pm = QPixmap(128, 128)
    pm.fill(QColor("#050505"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    for r, c in ((56, "#780000"), (44, "#e10600"), (28, "#ffd400")):
        p.setBrush(QColor(c))
        p.drawEllipse(QPointF(64, 64), r, r)
    p.end()
    return QIcon(pm)


class ClickFrame(QFrame):
    clicked = Signal()

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


class Orb(QWidget):
    def __init__(self, mini=False):
        super().__init__()
        self.mini = mini
        self.setMinimumSize(150, 150) if mini else self.setMinimumSize(320, 300)
        if mini:
            self.setFixedHeight(170)
        self.accent, self.primary, self.bg, self.scale = "#ffd400", "#e10600", "#0a0a0a", 1.0
        self.state, self.emotion = "idle", "neutral"
        self.level, self.ext, self.t, self.rot = 0.0, 0.0, 0.0, 0.0
        tm = QTimer(self)
        tm.timeout.connect(self._tick)
        tm.start(30)

    def set_theme(self, accent, primary, bg, scale):
        self.accent, self.primary, self.bg, self.scale = accent, primary, bg, scale

    def set_ext(self, v):
        self.ext = v

    def _colors(self):
        a, p = QColor(self.accent), QColor(self.primary)
        table = {"neutral": (a, p, p, a),
                 "nett": (a.lighter(140), a.darker(110), a, p.lighter(130)),
                 "boese": (QColor("#ff3300"), QColor("#6a0000"), QColor("#ff0000"), QColor("#a00000")),
                 "traurig": (a.darker(250), QColor("#2a0a0a"), p.darker(300), a.darker(250))}
        return table.get(self.emotion, table["neutral"])

    def _tick(self):
        self.t += 0.03
        speed = {"idle": 0.4, "listening": 0.9, "thinking": 2.4, "speaking": 1.3, "muted": 0.1}.get(self.state, 0.4)
        speed *= 1.8 if self.emotion == "boese" else 0.5 if self.emotion == "traurig" else 1
        self.rot = (self.rot + speed * 2) % 360
        if self.state == "speaking":
            target = 0.25 + 0.55 * abs(math.sin(self.t * 7.3)) * (0.6 + 0.4 * random.random())
        elif self.state == "thinking":
            target = 0.15 + 0.1 * math.sin(self.t * 6)
        elif self.state == "muted":
            target = 0.0
        else:
            target = 0.05 + 0.04 * math.sin(self.t * 1.5) + min(0.55, self.ext * 0.9)
        if self.emotion == "traurig":
            target *= 0.6
        self.level += (target - self.level) * 0.35
        if self.isVisible():
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        inner, outer, r1, r2 = self._colors()
        c = QPointF(self.width() / 2, self.height() / 2)
        base = min(self.width(), self.height()) * (0.17 if self.mini else 0.19) * self.scale
        r = base * (1 + 0.45 * self.level)
        g = QRadialGradient(c, r * 2.6)
        glow = QColor(outer)
        glow.setAlpha(150)
        g.setColorAt(0, glow)
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawEllipse(c, r * 2.6, r * 2.6)
        g2 = QRadialGradient(c - QPointF(r * 0.25, r * 0.25), r * 1.25)
        g2.setColorAt(0, inner)
        g2.setColorAt(0.65, outer)
        g2.setColorAt(1, QColor(self.bg))
        p.setBrush(g2)
        p.drawEllipse(c, r, r)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i, (scale, span, col, w, d) in enumerate(((1.35, 110, r1, 4, 1), (1.6, 70, r2, 3, -1), (1.9, 40, r1, 2, 1))):
            pen = QPen(col, 2 if self.mini else w)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            rr = base * scale * (1 + 0.25 * self.level)
            rect = QRectF(c.x() - rr, c.y() - rr, 2 * rr, 2 * rr)
            for k in range(3):
                p.drawArc(rect, int((self.rot * d + i * 40 + k * 120) * 16), int(span * 16))


class Bridge(QObject):
    log = Signal(str, str)
    state = Signal(str)
    emotion = Signal(str)
    level = Signal(float)
    notice = Signal(str)
    status = Signal(str)
    info = Signal(object)
    confirm = Signal(str, object)
    text_out = Signal(str)


class UiHooks(Hooks):
    def __init__(self, bridge):
        self.b = bridge

    def log(self, role, text): self.b.log.emit(role, text)
    def state(self, s): self.b.state.emit(s)
    def emotion(self, e): self.b.emotion.emit(e)
    def level(self, v): self.b.level.emit(float(v))
    def notice(self, kind): self.b.notice.emit(kind)

    def confirm(self, question):
        holder = {"ok": False, "ev": threading.Event()}
        self.b.confirm.emit(question, holder)
        holder["ev"].wait(90)
        return holder["ok"]


# ---------- Listen bearbeiten (Karten, Schnellzugriff, Automatisierungen) ----------
def edit_rows(parent, title, rows, fields):
    """rows: Liste von dicts, fields: [(key, Beschriftung)]. Gibt die neue Liste zurück oder None."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.resize(560, 420)
    rows = [dict(r) for r in rows]
    lay = QVBoxLayout(dlg)
    lst = QListWidget()
    lay.addWidget(lst)

    def show(sel=0):
        lst.clear()
        for r in rows:
            lst.addItem(" | ".join(str(r.get(k, "")) for k, _ in fields))
        if rows:
            lst.setCurrentRow(max(0, min(sel, len(rows) - 1)))

    def ask(r):
        out = {}
        for k, label in fields:
            v, ok = QInputDialog.getText(dlg, title, label + ":", text=str(r.get(k, "")))
            if not ok:
                return None
            out[k] = v
        return out

    def add():
        r = ask({})
        if r:
            rows.append(r)
            show(len(rows) - 1)

    def edit():
        i = lst.currentRow()
        if i >= 0:
            r = ask(rows[i])
            if r:
                rows[i] = r
                show(i)

    def delete():
        i = lst.currentRow()
        if i >= 0:
            rows.pop(i)
            show(i)

    def move(d):
        i = lst.currentRow()
        j = i + d
        if i >= 0 and 0 <= j < len(rows):
            rows[i], rows[j] = rows[j], rows[i]
            show(j)

    row = QHBoxLayout()
    for text, fn in (("Neu", add), ("Ändern", edit), ("Löschen", delete), ("▲", lambda: move(-1)), ("▼", lambda: move(1))):
        row.addWidget(btn(text, fn))
    lay.addLayout(row)
    row2 = QHBoxLayout()
    ok_b, no_b = QPushButton("Speichern"), QPushButton("Abbrechen")
    ok_b.clicked.connect(dlg.accept)
    no_b.clicked.connect(dlg.reject)
    row2.addWidget(ok_b)
    row2.addWidget(no_b)
    lay.addLayout(row2)
    show()
    return rows if dlg.exec() else None


# ---------- Kategorien-Baum mit Sortierung ----------
class ProgBackend:
    checkable = True

    def __init__(self, s):
        self.s = s

    def items(self):
        order = {i: n for n, i in enumerate(self.s.get("prog_order") or [])}
        entries = sorted(programs.all_entries(self.s), key=lambda e: order.get(e.id, 10000))
        allowed = programs.allowed_ids(self.s)
        return [dict(id=e.id, name=e.name, cat=programs.category_of(self.s, e), checked=e.id in allowed) for e in entries]

    def set_cat(self, i, c):
        d = self.s.get("prog_cat")
        d[i] = c
        self.s.set("prog_cat", d)

    def set_order(self, ids):
        self.s.set("prog_order", ids)

    def set_checked(self, ids):
        self.s.set("allowed_programs", ids)


class ProjBackend:
    checkable = False

    def __init__(self, s):
        self.s = s

    def items(self):
        return [dict(id=p["id"], name=p["name"], cat=p.get("cat", "Sonstiges")) for p in self.s.get("projects")]

    def _mod(self, fn):
        ps = self.s.get("projects")
        fn(ps)
        self.s.set("projects", ps)

    def set_cat(self, i, c):
        self._mod(lambda ps: [p.update(cat=c) for p in ps if p["id"] == i])

    def set_order(self, ids):
        self._mod(lambda ps: ps.sort(key=lambda p: ids.index(p["id"]) if p["id"] in ids else 10000))

    def set_checked(self, ids):
        pass

    def add(self, name, cat):
        nid = str(int.from_bytes(os.urandom(4), "big"))
        self._mod(lambda ps: ps.append(dict(id=nid, name=name, cat=cat, note="")))

    def rename(self, i, name):
        self._mod(lambda ps: [p.update(name=name) for p in ps if p["id"] == i])

    def remove(self, i):
        self._mod(lambda ps: ps.__setitem__(slice(None), [p for p in ps if p["id"] != i]))

    def get_note(self, i):
        return next((p.get("note", "") for p in self.s.get("projects") if p["id"] == i), "")

    def set_note(self, i, text):
        self._mod(lambda ps: [p.update(note=text) for p in ps if p["id"] == i])


class CatTree(QWidget):
    def __init__(self, backend, cats_key, settings, extra=()):
        super().__init__()
        self.b, self.key, self.s = backend, cats_key, settings
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(lab("Sortierung:"))
        self.sort = QComboBox()
        self.sort.addItems(["Eigene Reihenfolge", "A–Z"])
        self.sort.currentIndexChanged.connect(lambda _=0: self.refresh())
        top.addWidget(self.sort)
        top.addStretch(1)
        v.addLayout(top)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(self._changed)
        v.addWidget(self.tree, 1)
        row = QHBoxLayout()
        for text, fn in (("▲", lambda: self._move(-1)), ("▼", lambda: self._move(1)), ("Kategorie ändern …", self._set_cat),
                         ("Neue Kategorie …", self._new_cat), ("Kategorie löschen …", self._del_cat)):
            row.addWidget(btn(text, fn))
        v.addLayout(row)
        if extra:
            row2 = QHBoxLayout()
            for text, fn in extra:
                row2.addWidget(btn(text, fn))
            v.addLayout(row2)
        self.refresh()

    def cats(self):
        base = list(self.s.get(self.key))
        for it in self.b.items():
            if it["cat"] not in base:
                base.append(it["cat"])
        return base

    def refresh(self, keep=None):
        self.tree.blockSignals(True)
        self.tree.clear()
        items = self.b.items()
        if self.sort.currentIndex() == 1:
            items = sorted(items, key=lambda i: i["name"].lower())
        for c in self.cats():
            sub = [i for i in items if i["cat"] == c]
            top = QTreeWidgetItem([f"{c}  ({len(sub)})"])
            top.setData(0, ROLE, ("cat", c))
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            for i in sub:
                ch = QTreeWidgetItem([i["name"]])
                ch.setData(0, ROLE, ("item", i["id"]))
                if self.b.checkable:
                    ch.setFlags(ch.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    ch.setCheckState(0, Qt.CheckState.Checked if i.get("checked") else Qt.CheckState.Unchecked)
                top.addChild(ch)
                if keep == i["id"]:
                    self.tree.setCurrentItem(ch)
            top.setExpanded(True)
        self.tree.blockSignals(False)

    def selected(self):
        it = self.tree.currentItem()
        return (it, it.data(0, ROLE)) if it else (None, None)

    def selected_id(self):
        it, d = self.selected()
        return d[1] if d and d[0] == "item" else None

    def _changed(self, item, _col):
        if not self.b.checkable:
            return
        ids = []
        for n in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(n)
            for k in range(top.childCount()):
                ch = top.child(k)
                if ch.checkState(0) == Qt.CheckState.Checked:
                    ids.append(ch.data(0, ROLE)[1])
        self.b.set_checked(ids)

    def _move(self, d):
        it, data = self.selected()
        if not data:
            return
        if data[0] == "cat":
            cats = self.cats()
            i = cats.index(data[1])
            j = i + d
            if 0 <= j < len(cats):
                cats[i], cats[j] = cats[j], cats[i]
                self.s.set(self.key, cats)
                self.refresh()
            return
        if self.sort.currentIndex() == 1:
            self.sort.setCurrentIndex(0)  # auf eigene Reihenfolge wechseln, dann erneut drücken
            return
        parent = it.parent()
        n = parent.indexOfChild(it)
        m = n + d
        if 0 <= m < parent.childCount():
            ids = [parent.child(k).data(0, ROLE)[1] for k in range(parent.childCount())]
            ids[n], ids[m] = ids[m], ids[n]
            rest = [i["id"] for i in self.b.items() if i["id"] not in ids]
            self.b.set_order(ids + rest)
            self.refresh(keep=data[1])

    def _set_cat(self):
        i = self.selected_id()
        if not i:
            return
        c, ok = QInputDialog.getItem(self, "Kategorie", "Wählen oder neuen Namen tippen:", self.cats(), 0, True)
        if ok and c.strip():
            c = c.strip()
            cats = list(self.s.get(self.key))
            if c not in cats:
                self.s.set(self.key, cats + [c])
            self.b.set_cat(i, c)
            self.refresh(keep=i)

    def _new_cat(self):
        c, ok = QInputDialog.getText(self, "Neue Kategorie", "Name:")
        if ok and c.strip() and c.strip() not in self.cats():
            self.s.set(self.key, self.cats() + [c.strip()])
            self.refresh()

    def _del_cat(self):
        it, data = self.selected()
        if not data:
            return
        cat = data[1] if data[0] == "cat" else self.b.items()[0]["cat"]
        if data[0] == "item":
            cat = it.parent().data(0, ROLE)[1]
        cats = [c for c in self.cats() if c != cat]
        fallback = cats[0] if cats else "Sonstiges"
        if QMessageBox.question(self, "Kategorie löschen", f"„{cat}“ löschen? Einträge wandern nach „{fallback}“.") != QMessageBox.StandardButton.Yes:
            return
        for i in self.b.items():
            if i["cat"] == cat:
                self.b.set_cat(i["id"], fallback)
        self.s.set(self.key, cats or ["Sonstiges"])
        self.refresh()


class MainWindow(QMainWindow):
    def __init__(self, start_listener=True):
        super().__init__()
        self.setWindowTitle("YAVIS")
        self.setWindowIcon(make_icon())
        self.resize(1360, 860)
        self._quitting = False
        self.b = Bridge()
        self.a = Assistant(UiHooks(self.b))
        self.s = self.a.s
        self.b.log.connect(self.on_log)
        self.b.state.connect(self.on_state)
        self.b.emotion.connect(self.on_emotion)
        self.b.level.connect(self._level)
        self.b.notice.connect(self.on_notice)
        self.b.status.connect(lambda t: self.status.setText(t))
        self.b.info.connect(self._set_info)
        self.b.confirm.connect(self.on_confirm)
        self.b.text_out.connect(lambda t: self.sales_out.setPlainText(t))

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        right = QVBoxLayout()
        right.setSpacing(0)
        right.addWidget(self._build_header())
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        root.addLayout(right, 1)
        for fn in (self.page_home, self.page_chat, self.page_projects, self.page_files, self.page_knowledge,
                   self.page_tools, self.page_macros, self.page_settings):
            self.stack.addWidget(fn())
        self.nav_buttons[0].setChecked(True)
        self.apply_theme()
        self._tray()
        self._refresh_recent()
        self._refresh_home_projects()
        self.poll = QTimer(self)
        self.poll.timeout.connect(self._poll)
        self.poll.start(8000)
        if start_listener:
            self._poll()
            if self.s.get("always_listen"):
                self.a.start_listening()
            QTimer.singleShot(1500, lambda: threading.Thread(target=self._check_brain, daemon=True).start())

    # ---------- Grundgerüst ----------
    def _build_sidebar(self):
        f = QFrame()
        f.setObjectName("side")
        f.setFixedWidth(240)
        v = QVBoxLayout(f)
        self.mini = Orb(mini=True)
        v.addWidget(self.mini)
        name = lab("YAVIS", "h1")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(name)
        self.nav_buttons = []
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        for i, (text, icon) in enumerate(NAV):
            b = QPushButton(f"{icon}  {text}")
            b.setObjectName("nav")
            b.setCheckable(True)
            grp.addButton(b, i)
            v.addWidget(b)
            self.nav_buttons.append(b)
        grp.idClicked.connect(lambda i: self.stack.setCurrentIndex(i))
        v.addStretch(1)
        q = lab("„Große Ideen entstehen nicht im Alleingang – sondern mit den richtigen Werkzeugen.“", "muted", True)
        v.addWidget(q)
        return f

    def _build_header(self):
        f = QFrame()
        f.setObjectName("header")
        h = QHBoxLayout(f)
        self.tagline = lab("", "mono")
        self.tagline.setTextFormat(Qt.TextFormat.RichText)
        h.addWidget(self.tagline)
        h.addStretch(1)
        self.model_lbl = lab("● " + self.s.get("model"))
        h.addWidget(self.model_lbl)
        h.addWidget(lab("🔊"))
        self.hdr_vol = QSlider(Qt.Orientation.Horizontal)
        self.hdr_vol.setRange(0, 100)
        self.hdr_vol.setFixedWidth(130)
        self.hdr_vol.setValue(int(self.s.get("voice_volume")))
        self.hdr_vol.valueChanged.connect(self._vv)
        h.addWidget(self.hdr_vol)
        h.addWidget(btn("⚙", lambda: self._goto(7)))
        return f

    def _goto(self, i):
        self.nav_buttons[i].setChecked(True)
        self.stack.setCurrentIndex(i)

    # ---------- Seiten ----------
    def page_home(self):
        w = QWidget()
        h = QHBoxLayout(w)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        v = QVBoxLayout(inner)
        self.greet = lab("", "h1")
        self.greet.setTextFormat(Qt.TextFormat.RichText)
        self.greet.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.greet)
        sub = lab("Was möchtest du heute erledigen?")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(sub)
        box = QFrame()
        box.setObjectName("inputbox")
        bl = QVBoxLayout(box)
        self.home_in = QLineEdit()
        self.home_in.setObjectName("bare")
        self.home_in.setPlaceholderText("Stelle eine Frage, gib mir eine Aufgabe oder sag „YAVIS …“")
        self.home_in.returnPressed.connect(self._home_send)
        bl.addWidget(self.home_in)
        r = QHBoxLayout()
        r.addWidget(btn("🎤 Zuhören", self.a.activate))
        r.addWidget(btn("🌐 Websuche", self._home_search))
        r.addStretch(1)
        send = btn("➤", self._home_send, "send")
        r.addWidget(send)
        bl.addLayout(r)
        v.addWidget(box)
        head = QHBoxLayout()
        head.addWidget(lab("✨ Beliebte Aufgaben", "sect"))
        head.addStretch(1)
        head.addWidget(btn("Bearbeiten", self._edit_cards, "link"))
        v.addLayout(head)
        self.cards_grid = QGridLayout()
        v.addLayout(self.cards_grid)
        self._fill_cards()
        v.addWidget(lab("🕘 Zuletzt verwendet", "sect"))
        pf, self.recent_lay = panel("")
        v.addWidget(pf)
        v.addStretch(1)
        scroll.setWidget(inner)
        h.addWidget(scroll, 1)
        side = QWidget()
        side.setFixedWidth(330)
        sv = QVBoxLayout(side)
        qf, self.quick_lay = panel("⚡ Schnellzugriff", self._edit_quick)
        sv.addWidget(qf)
        self._fill_quick()
        pj, self.hproj_lay = panel("📁 Projekte")
        pj.layout().itemAt(0).layout().addWidget(btn("Alle anzeigen →", lambda: self._goto(2), "link"))
        sv.addWidget(pj)
        sf, sl = panel("🟢 Systemstatus")
        self.info_lbls = {}
        for key, text in (("ollama", "KI-Modell (Ollama)"), ("mic", "Mikrofon"), ("tts", "Sprachausgabe"), ("net", "Internet")):
            row = QHBoxLayout()
            row.addWidget(lab(text))
            row.addStretch(1)
            val = lab("…", "status")
            self.info_lbls[key] = val
            row.addWidget(val)
            sl.addLayout(row)
        sv.addWidget(sf)
        sv.addStretch(1)
        h.addWidget(side)
        return w

    def page_chat(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.orb = Orb()
        v.addWidget(self.orb, 1)
        self.status = lab(STATUS_TEXT["idle"], "status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.status)
        row = QHBoxLayout()
        self.btn_mic = QPushButton("🎤 Mikrofon an")
        self.btn_mic.setCheckable(True)
        self.btn_mic.setChecked(True)
        self.btn_mic.toggled.connect(self._mic_toggled)
        row.addWidget(self.btn_mic)
        row.addWidget(btn("Jetzt zuhören", self.a.activate))
        row.addWidget(btn("■ STOPP", self.a.stop, "stop"))
        row.addWidget(btn("👍", lambda: self.a.feedback(True)))
        row.addWidget(btn("👎", self._thumb_down))
        v.addLayout(row)
        self.logbox = QPlainTextEdit()
        self.logbox.setReadOnly(True)
        self.logbox.setMaximumHeight(200)
        v.addWidget(self.logbox)
        inp = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Oder hier schreiben …")
        self.inp.returnPressed.connect(self._send)
        inp.addWidget(self.inp)
        inp.addWidget(btn("Senden", self._send))
        v.addLayout(inp)
        return w

    def page_projects(self):
        w = QWidget()
        h = QHBoxLayout(w)
        self.proj = ProjBackend(self.s)
        self.ptree2 = CatTree(self.proj, "project_categories", self.s,
                              extra=[("Neues Projekt …", self._proj_add), ("Umbenennen …", self._proj_rename), ("Löschen", self._proj_del)])
        self.ptree2.tree.currentItemChanged.connect(lambda *_: self._proj_select())
        h.addWidget(self.ptree2, 1)
        right = QVBoxLayout()
        right.addWidget(lab("Notizen zum Projekt", "sect"))
        self.proj_note = QTextEdit()
        self.proj_note.textChanged.connect(self._proj_note_changed)
        right.addWidget(self.proj_note, 1)
        h.addLayout(right, 1)
        self._proj_cur = None
        return w

    def page_files(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(lab("Datei suchen (Desktop, Dokumente, Downloads)", "sect"))
        row = QHBoxLayout()
        self.file_in = QLineEdit()
        self.file_in.setPlaceholderText("Dateiname …")
        self.file_in.returnPressed.connect(self._file_search)
        row.addWidget(self.file_in)
        row.addWidget(btn("Suchen", self._file_search))
        v.addLayout(row)
        v.addWidget(lab("Ordner öffnen", "sect"))
        grid = QGridLayout()
        for n, (text, sub) in enumerate((("Downloads", "Downloads"), ("Dokumente", "Documents"), ("Desktop", "Desktop"),
                                         ("Bilder", "Pictures"), ("Musik", "Music"), ("Videos", "Videos"))):
            grid.addWidget(btn("📁 " + text, lambda s_=sub: self._open_folder(s_)), n // 3, n % 3)
        v.addLayout(grid)
        v.addStretch(1)
        return w

    def page_knowledge(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.cmb_mem = QComboBox()
        for text, tb in (("Gemerkte Fakten", "facts"), ("Notizen", "notes"), ("Aufgaben", "todos"),
                         ("Feedback / Lektionen", "feedback"), ("Eingaben & Protokoll", "actions")):
            self.cmb_mem.addItem(text, tb)
        self.cmb_mem.currentIndexChanged.connect(lambda _=0: self._refresh_mem())
        v.addWidget(self.cmb_mem)
        self.mlist = QListWidget()
        self.mlist.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        v.addWidget(self.mlist)
        row = QHBoxLayout()
        for text, fn in (("Neu laden", self._refresh_mem), ("Auswahl löschen", self._del_mem), ("Diese Liste leeren", self._clear_mem),
                         ("ALLES löschen", self._clear_all_mem)):
            row.addWidget(btn(text, fn))
        v.addLayout(row)
        v.addWidget(lab("Gespeichert wird nur, was du sagst („Merk dir …“, „Notiere …“) oder bewertest. Alles bleibt lokal.", "muted", True))
        self._refresh_mem()
        return w

    def page_tools(self):
        tabs = QTabWidget()
        self.ptree = CatTree(ProgBackend(self.s), "prog_categories", self.s,
                             extra=[("Alle erlauben", lambda: self._set_all(True)), ("Keine erlauben", lambda: self._set_all(False)),
                                    ("Startmenü durchsuchen …", self._scan_menu), ("Datei/Spiel hinzufügen …", self._add_custom),
                                    ("Eigenes entfernen", self._remove_custom), ("Test-Start", self._test_start)])
        pw = QWidget()
        pl = QVBoxLayout(pw)
        pl.addWidget(lab("Haken = YAVIS darf dieses Programm starten. Sortieren und Kategorien wie du willst.", "muted", True))
        pl.addWidget(self.ptree)
        tabs.addTab(pw, "Programme")
        tabs.addTab(self._tab_music(), "Musik")
        tabs.addTab(self._tab_sales(), "Verkauf")
        return tabs

    def _tab_music(self):
        w = QWidget()
        v = QVBoxLayout(w)
        top = QHBoxLayout()
        self.lbl_folder = lab(self.s.get("music_folder") or "Kein Musikordner gewählt")
        top.addWidget(self.lbl_folder, 1)
        top.addWidget(btn("Musikordner wählen …", self._pick_music))
        v.addLayout(top)
        self.tracklist = QListWidget()
        self.tracklist.itemDoubleClicked.connect(lambda it: self.a.music.play(self.tracklist.row(it)))
        v.addWidget(self.tracklist)
        row = QHBoxLayout()
        m = self.a.music
        for text, fn in (("⏮", m.prev), ("▶ Abspielen", lambda: m.play(self.tracklist.currentRow() if self.tracklist.currentRow() >= 0 else None)),
                         ("⏸", m.pause), ("⏯ Weiter", m.resume), ("⏭", m.next), ("■", m.stop)):
            row.addWidget(btn(text, fn))
        v.addLayout(row)
        if self.s.get("music_folder"):
            self._reload_tracks()
        return w

    def _tab_sales(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(lab("Verkaufshilfe: Texte vorbereiten. Veröffentlichen, Kaufen, Bezahlen, Senden machst du selbst.", "muted", True))
        self.sales_in = QTextEdit()
        self.sales_in.setPlaceholderText("Produktdaten oder Kunde/Leistung eintragen …")
        self.sales_in.setMaximumHeight(130)
        v.addWidget(self.sales_in)
        row = QHBoxLayout()
        for text, tpl in (("Beschreibung erstellen", "Schreibe eine ehrliche, ansprechende Verkaufsbeschreibung (max. 6 Sätze) für:\n{}"),
                          ("Angebot entwerfen", "Entwirf ein höfliches Angebot mit Preis-Platzhaltern für:\n{}"),
                          ("Kleinanzeigen-Text", "Schreibe einen Titel (max. 60 Zeichen) und einen kurzen Text für eine Kleinanzeige zu:\n{}")):
            row.addWidget(btn(text, lambda t=tpl: self._gen(t)))
        row.addWidget(btn("Preise im Browser prüfen", self._prices))
        v.addLayout(row)
        self.sales_out = QTextEdit()
        v.addWidget(self.sales_out, 1)
        return w

    def page_macros(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(lab("Eigene Befehle: ein Satz startet mehrere Programme/Seiten auf einmal. "
                        "Beispiel: Satz „arbeitsmodus“ → „chrome, word, spotify“.", "muted", True))
        self.mlist2 = QListWidget()
        v.addWidget(self.mlist2)
        row = QHBoxLayout()
        row.addWidget(btn("Bearbeiten …", self._edit_macros))
        row.addWidget(btn("Testen", self._test_macro))
        v.addLayout(row)
        self._fill_macros()
        return w

    def page_settings(self):
        tabs = QTabWidget()
        tabs.addTab(self._tab_design(), "Design")
        tabs.addTab(self._tab_audio(), "Stimme & Lautstärke")
        tabs.addTab(self._tab_names(), "Namen & Anrede")
        tabs.addTab(self._tab_system(), "KI & System")
        return tabs

    def _tab_design(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(lab("Farbschema", "sect"))
        self.cmb_preset = QComboBox()
        self.cmb_preset.addItem("Eigenes …")
        self.cmb_preset.addItems(list(PRESETS))
        self.cmb_preset.activated.connect(self._preset)
        v.addWidget(self.cmb_preset)
        self.color_btns = {}
        for key, label in (("accent", "Akzentfarbe (Gelb)"), ("primary", "Hauptfarbe (Rot)"), ("bg", "Hintergrund"),
                           ("panel", "Karten & Felder"), ("text", "Textfarbe")):
            row = QHBoxLayout()
            row.addWidget(lab(label))
            row.addStretch(1)
            b = QPushButton()
            b.setFixedWidth(130)
            b.clicked.connect(lambda _=False, k=key: self._pick_color(k))
            self.color_btns[key] = b
            row.addWidget(b)
            v.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(lab("Schriftgröße"))
        sp = QSpinBox()
        sp.setRange(11, 22)
        sp.setValue(int(self.s.get("font_size")))
        sp.valueChanged.connect(lambda x: (self.s.set("font_size", x), self.apply_theme()))
        row.addWidget(sp)
        v.addLayout(row)
        v.addWidget(lab("Größe des Kreises (%)"))
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(50, 150)
        sl.setValue(int(self.s.get("orb_scale")))
        sl.valueChanged.connect(lambda x: (self.s.set("orb_scale", x), self.apply_theme()))
        v.addWidget(sl)
        v.addWidget(btn("Standard-Design wiederherstellen", lambda: self._preset_by_name("Rot · Schwarz · Gelb")))
        v.addStretch(1)
        return w

    def _tab_audio(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(lab("Lautstärke Stimme"))
        self.vol_voice = QSlider(Qt.Orientation.Horizontal)
        self.vol_voice.setRange(0, 100)
        self.vol_voice.setValue(int(self.s.get("voice_volume")))
        self.vol_voice.valueChanged.connect(self._vv)
        v.addWidget(self.vol_voice)
        v.addWidget(lab("Lautstärke Musik"))
        mv = QSlider(Qt.Orientation.Horizontal)
        mv.setRange(0, 100)
        mv.setValue(int(self.s.get("volume")))
        mv.valueChanged.connect(self.a.music.set_volume)
        v.addWidget(mv)
        v.addWidget(lab(f"Stimme ({len(voices.VOICES)} Voreinstellungen: Frau / Mann, warm, samtig, Mama, hart …)"))
        cmb = QComboBox()
        for vo in voices.VOICES:
            cmb.addItem(("♀ " if vo.gender == "f" else "♂ ") + vo.label, vo.id)
        cmb.setCurrentIndex(max(0, cmb.findData(self.s.get("voice"))))
        cmb.currentIndexChanged.connect(lambda _=0: self.s.set("voice", cmb.currentData()))
        v.addWidget(cmb)
        for label, key, lo, hi in (("Tempo (%)", "voice_rate", -40, 40), ("Tonhöhe (Hz)", "voice_pitch", -30, 30)):
            v.addWidget(lab(label))
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(int(self.s.get(key)))
            sl.valueChanged.connect(lambda val, k=key: self.s.set(k, val))
            v.addWidget(sl)
        v.addWidget(lab("Gefühle"))
        mood = QComboBox()
        for text, key in (("Automatisch (nett / traurig / böse je nach Lage)", "auto"), ("Immer neutral", "neutral"),
                          ("Immer nett & lieb", "nett"), ("Immer böse", "boese"), ("Immer traurig", "traurig")):
            mood.addItem(text, key)
        mood.setCurrentIndex(max(0, mood.findData(self.s.get("mood"))))
        mood.currentIndexChanged.connect(lambda _=0: self.s.set("mood", mood.currentData()))
        v.addWidget(mood)
        off = QCheckBox("Nur Windows-Offline-Stimme verwenden (kein Internet, klingt einfacher)")
        off.setChecked(bool(self.s.get("offline_voice")))
        off.toggled.connect(lambda c: self.s.set("offline_voice", c))
        v.addWidget(off)
        v.addWidget(btn("Stimme anhören", lambda: self.a.say(f"Hallo {self.a.title}, so klinge ich. Gefällt dir das?", "nett", log=False)))
        v.addStretch(1)
        return w

    def _tab_names(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(lab("Aktivierungswörter – YAVIS hört auf jedes (ein Wort, mind. 3 Buchstaben):", "sect"))
        self.wlist = QListWidget()
        self.wlist.addItems(self.s.get("wake_words"))
        v.addWidget(self.wlist)
        row = QHBoxLayout()
        self.wedit = QLineEdit()
        self.wedit.setPlaceholderText("Neuer Name …")
        row.addWidget(self.wedit)
        row.addWidget(btn("Hinzufügen", self._add_wake))
        row.addWidget(btn("Entfernen", self._rem_wake))
        v.addLayout(row)
        v.addWidget(lab("Anrede (Standard: Master):"))
        t = QLineEdit(self.s.get("user_title"))
        t.textChanged.connect(lambda x: (self.s.set("user_title", x.strip() or "Master"), self._update_greet()))
        v.addWidget(t)
        v.addStretch(1)
        return w

    def _tab_system(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(lab("Sprachmodell (Ollama, lokal & kostenlos)", "sect"))
        self.ed_model = QLineEdit(self.s.get("model"))
        self.ed_model.editingFinished.connect(self._model_changed)
        v.addWidget(self.ed_model)
        row = QHBoxLayout()
        row.addWidget(btn("Ollama installieren", self._install_ollama))
        row.addWidget(btn("Modell herunterladen", self._pull_model))
        row.addWidget(btn("Verbindung testen", lambda: threading.Thread(target=self._check_brain, args=(True,), daemon=True).start()))
        v.addLayout(row)
        v.addWidget(lab("Spracherkennung (Whisper): größer = genauer, aber langsamer (Neustart nötig)"))
        cw = QComboBox()
        cw.addItems(["tiny", "base", "small", "medium"])
        cw.setCurrentText(self.s.get("whisper_model"))
        cw.currentTextChanged.connect(lambda t: self.s.set("whisper_model", t))
        v.addWidget(cw)
        al = QCheckBox("Dauerhaft auf Aktivierungswort hören (Mikrofon-Status immer sichtbar)")
        al.setChecked(bool(self.s.get("always_listen")))
        al.toggled.connect(lambda c: self.s.set("always_listen", c))
        v.addWidget(al)
        au = QCheckBox("YAVIS mit Windows starten (im Hintergrund, Tray-Symbol)")
        au.setChecked(self._autostart_get())
        au.toggled.connect(self._autostart_set)
        v.addWidget(au)
        v.addWidget(lab(f"Daten liegen lokal in: {home_dir()}", "muted", True))
        v.addStretch(1)
        return w

    # ---------- Theme ----------
    def apply_theme(self):
        t, fs = self.s.get("theme"), int(self.s.get("font_size"))
        self.setStyleSheet(build_style(t, fs))
        scale = int(self.s.get("orb_scale")) / 100
        for o in (self.orb, self.mini):
            o.set_theme(t["accent"], t["primary"], t["bg"], scale)
        self.tagline.setText(f'DEIN KI-ASSISTENT.<br>DENKT MIT. <span style="color:{t["primary"]}">HILFT.</span> '
                             f'<span style="color:{t["accent"]}">SCHAFFT.</span>')
        for k, b in self.color_btns.items():
            b.setText(t[k].upper())
            b.setStyleSheet(f"background:{t[k]};color:{contrast(t[k])};border:1px solid #888")
        self._update_greet()

    def _update_greet(self):
        t = self.s.get("theme")
        self.greet.setText(f'Hallo, {self.s.get("user_title")}! Ich bin <span style="color:{t["primary"]}">YAVIS</span><span style="color:{t["accent"]}">.</span>')

    def _pick_color(self, key):
        t = self.s.get("theme")
        c = QColorDialog.getColor(QColor(t[key]), self, "Farbe wählen")
        if c.isValid():
            t[key] = c.name()
            self.s.set("theme", t)
            self.apply_theme()

    def _preset(self, idx):
        if idx > 0:
            self._preset_by_name(self.cmb_preset.itemText(idx))

    def _preset_by_name(self, name):
        self.s.set("theme", dict(PRESETS[name]))
        self.apply_theme()

    def _vv(self, val):
        self.s.set("voice_volume", val)
        for sl in (self.hdr_vol, self.vol_voice):
            if sl.value() != val:
                sl.blockSignals(True)
                sl.setValue(val)
                sl.blockSignals(False)

    # ---------- Home ----------
    def _fill_cards(self):
        clear_layout(self.cards_grid)
        for n, c in enumerate(self.s.get("task_cards")):
            card = ClickFrame()
            card.setObjectName("card")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            l = QVBoxLayout(card)
            l.addWidget(lab(c.get("title", ""), "sect"))
            l.addWidget(lab(c.get("desc", ""), "muted", True))
            card.clicked.connect(lambda p=c.get("prompt", ""): self._run_or_fill(p))
            self.cards_grid.addWidget(card, n // 2, n % 2)

    def _fill_quick(self):
        clear_layout(self.quick_lay)
        head = lab("")
        for q in self.s.get("quick"):
            self.quick_lay.addWidget(btn(q.get("name", ""), lambda c=q.get("cmd", ""): self._run_or_fill(c), "row"))

    def _run_or_fill(self, cmd):
        if not cmd.strip():
            self._goto(1)
        elif cmd.endswith((" ", ":")):
            self.home_in.setText(cmd)
            self.home_in.setFocus()
        else:
            self.a.submit(cmd)

    def _edit_cards(self):
        rows = edit_rows(self, "Aufgaben-Karten", self.s.get("task_cards"),
                         [("title", "Titel"), ("desc", "Beschreibung"), ("prompt", "Befehl/Vorlage (endet mit Leerzeichen = wird ergänzt)")])
        if rows is not None:
            self.s.set("task_cards", rows)
            self._fill_cards()

    def _edit_quick(self):
        rows = edit_rows(self, "Schnellzugriff", self.s.get("quick"), [("name", "Name"), ("cmd", "Befehl (z. B. öffne youtube)")])
        if rows is not None:
            self.s.set("quick", rows)
            self._fill_quick()

    def _home_send(self):
        t = self.home_in.text().strip()
        if t:
            self.home_in.clear()
            self.a.submit(t)

    def _home_search(self):
        t = self.home_in.text().strip()
        if t:
            self.home_in.clear()
            self.a.submit("recherchiere " + t)

    def _refresh_recent(self):
        clear_layout(self.recent_lay)
        rows = [t[9:] for _, t, _ in self.a.mem.list("actions", 80) if t.startswith("Eingabe: ")][:5]
        if not rows:
            self.recent_lay.addWidget(lab("Noch nichts – sag oder schreibe etwas.", "muted"))
        for r in rows:
            self.recent_lay.addWidget(btn("💬  " + r, lambda x=r: self.a.submit(x), "row"))

    def _refresh_home_projects(self):
        clear_layout(self.hproj_lay)
        ps = self.s.get("projects")[:4]
        if not ps:
            self.hproj_lay.addWidget(lab("Noch keine Projekte.", "muted"))
        for p in ps:
            self.hproj_lay.addWidget(lab(f"📁 {p['name']}  ·  {p.get('cat', '')}"))

    def _poll(self):
        def work():
            info = {"ollama": self.a.brain.available() and self.a.brain.has_model(),
                    "mic": bool(self.a.listener and self.a.listener.is_alive() and not self.a.listener.muted), "tts": True}
            try:
                urllib.request.urlopen("https://www.msftconnecttest.com/connecttest.txt", timeout=2).read(10)
                info["net"] = True
            except Exception:
                info["net"] = False
            self.b.info.emit(info)
        threading.Thread(target=work, daemon=True).start()

    def _set_info(self, info):
        for k, lbl in self.info_lbls.items():
            lbl.setText("Aktiv" if info.get(k) else "Aus / nicht erreichbar")

    # ---------- Slots ----------
    def on_log(self, role, text):
        who = {"user": "Du", "yavis": "YAVIS", "system": "System"}.get(role, role)
        self.logbox.appendPlainText(f"{who}: {text}")
        if role == "user":
            self.status.setText("„" + text[:70] + "“")
            QTimer.singleShot(400, self._refresh_recent)

    def on_state(self, s):
        self.orb.state = self.mini.state = s
        if s != "speaking":
            self.status.setText(STATUS_TEXT.get(s, ""))

    def on_emotion(self, e):
        self.orb.emotion = self.mini.emotion = e if e in ("neutral", "nett", "boese", "traurig") else "neutral"

    def _level(self, v):
        self.orb.set_ext(v)
        self.mini.set_ext(v)

    def on_confirm(self, question, holder):
        r = QMessageBox.question(self, "Bestätigung nötig", question)
        holder["ok"] = r == QMessageBox.StandardButton.Yes
        holder["ev"].set()

    def on_notice(self, kind):
        if kind == "ollama_missing":
            if QMessageBox.question(self, "Ollama fehlt", "Für das lokale KI-Gehirn wird das kostenlose Ollama benötigt. Jetzt herunterladen und installieren?") == QMessageBox.StandardButton.Yes:
                self._install_ollama()
        elif kind == "model_missing":
            if QMessageBox.question(self, "Modell fehlt", f"Das Modell {self.s.get('model')} ist noch nicht geladen (ca. 2 GB, einmalig). Jetzt herunterladen?") == QMessageBox.StandardButton.Yes:
                self._pull_model()

    def _send(self):
        t = self.inp.text().strip()
        if t:
            self.inp.clear()
            self.a.submit(t)

    def _mic_toggled(self, on):
        self.btn_mic.setText("🎤 Mikrofon an" if on else "🔇 Mikrofon aus")
        self.a.set_muted(not on)

    def _thumb_down(self):
        note, ok = QInputDialog.getText(self, "Was war falsch?", "Kurz sagen, was YAVIS besser machen soll (optional):")
        if ok:
            self.a.feedback(False, note)

    def _model_changed(self):
        self.s.set("model", self.ed_model.text().strip())
        self.model_lbl.setText("● " + self.s.get("model"))

    # ---------- Projekte ----------
    def _proj_select(self):
        self._proj_cur = None
        pid = self.ptree2.selected_id()
        self.proj_note.blockSignals(True)
        self.proj_note.setPlainText(self.proj.get_note(pid) if pid else "")
        self.proj_note.blockSignals(False)
        self._proj_cur = pid

    def _proj_note_changed(self):
        if self._proj_cur:
            self.proj.set_note(self._proj_cur, self.proj_note.toPlainText())

    def _proj_add(self):
        name, ok = QInputDialog.getText(self, "Neues Projekt", "Name:")
        if ok and name.strip():
            cats = self.ptree2.cats()
            cat, ok2 = QInputDialog.getItem(self, "Kategorie", "Kategorie:", cats, 0, True)
            if ok2:
                self.proj.add(name.strip(), cat.strip() or "Sonstiges")
                self.ptree2.refresh()
                self._refresh_home_projects()

    def _proj_rename(self):
        pid = self.ptree2.selected_id()
        if pid:
            name, ok = QInputDialog.getText(self, "Umbenennen", "Neuer Name:")
            if ok and name.strip():
                self.proj.rename(pid, name.strip())
                self.ptree2.refresh(keep=pid)
                self._refresh_home_projects()

    def _proj_del(self):
        pid = self.ptree2.selected_id()
        if pid and QMessageBox.question(self, "Löschen", "Projekt wirklich löschen?") == QMessageBox.StandardButton.Yes:
            self.proj.remove(pid)
            self.ptree2.refresh()
            self._refresh_home_projects()

    # ---------- Dateien ----------
    def _file_search(self):
        t = self.file_in.text().strip()
        if t:
            self.a.submit("suche datei " + t)

    @staticmethod
    def _open_folder(sub):
        if os.name == "nt":
            os.startfile(os.path.join(os.path.expanduser("~"), sub))  # noqa

    # ---------- Programme ----------
    def _set_all(self, on):
        self.s.set("allowed_programs", [e.id for e in programs.all_entries(self.s)] if on else [])
        self.ptree.refresh()

    def _add_custom_entry(self, name, path):
        c = self.s.get("custom_programs")
        c[name] = path
        self.s.set("custom_programs", c)
        if self.s.get("allowed_programs") is not None:
            self.s.set("allowed_programs", list(self.s.get("allowed_programs")) + ["custom:" + name])

    def _add_custom(self):
        path, _ = QFileDialog.getOpenFileName(self, "Programm, Spiel oder Verknüpfung wählen", "", "Alle Dateien (*.*)")
        if path:
            name, ok = QInputDialog.getText(self, "Name", "Wie soll ich es nennen, wenn du es sagst?", text=os.path.splitext(os.path.basename(path))[0])
            if ok and name.strip():
                self._add_custom_entry(name.strip(), path)
                self.ptree.refresh()

    def _scan_menu(self):
        found = programs.scan_start_menu(force=True)
        if not found:
            QMessageBox.information(self, "Startmenü", "Keine Verknüpfungen gefunden (nur unter Windows).")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Programme aus dem Startmenü hinzufügen")
        dlg.resize(460, 560)
        lay = QVBoxLayout(dlg)
        lst = QListWidget()
        lst.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        lst.addItems(sorted(found, key=str.lower))
        lay.addWidget(lst)
        ok = QPushButton("Ausgewählte hinzufügen")
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)
        if dlg.exec():
            for it in lst.selectedItems():
                self._add_custom_entry(it.text(), found[it.text()])
            self.ptree.refresh()

    def _remove_custom(self):
        pid = self.ptree.selected_id()
        if pid and pid.startswith("custom:"):
            c = self.s.get("custom_programs")
            c.pop(pid[7:], None)
            self.s.set("custom_programs", c)
            self.ptree.refresh()

    def _test_start(self):
        pid = self.ptree.selected_id()
        e = next((x for x in programs.all_entries(self.s) if x.id == pid), None)
        if e:
            ok, msg = programs.launch(e)
            if not ok:
                QMessageBox.warning(self, "Start", msg)

    # ---------- Musik ----------
    def _pick_music(self):
        d = QFileDialog.getExistingDirectory(self, "Musikordner wählen")
        if d:
            self.s.set("music_folder", d)
            self._reload_tracks()

    def _reload_tracks(self):
        n = self.a.music.load_folder(self.s.get("music_folder"))
        self.tracklist.clear()
        self.tracklist.addItems([p.stem for p in self.a.music.tracks])
        self.lbl_folder.setText(f"{self.s.get('music_folder')}  ({n} Titel)")

    # ---------- Automatisierungen ----------
    def _fill_macros(self):
        self.mlist2.clear()
        for k, v in self.s.get("macros").items():
            self.mlist2.addItem(f"{k}  →  {v}")

    def _edit_macros(self):
        rows = [dict(phrase=k, targets=v) for k, v in self.s.get("macros").items()]
        out = edit_rows(self, "Eigene Befehle", rows, [("phrase", "Satz (z. B. arbeitsmodus)"), ("targets", "Programme/Seiten, durch Komma getrennt")])
        if out is not None:
            self.s.set("macros", {r["phrase"].lower().strip(): r["targets"] for r in out if r["phrase"].strip()})
            self._fill_macros()

    def _test_macro(self):
        it = self.mlist2.currentItem()
        if it:
            self.a.submit(it.text().split("  →  ")[0])

    # ---------- Namen ----------
    def _add_wake(self):
        w = self.wedit.text().strip().lower()
        if len(w) >= 3 and " " not in w and w not in self.s.get("wake_words"):
            self.s.set("wake_words", self.s.get("wake_words") + [w])
            self.wlist.addItem(w)
            self.wedit.clear()

    def _rem_wake(self):
        it = self.wlist.currentItem()
        words = self.s.get("wake_words")
        if it and len(words) > 1:
            words.remove(it.text())
            self.s.set("wake_words", words)
            self.wlist.takeItem(self.wlist.row(it))

    # ---------- Gedächtnis ----------
    def _refresh_mem(self):
        self.mlist.clear()
        tb = self.cmb_mem.currentData()
        for i, text, extra in self.a.mem.list(tb):
            self.mlist.addItem(text + ("  ✓" if tb == "todos" and extra else ""))
            self.mlist.item(self.mlist.count() - 1).setData(ROLE, i)

    def _del_mem(self):
        for it in self.mlist.selectedItems():
            self.a.mem.delete(self.cmb_mem.currentData(), it.data(ROLE))
        self._refresh_mem()

    def _clear_mem(self):
        if QMessageBox.question(self, "Löschen", "Diese Liste komplett leeren?") == QMessageBox.StandardButton.Yes:
            self.a.mem.clear(self.cmb_mem.currentData())
            self._refresh_mem()

    def _clear_all_mem(self):
        if QMessageBox.question(self, "ALLES löschen", "Wirklich ALLE gespeicherten Daten löschen?") == QMessageBox.StandardButton.Yes:
            self.a.mem.clear()
            self._refresh_mem()

    # ---------- Verkauf ----------
    def _gen(self, tpl):
        txt = self.sales_in.toPlainText().strip()
        if txt:
            self.sales_out.setPlainText("Ich schreibe …")
            threading.Thread(target=lambda: self.b.text_out.emit(self.a.generate_text(tpl.format(txt))), daemon=True).start()

    def _prices(self):
        txt = self.sales_in.toPlainText().strip().split("\n")[0]
        if txt:
            self.a.submit("preise " + txt)

    # ---------- Ollama ----------
    def _check_brain(self, verbose=False):
        if not self.a.brain.available():
            self.b.notice.emit("ollama_missing")
        elif not self.a.brain.has_model():
            self.b.notice.emit("model_missing")
        else:
            threading.Thread(target=self.a.brain.warmup, daemon=True).start()
            if verbose:
                self.b.status.emit("Ollama läuft, Modell bereit.")

    def _install_ollama(self):
        def work():
            try:
                self.b.status.emit("Lade Ollama herunter …")
                dest = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
                urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", dest)
                self.b.status.emit("Ollama-Installer gestartet. Danach „Modell herunterladen“ drücken.")
                os.startfile(dest)  # noqa
            except Exception as ex:
                self.b.status.emit(f"Download fehlgeschlagen: {ex}")
        threading.Thread(target=work, daemon=True).start()

    def _pull_model(self):
        def work():
            try:
                self.a.brain.pull(self.s.get("model"), lambda st, pct: self.b.status.emit(f"Modell: {st} {'' if pct is None else str(pct) + '%'}"))
                self.b.status.emit("Modell fertig geladen.")
                self.a.brain.available()
                self.a.brain.warmup()
            except Exception as ex:
                self.b.status.emit(f"Modell-Download fehlgeschlagen (läuft Ollama?): {ex}")
        threading.Thread(target=work, daemon=True).start()

    # ---------- Autostart & Tray ----------
    @staticmethod
    def _autostart_get():
        if os.name != "nt":
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
                winreg.QueryValueEx(k, "YAVIS")
                return True
        except Exception:
            return False

    @staticmethod
    def _autostart_set(on):
        if os.name != "nt":
            return
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as k:
            if on:
                cmd = f'"{sys.executable}" --minimized' if getattr(sys, "frozen", False) else f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}" --minimized'
                winreg.SetValueEx(k, "YAVIS", 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(k, "YAVIS")
                except FileNotFoundError:
                    pass

    def _tray(self):
        self.tray = QSystemTrayIcon(make_icon(), self)
        m = QMenu()
        a1, a2 = QAction("YAVIS öffnen", self), QAction("Beenden", self)
        a1.triggered.connect(self.showNormal)
        a2.triggered.connect(self._quit)
        m.addAction(a1)
        m.addAction(a2)
        self._tray_menu = m
        self.tray.setContextMenu(m)
        self.tray.activated.connect(lambda r: self.showNormal() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.setToolTip("YAVIS läuft – sag „YAVIS“")
        self.tray.show()

    def _quit(self):
        self._quitting = True
        self.a.music.stop()
        self.a.speaker.stop()
        if self.a.listener:
            self.a.listener.stop()
        QApplication.quit()

    def closeEvent(self, e):
        if self._quitting or not self.tray.isVisible():
            e.accept()
        else:
            e.ignore()
            self.hide()
            self.tray.showMessage("YAVIS", "Läuft im Hintergrund weiter. Rechtsklick auf das Symbol zum Beenden.")

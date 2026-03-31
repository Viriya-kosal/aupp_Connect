"""
main.py  —  AUPP Connect PyQt6 Desktop Client  (v3 - Full UI Redesign)
Run with: python main.py
Make sure the Django server is running first: python manage.py runserver
"""

import sys
import os
import json
from datetime import datetime
import urllib.request
import urllib.error

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QScrollArea,
    QFrame, QComboBox, QStackedWidget, QFileDialog, QMessageBox,
    QDialog, QSizePolicy, QToolButton, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QAction, QCursor

API_BASE = 'http://127.0.0.1:8000/api'


def api(method, path, data=None, params=None):
    url = f'{API_BASE}{path}'
    if params:
        url += '?' + '&'.join(f'{k}={v}' for k, v in params.items())
    body    = json.dumps(data).encode() if data is not None else None
    headers = {'Content-Type': 'application/json'}
    req     = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ── Design Tokens ──────────────────────────────────────────────────────────────
PRIMARY      = '#1A6ED8'
PRIMARY_DARK = '#1158B0'
PRIMARY_LITE = '#EBF3FF'
PRIMARY_MID  = '#A8CCFA'
ACCENT       = '#F5A623'
SUCCESS      = '#27AE60'
DANGER       = '#E74C3C'
TEXT_DARK    = '#1A1A2E'
TEXT_MID     = '#555570'
TEXT_MUTED   = '#9999AA'
BORDER       = '#E4E6EF'
BG_APP       = '#F0F2F8'
BG_SIDEBAR   = '#1A1A2E'
WHITE        = '#FFFFFF'

AVATAR_PALETTES = [
    ('#D6E8FF', '#1A6ED8'), ('#D6F5E8', '#1A8C5A'), ('#FFE8D6', '#C0522A'),
    ('#F5D6FF', '#8C1AB5'), ('#FFF5D6', '#B58C1A'), ('#D6FFF5', '#1AB5A0'),
]

NAV_COLORS = {'feed': '#4A9EFF', 'bookmarks': '#F5A623', 'stats': '#9B59B6'}

STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 5px; }
QScrollBar::handle:vertical { background: #CCCCDD; border-radius: 3px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLineEdit, QTextEdit {
    border: 1.5px solid #E4E6EF; border-radius: 10px;
    padding: 10px 14px; background: #FFFFFF;
    font-size: 13px; color: #1A1A2E;
}
QLineEdit:focus, QTextEdit:focus { border: 1.5px solid #1A6ED8; background: #FAFCFF; }
QComboBox {
    border: 1.5px solid #E4E6EF; border-radius: 10px;
    padding: 8px 14px; background: #FFFFFF;
    font-size: 12px; color: #555570;
}
QComboBox:focus { border: 1.5px solid #1A6ED8; }
QComboBox::drop-down { border: none; width: 20px; }
QMenu {
    background: #FFFFFF; border: 1px solid #E4E6EF;
    border-radius: 10px; padding: 6px;
}
QMenu::item { padding: 8px 20px; border-radius: 7px; font-size: 12px; color: #1A1A2E; }
QMenu::item:selected { background: #EBF3FF; color: #1A6ED8; }
QToolTip { background: #1A1A2E; color: white; border: none; border-radius: 6px; padding: 5px 10px; font-size: 11px; }
"""

_meta = {'departments': {}, 'course_tags': {}}

def load_metadata():
    result = api('GET', '/metadata/')
    if result and 'departments' in result:
        _meta['departments'] = result['departments']
        _meta['course_tags'] = result['course_tags']


def timesince(dt_str):
    try:
        dt   = datetime.strptime(dt_str[:19], '%Y-%m-%d %H:%M:%S')
        diff = datetime.now() - dt
        s    = int(diff.total_seconds())
        if s < 60:    return 'just now'
        if s < 3600:  return f'{s // 60}m ago'
        if s < 86400: return f'{s // 3600}h ago'
        return f'{s // 86400}d ago'
    except Exception:
        return ''


def make_avatar(initials, size=38, palette_idx=0):
    bg, fg = AVATAR_PALETTES[palette_idx % len(AVATAR_PALETTES)]
    lbl = QLabel(str(initials).upper()[:2])
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"QLabel{{background:{bg};color:{fg};border-radius:{size//2}px;font-size:{max(9,size//3)}px;font-weight:700;border:none;}}")
    return lbl


def make_card(radius=14):
    f = QFrame()
    f.setStyleSheet(f"QFrame{{background:{WHITE};border:1px solid {BORDER};border-radius:{radius}px;}}")
    return f


def make_divider():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{BORDER};border:none;max-height:1px;")
    return line


def show_toast(parent_window, message, color=SUCCESS):
    toast = QLabel(message, parent_window)
    toast.setStyleSheet(f"QLabel{{background:{color};color:white;border-radius:18px;padding:10px 22px;font-size:13px;font-weight:700;border:none;}}")
    toast.adjustSize()
    pw, ph = parent_window.width(), parent_window.height()
    toast.move((pw - toast.width()) // 2, ph - 80)
    toast.show()
    toast.raise_()
    QTimer.singleShot(2500, toast.deleteLater)


# ── Dialogs ────────────────────────────────────────────────────────────────────

class EditPostDialog(QDialog):
    def __init__(self, post, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Edit Post')
        self.setFixedWidth(500)
        self.setStyleSheet(f"background:{WHITE};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(QLabel('Edit Post', styleSheet=f"font-size:17px;font-weight:700;color:{TEXT_DARK};border:none;background:transparent;"))
        self.body_edit = QTextEdit()
        self.body_edit.setPlainText(post.get('body', ''))
        self.body_edit.setFixedHeight(130)
        layout.addWidget(self.body_edit)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton('Cancel')
        cancel.setStyleSheet(f"background:transparent;color:{TEXT_MUTED};border:1.5px solid {BORDER};border-radius:18px;padding:8px 20px;font-size:13px;")
        cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel.clicked.connect(self.reject)
        save = QPushButton('Save Changes')
        save.setStyleSheet(f"background:{PRIMARY};color:white;border:none;border-radius:18px;padding:9px 24px;font-size:13px;font-weight:700;")
        save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(save)
        layout.addLayout(row)

    def new_body(self):
        return self.body_edit.toPlainText().strip()


class ShareDialog(QDialog):
    def __init__(self, post, parent=None):
        super().__init__(parent)
        self.post    = post
        self._shared = False
        self.setWindowTitle('Share Post')
        self.setFixedWidth(440)
        self.setStyleSheet(f"background:{WHITE};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(QLabel('Share this post', styleSheet=f"font-size:17px;font-weight:700;color:{TEXT_DARK};border:none;background:transparent;"))
        preview = QFrame()
        preview.setStyleSheet(f"QFrame{{background:{BG_APP};border:1px solid {BORDER};border-radius:10px;}}")
        pl = QVBoxLayout(preview)
        pl.setContentsMargins(14, 12, 14, 12)
        pl.addWidget(QLabel(f"{post['first_name']} {post['last_name']}", styleSheet=f"font-size:12px;font-weight:700;color:{PRIMARY};border:none;background:transparent;"))
        body_txt = post.get('body','')[:160] + ('…' if len(post.get('body',''))>160 else '')
        bl = QLabel(body_txt)
        bl.setWordWrap(True)
        bl.setStyleSheet(f"font-size:12px;color:{TEXT_MID};border:none;background:transparent;")
        pl.addWidget(bl)
        layout.addWidget(preview)
        self.note = QTextEdit()
        self.note.setPlaceholderText('Add a note... (optional)')
        self.note.setFixedHeight(70)
        layout.addWidget(self.note)
        row = QHBoxLayout()
        row.setSpacing(10)
        copy = QPushButton('📋  Copy to Clipboard')
        copy.setStyleSheet(f"background:{PRIMARY};color:white;border:none;border-radius:18px;padding:9px 18px;font-size:13px;font-weight:600;")
        copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        copy.clicked.connect(self._copy)
        share = QPushButton('🔁  Share Internally')
        share.setStyleSheet(f"background:{SUCCESS};color:white;border:none;border-radius:18px;padding:9px 18px;font-size:13px;font-weight:600;")
        share.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        share.clicked.connect(self._share_internal)
        row.addWidget(copy)
        row.addWidget(share)
        layout.addLayout(row)
        cancel = QPushButton('Cancel')
        cancel.setStyleSheet(f"background:transparent;color:{TEXT_MUTED};border:none;font-size:12px;padding:4px;")
        cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel, alignment=Qt.AlignmentFlag.AlignCenter)

    def _copy(self):
        extra = self.note.toPlainText().strip()
        text  = f"[AUPP Connect] {self.post['first_name']} {self.post['last_name']} wrote:\n\n{self.post.get('body','')}"
        if extra: text = extra + '\n\n' + text
        QApplication.clipboard().setText(text)
        self._shared = True
        self.accept()

    def _share_internal(self):
        self._shared = True
        self.accept()

    def was_shared(self): return self._shared


# ── Post Card ──────────────────────────────────────────────────────────────────

class PostCard(QFrame):
    post_deleted     = pyqtSignal(int)
    bookmark_changed = pyqtSignal(int, bool)

    def __init__(self, post, current_user):
        super().__init__()
        self.post            = post
        self.current_user    = current_user
        self._comments_open  = False
        self._bookmarked     = post.get('bookmarked_by_me', False)
        self._liked          = post.get('liked_by_me', False)
        self._build()

    def _build(self):
        self.setStyleSheet(f"QFrame{{background:{WHITE};border:1px solid {BORDER};border-radius:16px;}}")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 16)
        outer.setSpacing(14)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        palette_idx = self.post['id'] % len(AVATAR_PALETTES)
        hdr.addWidget(make_avatar(self.post.get('avatar_initials','?'), size=44, palette_idx=palette_idx))

        meta = QVBoxLayout()
        meta.setSpacing(2)
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_lbl = QLabel(f"{self.post['first_name']} {self.post['last_name']}")
        name_lbl.setStyleSheet(f"font-size:14px;font-weight:700;color:{TEXT_DARK};border:none;background:transparent;")
        name_row.addWidget(name_lbl)
        if self.post.get('course_tag'):
            tag = QLabel(f"# {self.post['course_tag']}")
            tag.setStyleSheet(f"background:{PRIMARY_LITE};color:{PRIMARY};font-size:10px;font-weight:700;border-radius:8px;padding:2px 9px;border:none;")
            name_row.addWidget(tag)
        if self.post.get('sentiment'):
            s = self.post['sentiment']
            sc = {'positive': (SUCCESS,'#E8F8EF'), 'neutral': (TEXT_MUTED,'#F4F4F8'), 'negative': (DANGER,'#FDECEA')}
            sfg, sbg = sc.get(s, (TEXT_MUTED, '#F4F4F8'))
            sl = QLabel(f"● {s.capitalize()}")
            sl.setStyleSheet(f"background:{sbg};color:{sfg};font-size:10px;font-weight:600;border-radius:8px;padding:2px 9px;border:none;")
            name_row.addWidget(sl)
        name_row.addStretch()
        meta.addLayout(name_row)
        dept = _meta['departments'].get(self.post.get('department',''), '')
        sub = QLabel(f"{dept}  ·  Year {self.post.get('year_level','')}  ·  {timesince(self.post.get('created_at',''))}")
        sub.setStyleSheet(f"font-size:11px;color:{TEXT_MUTED};border:none;background:transparent;")
        meta.addWidget(sub)
        hdr.addLayout(meta, 1)

        # ••• menu
        more = QToolButton()
        more.setText('•••')
        more.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        more.setStyleSheet(f"""
            QToolButton{{background:transparent;color:{TEXT_MUTED};border:none;font-size:12px;
            padding:4px 8px;border-radius:8px;font-weight:700;letter-spacing:2px;}}
            QToolButton:hover{{background:{BG_APP};color:{TEXT_DARK};}}
            QToolButton::menu-indicator{{image:none;}}
        """)
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(more)
        is_own = str(self.post.get('author_id')) == str(self.current_user['id'])
        if is_own:
            ae = QAction('✏️   Edit post', self); ae.triggered.connect(self._edit_post); menu.addAction(ae)
            ad = QAction('🗑️   Delete post', self); ad.triggered.connect(self._delete_post); menu.addAction(ad)
            menu.addSeparator()
        ac = QAction('🔗   Copy text', self)
        ac.triggered.connect(lambda: (QApplication.clipboard().setText(self.post.get('body','')), show_toast(self.window(), '📋  Copied!', TEXT_MID)))
        menu.addAction(ac)
        more.setMenu(menu)
        hdr.addWidget(more)
        outer.addLayout(hdr)

        # ── Body ─────────────────────────────────────────────────────────────
        self.body_lbl = QLabel(self.post.get('body',''))
        self.body_lbl.setWordWrap(True)
        self.body_lbl.setStyleSheet(f"font-size:14px;color:{TEXT_DARK};border:none;background:transparent;")
        outer.addWidget(self.body_lbl)

        # ── Image ─────────────────────────────────────────────────────────────
        img = self.post.get('image_path','')
        if img and os.path.exists(img):
            il = QLabel()
            il.setPixmap(QPixmap(img).scaledToWidth(560, Qt.TransformationMode.SmoothTransformation))
            il.setStyleSheet("border-radius:10px;border:none;")
            outer.addWidget(il)

        # ── Counts ────────────────────────────────────────────────────────────
        lc = self.post.get('like_count', 0)
        cc = self.post.get('comment_count', 0)
        sc = self.post.get('share_count', 0)
        parts = []
        if lc: parts.append(f"❤️ {lc}")
        if cc: parts.append(f"💬 {cc}")
        if sc: parts.append(f"↗ {sc}")
        if parts:
            self.counts_lbl = QLabel('   '.join(parts))
            self.counts_lbl.setStyleSheet(f"font-size:12px;color:{TEXT_MUTED};border:none;background:transparent;")
            outer.addWidget(self.counts_lbl)
        else:
            self.counts_lbl = None

        outer.addWidget(make_divider())

        # ── Action buttons ────────────────────────────────────────────────────
        actions = QHBoxLayout()
        actions.setSpacing(2)

        self.like_btn = self._action_btn('❤️', 'Like', self._liked, DANGER)
        self.like_btn.clicked.connect(self._toggle_like)
        actions.addWidget(self.like_btn)

        self.cmt_btn = self._action_btn('💬', 'Comment', False, PRIMARY)
        self.cmt_btn.clicked.connect(self._toggle_comments)
        actions.addWidget(self.cmt_btn)

        self.share_btn = self._action_btn('↗', 'Share', False, SUCCESS)
        self.share_btn.clicked.connect(self._share_post)
        actions.addWidget(self.share_btn)

        actions.addStretch()

        self.bm_btn = self._action_btn('🔖', 'Save', self._bookmarked, ACCENT)
        self.bm_btn.clicked.connect(self._toggle_bookmark)
        actions.addWidget(self.bm_btn)

        outer.addLayout(actions)

        # ── Comments panel ─────────────────────────────────────────────────────
        self.cmt_panel  = QWidget()
        self.cmt_panel.setStyleSheet("background:transparent;")
        self.cmt_vbox   = QVBoxLayout(self.cmt_panel)
        self.cmt_vbox.setContentsMargins(0, 4, 0, 0)
        self.cmt_vbox.setSpacing(10)
        self.cmt_panel.setVisible(False)
        outer.addWidget(self.cmt_panel)

    def _action_btn(self, icon, label, active=False, active_color=PRIMARY):
        color = active_color if active else TEXT_MUTED
        btn = QPushButton(f' {icon}  {label} ')
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        bg = f'{active_color}18' if active else 'transparent'
        btn.setStyleSheet(f"""
            QPushButton{{background:{bg};color:{color};border:none;border-radius:10px;
            padding:8px 14px;font-size:13px;font-weight:{'700' if active else '500'};}}
            QPushButton:hover{{background:{PRIMARY_LITE};color:{PRIMARY};}}
        """)
        return btn

    def _set_active(self, btn, active, icon, label, active_color):
        color = active_color if active else TEXT_MUTED
        bg    = f'{active_color}18' if active else 'transparent'
        btn.setText(f' {icon}  {label} ')
        btn.setStyleSheet(f"""
            QPushButton{{background:{bg};color:{color};border:none;border-radius:10px;
            padding:8px 14px;font-size:13px;font-weight:{'700' if active else '500'};}}
            QPushButton:hover{{background:{PRIMARY_LITE};color:{PRIMARY};}}
        """)

    def _refresh_counts(self):
        lc = self.post.get('like_count', 0)
        cc = self.post.get('comment_count', 0)
        sc = self.post.get('share_count', 0)
        parts = []
        if lc: parts.append(f"❤️ {lc}")
        if cc: parts.append(f"💬 {cc}")
        if sc: parts.append(f"↗ {sc}")
        if self.counts_lbl:
            self.counts_lbl.setText('   '.join(parts))

    # ── Interactions ──────────────────────────────────────────────────────────

    def _toggle_like(self):
        result = api('POST', f'/posts/{self.post["id"]}/like/', {'user_id': self.current_user['id']})
        if result.get('ok'):
            self._liked = result['liked']
            self.post['like_count'] = result['like_count']
            self._set_active(self.like_btn, self._liked, '❤️', 'Like', DANGER)
            self._refresh_counts()

    def _toggle_comments(self):
        self._comments_open = not self._comments_open
        if self._comments_open:
            self._load_comments()
        self.cmt_panel.setVisible(self._comments_open)

    def _share_post(self):
        dlg = ShareDialog(self.post, self)
        dlg.exec()
        if dlg.was_shared():
            result = api('POST', f'/posts/{self.post["id"]}/share/', {'user_id': self.current_user['id']})
            self.post['share_count'] = result.get('share_count', self.post.get('share_count', 0) + 1)
            self._refresh_counts()
            show_toast(self.window(), '↗  Post shared!', PRIMARY)

    def _toggle_bookmark(self):
        result = api('POST', f'/posts/{self.post["id"]}/bookmark/', {'user_id': self.current_user['id']})
        if result.get('ok'):
            self._bookmarked = result['bookmarked']
            self._set_active(self.bm_btn, self._bookmarked, '🔖', 'Save', ACCENT)
            self.bookmark_changed.emit(self.post['id'], self._bookmarked)
            show_toast(self.window(), '🔖  Saved!' if self._bookmarked else 'Bookmark removed', ACCENT if self._bookmarked else TEXT_MUTED)

    def _edit_post(self):
        dlg = EditPostDialog(self.post, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_body = dlg.new_body()
            if not new_body: return
            result = api('PATCH', f'/posts/{self.post["id"]}/', {'user_id': self.current_user['id'], 'body': new_body})
            if result.get('ok'):
                self.post['body'] = new_body
                self.body_lbl.setText(new_body)
                show_toast(self.window(), '✅  Post updated!', SUCCESS)
            else:
                QMessageBox.warning(self, 'Error', result.get('error', 'Could not update.'))

    def _delete_post(self):
        if QMessageBox.question(self, 'Delete', 'Delete this post permanently?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Yes:
            result = api('DELETE', f'/posts/{self.post["id"]}/', {'user_id': self.current_user['id']})
            if result.get('ok'):
                self.post_deleted.emit(self.post['id'])
                self.setVisible(False); self.deleteLater()
            else:
                QMessageBox.warning(self, 'Error', result.get('error', 'Could not delete.'))

    # ── Comments ──────────────────────────────────────────────────────────────

    def _load_comments(self):
        while self.cmt_vbox.count():
            item = self.cmt_vbox.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        result   = api('GET', f'/posts/{self.post["id"]}/comments/')
        comments = result.get('comments', [])

        if not comments:
            lbl = QLabel('No comments yet — be the first!')
            lbl.setStyleSheet(f"font-size:12px;color:{TEXT_MUTED};background:transparent;border:none;padding:4px 0;")
            self.cmt_vbox.addWidget(lbl)
        else:
            for c in comments:
                self._add_comment_row(c)

        # Input
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(make_avatar(self.current_user.get('avatar_initials','?'), size=32, palette_idx=0))
        self.cmt_input = QLineEdit()
        self.cmt_input.setPlaceholderText('Write a comment...')
        self.cmt_input.setStyleSheet(f"QLineEdit{{border:1.5px solid {BORDER};border-radius:18px;padding:8px 14px;font-size:12px;background:{BG_APP};}}QLineEdit:focus{{border-color:{PRIMARY};background:{WHITE};}}")
        self.cmt_input.returnPressed.connect(self._send_comment)
        send = QPushButton('Send')
        send.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        send.setStyleSheet(f"background:{PRIMARY};color:white;border:none;border-radius:16px;padding:8px 18px;font-size:12px;font-weight:700;")
        send.clicked.connect(self._send_comment)
        row.addWidget(self.cmt_input, 1)
        row.addWidget(send)
        wrap = QWidget(); wrap.setStyleSheet("background:transparent;"); wrap.setLayout(row)
        self.cmt_vbox.addWidget(wrap)

    def _add_comment_row(self, c):
        row = QHBoxLayout(); row.setSpacing(10); row.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.addWidget(make_avatar(c.get('avatar_initials','?'), size=32, palette_idx=c['id'] % len(AVATAR_PALETTES)))
        bubble = QFrame()
        bubble.setStyleSheet(f"QFrame{{background:{BG_APP};border-radius:12px;border:none;}}")
        bl = QVBoxLayout(bubble); bl.setContentsMargins(12,8,12,8); bl.setSpacing(3)
        top = QHBoxLayout()
        top.addWidget(QLabel(f"{c['first_name']} {c['last_name']}", styleSheet=f"font-size:12px;font-weight:700;color:{PRIMARY};border:none;background:transparent;"))
        top.addWidget(QLabel(timesince(c.get('created_at','')), styleSheet=f"font-size:10px;color:{TEXT_MUTED};border:none;background:transparent;"))
        top.addStretch()
        if str(c.get('author_id','')) == str(self.current_user['id']):
            db = QPushButton('×'); db.setFixedSize(20,20)
            db.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            db.setStyleSheet(f"background:transparent;color:{TEXT_MUTED};border:none;font-size:14px;font-weight:700;")
            cid = c['id']; db.clicked.connect(lambda _, _id=cid: self._delete_comment(_id))
            top.addWidget(db)
        bl.addLayout(top)
        body = QLabel(c['body']); body.setWordWrap(True)
        body.setStyleSheet(f"font-size:12px;color:{TEXT_DARK};border:none;background:transparent;")
        bl.addWidget(body)
        row.addWidget(bubble, 1)
        wrap = QWidget(); wrap.setStyleSheet("background:transparent;"); wrap.setLayout(row)
        self.cmt_vbox.addWidget(wrap)

    def _send_comment(self):
        text = self.cmt_input.text().strip()
        if not text: return
        result = api('POST', f'/posts/{self.post["id"]}/comments/', {'author_id': self.current_user['id'], 'body': text})
        if result.get('ok'):
            self.post['comment_count'] = self.post.get('comment_count', 0) + 1
            self.cmt_input.clear()
            self._load_comments()

    def _delete_comment(self, comment_id):
        result = api('DELETE', f'/comments/{comment_id}/', {'user_id': self.current_user['id']})
        if result.get('ok'):
            self.post['comment_count'] = max(0, self.post.get('comment_count', 1) - 1)
            self._load_comments()


# ── Compose Box ────────────────────────────────────────────────────────────────

class ComposeBox(QFrame):
    post_created = pyqtSignal()

    def __init__(self, user):
        super().__init__()
        self.user           = user
        self.selected_image = ''
        self._build()

    def _build(self):
        self.setStyleSheet(f"QFrame{{background:{WHITE};border:1px solid {BORDER};border-radius:16px;}}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(14)

        top = QHBoxLayout(); top.setSpacing(12); top.setAlignment(Qt.AlignmentFlag.AlignTop)
        top.addWidget(make_avatar(self.user.get('avatar_initials','?'), size=44, palette_idx=0))
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("What's on your mind? Share something with your campus...")
        self.text_area.setMinimumHeight(80)
        self.text_area.setMaximumHeight(140)
        self.text_area.setStyleSheet(f"QTextEdit{{border:none;border-radius:12px;padding:10px 14px;font-size:14px;background:{BG_APP};color:{TEXT_DARK};}}QTextEdit:focus{{background:{WHITE};border:1.5px solid {PRIMARY};}}")
        top.addWidget(self.text_area, 1)
        layout.addLayout(top)

        self.img_preview = QLabel(); self.img_preview.setVisible(False)
        self.img_preview.setStyleSheet("border-radius:10px;border:none;")
        layout.addWidget(self.img_preview)

        layout.addWidget(make_divider())

        # Bottom bar
        bottom = QHBoxLayout(); bottom.setSpacing(10)

        photo_btn = QPushButton('📷  Add Photo')
        photo_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        photo_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXT_MID};border:1.5px solid {BORDER};border-radius:18px;padding:7px 16px;font-size:12px;font-weight:500;}}QPushButton:hover{{background:{PRIMARY_LITE};color:{PRIMARY};border-color:{PRIMARY_MID};}}")
        photo_btn.clicked.connect(self._pick_image)
        bottom.addWidget(photo_btn)

        self.tag_combo = QComboBox()
        self.tag_combo.setFixedWidth(155)
        self.tag_combo.addItem('🏷️  No Tag', '')
        for code, label in _meta['course_tags'].items():
            self.tag_combo.addItem(label, code)
        self.tag_combo.setStyleSheet(f"QComboBox{{border:1.5px solid {BORDER};border-radius:18px;padding:7px 14px;font-size:12px;color:{TEXT_MID};background:{WHITE};}}QComboBox:hover{{border-color:{PRIMARY_MID};}}")
        bottom.addWidget(self.tag_combo)
        bottom.addStretch()

        # THE POST BUTTON — large, visible, unmissable
        self.post_btn = QPushButton('📢  Post Now')
        self.post_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.post_btn.setFixedHeight(42)
        self.post_btn.setMinimumWidth(130)
        self.post_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {PRIMARY},stop:1 #2E8BF0);
                color: white; border: none; border-radius: 21px;
                padding: 0 28px; font-size: 14px; font-weight: 800;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {PRIMARY_DARK},stop:1 {PRIMARY});
            }}
            QPushButton:pressed {{ background: {PRIMARY_DARK}; }}
        """)
        self.post_btn.clicked.connect(self._submit)
        bottom.addWidget(self.post_btn)
        layout.addLayout(bottom)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select Image', '', 'Images (*.png *.jpg *.jpeg *.gif)')
        if path:
            self.selected_image = path
            self.img_preview.setPixmap(QPixmap(path).scaledToWidth(320, Qt.TransformationMode.SmoothTransformation))
            self.img_preview.setVisible(True)

    def _submit(self):
        body = self.text_area.toPlainText().strip()
        if not body:
            show_toast(self.window(), '⚠️  Write something first!', DANGER)
            return
        result = api('POST', '/posts/', {
            'author_id':  self.user['id'],
            'body':       body,
            'course_tag': self.tag_combo.currentData() or '',
            'image_path': self.selected_image,
        })
        if result.get('ok'):
            self.text_area.clear()
            self.selected_image = ''
            self.img_preview.setVisible(False)
            self.tag_combo.setCurrentIndex(0)
            show_toast(self.window(), '🎉  Post published!', SUCCESS)
            self.post_created.emit()
        else:
            QMessageBox.warning(self, 'Error', result.get('error', 'Could not post.'))


# ── Sidebar ────────────────────────────────────────────────────────────────────

class Sidebar(QWidget):
    nav_changed = pyqtSignal(str)

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setFixedWidth(220)
        self.setStyleSheet(f"background:{BG_SIDEBAR};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo_wrap = QWidget()
        logo_wrap.setStyleSheet(f"background:{BG_SIDEBAR};border-bottom:1px solid #2E2E45;")
        lw = QVBoxLayout(logo_wrap)
        lw.setContentsMargins(20, 22, 20, 18); lw.setSpacing(0)
        l1 = QLabel('AUPP')
        l1.setStyleSheet(f"font-size:26px;font-weight:900;color:{PRIMARY};border:none;background:transparent;letter-spacing:-1px;")
        l2 = QLabel('Connect')
        l2.setStyleSheet(f"font-size:26px;font-weight:900;color:white;border:none;background:transparent;letter-spacing:-1px;margin-top:-6px;")
        l3 = QLabel('Student Community Platform')
        l3.setStyleSheet(f"font-size:10px;color:#666688;border:none;background:transparent;font-weight:500;margin-top:4px;")
        lw.addWidget(l1); lw.addWidget(l2); lw.addWidget(l3)
        layout.addWidget(logo_wrap)

        # Nav
        nav_wrap = QWidget()
        nav_wrap.setStyleSheet(f"background:{BG_SIDEBAR};")
        nv = QVBoxLayout(nav_wrap)
        nv.setContentsMargins(12, 20, 12, 20); nv.setSpacing(4)

        self.nav_btns = {}
        for key, icon, label in [('feed','🏠','Home Feed'), ('bookmarks','🔖','Saved Posts'), ('stats','📊','Statistics')]:
            btn = QPushButton(f'   {icon}   {label}')
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setMinimumHeight(48)
            btn.clicked.connect(lambda _, k=key: self._nav(k))
            self.nav_btns[key] = btn
            nv.addWidget(btn)

        nv.addStretch()
        layout.addWidget(nav_wrap, 1)

        # User strip
        us_wrap = QWidget()
        us_wrap.setStyleSheet("background:#14142A;border-top:1px solid #2E2E45;")
        us = QHBoxLayout(us_wrap); us.setContentsMargins(16,14,16,14); us.setSpacing(10)
        us.addWidget(make_avatar(self.user.get('avatar_initials','?'), size=36, palette_idx=0))
        info = QVBoxLayout(); info.setSpacing(1)
        info.addWidget(QLabel(f"{self.user['first_name']} {self.user['last_name']}", styleSheet="font-size:12px;font-weight:700;color:white;border:none;background:transparent;"))
        dept = _meta['departments'].get(self.user.get('department',''), '')
        info.addWidget(QLabel(f"{dept} · Yr {self.user.get('year_level',1)}", styleSheet=f"font-size:10px;color:#666688;border:none;background:transparent;"))
        us.addLayout(info, 1)
        logout = QPushButton('↪')
        logout.setFixedSize(30,30); logout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        logout.setStyleSheet(f"background:#2E2E45;color:#888899;border:none;border-radius:15px;font-size:14px;")
        logout.setToolTip('Log out')
        logout.clicked.connect(lambda: self.nav_changed.emit('logout'))
        us.addWidget(logout)
        layout.addWidget(us_wrap)
        self._set_active('feed')

    def _nav(self, key):
        self._set_active(key)
        self.nav_changed.emit(key)

    def _set_active(self, key):
        accent = NAV_COLORS.get(key, PRIMARY)
        for k, btn in self.nav_btns.items():
            if k == key:
                btn.setStyleSheet(f"QPushButton{{background:{accent}25;color:{accent};border:none;border-radius:12px;padding:12px 16px;font-size:13px;font-weight:700;text-align:left;}}")
            else:
                btn.setStyleSheet(f"QPushButton{{background:transparent;color:#888899;border:none;border-radius:12px;padding:12px 16px;font-size:13px;font-weight:500;text-align:left;}}QPushButton:hover{{background:#2E2E45;color:white;}}")


# ── Feed Page ──────────────────────────────────────────────────────────────────

class FeedPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._build()
        self._load()

    def _build(self):
        self.setStyleSheet(f"background:{BG_APP};")
        root = QHBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(20)

        # Center
        center = QWidget(); center.setStyleSheet("background:transparent;")
        cv = QVBoxLayout(center); cv.setContentsMargins(0,0,0,0); cv.setSpacing(14)

        self.compose = ComposeBox(self.user)
        self.compose.post_created.connect(self._load)
        cv.addWidget(self.compose)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel('Latest Posts', styleSheet=f"font-size:15px;font-weight:700;color:{TEXT_DARK};border:none;background:transparent;"))
        top_row.addStretch()
        ref = QPushButton('↻  Refresh')
        ref.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ref.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXT_MID};border:1.5px solid {BORDER};border-radius:16px;padding:6px 14px;font-size:12px;}}QPushButton:hover{{background:{PRIMARY_LITE};color:{PRIMARY};border-color:{PRIMARY_MID};}}")
        ref.clicked.connect(self._load)
        top_row.addWidget(ref)
        cv.addLayout(top_row)

        self.feed_scroll = QScrollArea()
        self.feed_scroll.setWidgetResizable(True)
        self.feed_scroll.setStyleSheet("background:transparent;border:none;")
        self.feed_inner = QWidget(); self.feed_inner.setStyleSheet("background:transparent;")
        self.feed_vbox  = QVBoxLayout(self.feed_inner)
        self.feed_vbox.setContentsMargins(0,0,0,0); self.feed_vbox.setSpacing(16)
        self.feed_vbox.addStretch()
        self.feed_scroll.setWidget(self.feed_inner)
        cv.addWidget(self.feed_scroll, 1)
        root.addWidget(center, 1)

        # Right panel
        right = QWidget(); right.setFixedWidth(230); right.setStyleSheet("background:transparent;")
        rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(16)

        self.trend_card = make_card()
        self.trend_layout = QVBoxLayout(self.trend_card)
        self.trend_layout.setContentsMargins(16,16,16,16); self.trend_layout.setSpacing(0)
        self.trend_layout.addWidget(QLabel('🔥  Trending Tags', styleSheet=f"font-size:11px;font-weight:700;color:{TEXT_MUTED};letter-spacing:0.5px;border:none;background:transparent;"))
        rv.addWidget(self.trend_card)

        self.mood_card = make_card()
        ml = QVBoxLayout(self.mood_card); ml.setContentsMargins(16,16,16,16); ml.setSpacing(8)
        ml.addWidget(QLabel('😊  Campus Mood', styleSheet=f"font-size:11px;font-weight:700;color:{TEXT_MUTED};letter-spacing:0.5px;border:none;background:transparent;"))
        self.mood_bars = {}
        for sent, color, emoji in [('positive',SUCCESS,'😊'),('neutral',TEXT_MUTED,'😐'),('negative',DANGER,'😟')]:
            ml.addSpacing(4)
            row2 = QHBoxLayout()
            ll = QLabel(f'{emoji} {sent.capitalize()}')
            ll.setStyleSheet(f"font-size:12px;color:{TEXT_MID};border:none;background:transparent;")
            pl = QLabel('0%')
            pl.setStyleSheet(f"font-size:12px;font-weight:700;color:{color};border:none;background:transparent;")
            row2.addWidget(ll); row2.addStretch(); row2.addWidget(pl)
            ml.addLayout(row2)
            track = QFrame(); track.setFixedHeight(6)
            track.setStyleSheet(f"background:{BG_APP};border-radius:3px;border:none;")
            inner = QFrame(track); inner.setFixedHeight(6)
            inner.setStyleSheet(f"background:{color};border-radius:3px;border:none;")
            inner.setFixedWidth(0)
            self.mood_bars[sent] = (pl, track, inner)
            ml.addWidget(track)
        ml.addSpacing(6)
        ml.addWidget(QLabel('Powered by ML sentiment analysis', styleSheet=f"font-size:10px;color:{TEXT_MUTED};border:none;background:transparent;"))
        rv.addWidget(self.mood_card)
        rv.addStretch()
        root.addWidget(right)

    def _load(self):
        while self.feed_vbox.count() > 1:
            item = self.feed_vbox.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        result = api('GET', '/posts/', params={'user_id': self.user['id']})
        posts  = result.get('posts', [])

        if not posts:
            empty = QLabel('No posts yet.\nBe the first to share something!')
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{TEXT_MUTED};font-size:14px;padding:60px 20px;background:transparent;border:none;")
            self.feed_vbox.insertWidget(0, empty)
        else:
            for i, post in enumerate(posts):
                pc = PostCard(post, self.user)
                pc.post_deleted.connect(lambda pid: self._load())
                self.feed_vbox.insertWidget(i, pc)

        self._load_trending()
        self._load_mood()

    def _load_trending(self):
        while self.trend_layout.count() > 1:
            item = self.trend_layout.takeAt(1)
            if item.widget(): item.widget().deleteLater()
        result = api('GET', '/trending/')
        tags   = result.get('tags', [])
        if not tags:
            self.trend_layout.addWidget(QLabel('No tags yet', styleSheet=f"font-size:12px;color:{TEXT_MUTED};border:none;background:transparent;padding:8px 0;"))
        else:
            for t in tags:
                self.trend_layout.addSpacing(8)
                row3 = QHBoxLayout()
                tl = QLabel(f"# {t['course_tag']}")
                tl.setStyleSheet(f"font-size:13px;font-weight:600;color:{PRIMARY};border:none;background:transparent;")
                cl = QLabel(f"{t['count']} post{'s' if t['count']!=1 else ''}")
                cl.setStyleSheet(f"font-size:11px;color:{TEXT_MUTED};border:none;background:transparent;")
                row3.addWidget(tl); row3.addStretch(); row3.addWidget(cl)
                wrap = QWidget(); wrap.setStyleSheet("background:transparent;"); wrap.setLayout(row3)
                self.trend_layout.addWidget(wrap)

    def _load_mood(self):
        result = api('GET', '/sentiment-today/')
        for s, (pl, track, inner) in self.mood_bars.items():
            val = result.get(s, 0)
            pl.setText(f'{val}%')
            w = max(int(track.width() * val / 100), 0) if track.width() > 0 else 0
            inner.setFixedWidth(w)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._load_mood()


# ── Bookmarks Page ─────────────────────────────────────────────────────────────

class BookmarksPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{BG_APP};")
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(16)
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel('🔖  Saved Posts', styleSheet=f"font-size:20px;font-weight:700;color:{TEXT_DARK};border:none;background:transparent;"))
        hdr.addStretch()
        ref = QPushButton('↻  Refresh')
        ref.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ref.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXT_MID};border:1.5px solid {BORDER};border-radius:16px;padding:6px 14px;font-size:12px;}}QPushButton:hover{{background:{PRIMARY_LITE};color:{PRIMARY};border-color:{PRIMARY_MID};}}")
        ref.clicked.connect(self.load)
        hdr.addWidget(ref)
        layout.addLayout(hdr)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:transparent;border:none;")
        self.inner = QWidget(); self.inner.setStyleSheet("background:transparent;")
        self.vbox  = QVBoxLayout(self.inner)
        self.vbox.setContentsMargins(0,0,0,0); self.vbox.setSpacing(16); self.vbox.addStretch()
        self.scroll.setWidget(self.inner)
        layout.addWidget(self.scroll, 1)

    def load(self):
        while self.vbox.count() > 1:
            item = self.vbox.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        result = api('GET', '/bookmarks/', params={'user_id': self.user['id']})
        posts  = result.get('posts', [])
        if not posts:
            empty = QLabel('Nothing saved yet.\nBookmark posts to see them here.')
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{TEXT_MUTED};font-size:14px;padding:60px 20px;background:transparent;border:none;")
            self.vbox.insertWidget(0, empty)
        else:
            for i, post in enumerate(posts):
                pc = PostCard(post, self.user)
                pc.bookmark_changed.connect(lambda pid, bm: self.load() if not bm else None)
                self.vbox.insertWidget(i, pc)


# ── Stats Page ─────────────────────────────────────────────────────────────────

class StatsPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{BG_APP};")
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(20)
        layout.addWidget(QLabel('📊  Statistics', styleSheet=f"font-size:22px;font-weight:700;color:{TEXT_DARK};border:none;background:transparent;"))
        layout.addWidget(QLabel('Campus activity at a glance', styleSheet=f"font-size:13px;color:{TEXT_MUTED};border:none;background:transparent;"))
        result = api('GET', '/stats/')
        row = QHBoxLayout(); row.setSpacing(14)
        for emoji, label, value, color in [
            ('📝','Total Posts',str(result.get('total_posts',0)),PRIMARY),
            ('👥','Active Students',str(result.get('active_users',0)),SUCCESS),
            ('🏷️','Top Tag',result.get('top_tag','N/A'),ACCENT),
            ('↗','Total Shares',str(result.get('total_shares',0)),DANGER),
        ]:
            c = make_card(); cl = QVBoxLayout(c); cl.setContentsMargins(18,18,18,18); cl.setSpacing(6)
            cl.addWidget(QLabel(emoji, styleSheet=f"font-size:22px;border:none;background:transparent;"))
            cl.addWidget(QLabel(value, styleSheet=f"font-size:26px;font-weight:800;color:{color};border:none;background:transparent;"))
            cl.addWidget(QLabel(label, styleSheet=f"font-size:11px;color:{TEXT_MUTED};font-weight:600;border:none;background:transparent;"))
            row.addWidget(c)
        layout.addLayout(row)
        try:
            import matplotlib; matplotlib.use('Agg')
            import matplotlib.pyplot as plt, io
            daily = result.get('daily_posts', [])
            fig, ax = plt.subplots(figsize=(6,3))
            fig.patch.set_facecolor('white')
            if daily:
                dates  = [r['date'] for r in daily]
                counts = [r['count'] for r in daily]
                bars   = ax.bar(dates, counts, color=PRIMARY, width=0.6, zorder=3)
                ax.set_xticklabels(dates, rotation=30, ha='right', fontsize=8)
                for bar in bars:
                    h = bar.get_height()
                    if h > 0:
                        ax.text(bar.get_x()+bar.get_width()/2., h+0.1, str(int(h)), ha='center', va='bottom', fontsize=8, color=PRIMARY)
            else:
                ax.text(0.5, 0.5, 'No data yet', ha='center', va='center', transform=ax.transAxes, color=TEXT_MUTED)
            ax.set_title('Posts per Day — Last 7 Days', fontsize=11, fontweight='bold', color=TEXT_DARK, pad=12)
            ax.set_ylabel('Posts', fontsize=9, color=TEXT_MUTED)
            ax.grid(axis='y', alpha=0.3, zorder=0)
            ax.spines[['top','right','left']].set_visible(False)
            ax.tick_params(colors=TEXT_MUTED)
            fig.tight_layout()
            buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=110, bbox_inches='tight'); plt.close(fig); buf.seek(0)
            pix = QPixmap(); pix.loadFromData(buf.read())
            cc = make_card(); ccl = QVBoxLayout(cc); ccl.setContentsMargins(16,16,16,16)
            il = QLabel(); il.setPixmap(pix); ccl.addWidget(il)
            layout.addWidget(cc)
        except Exception:
            layout.addWidget(QLabel('Install matplotlib for charts: pip install matplotlib', styleSheet=f"color:{TEXT_MUTED};font-size:12px;border:none;background:transparent;"))
        layout.addStretch()


# ── Auth Pages ─────────────────────────────────────────────────────────────────

class LoginPage(QWidget):
    login_success = pyqtSignal(dict)
    go_register   = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {BG_SIDEBAR},stop:0.6 #1E2A5E,stop:1 #1A6ED8);")
        outer = QVBoxLayout(self); outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c = QFrame(); c.setFixedWidth(420)
        c.setStyleSheet(f"QFrame{{background:{WHITE};border:none;border-radius:20px;}}")
        cl = QVBoxLayout(c); cl.setContentsMargins(36,36,36,36); cl.setSpacing(16)
        r = QHBoxLayout(); r.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r.addWidget(QLabel('AUPP', styleSheet=f"font-size:28px;font-weight:900;color:{PRIMARY};border:none;background:transparent;letter-spacing:-1px;"))
        r.addWidget(QLabel('Connect', styleSheet=f"font-size:28px;font-weight:900;color:{TEXT_DARK};border:none;background:transparent;letter-spacing:-1px;"))
        cl.addLayout(r)
        cl.addWidget(QLabel('Welcome back! Sign in to continue.', styleSheet=f"font-size:13px;color:{TEXT_MUTED};border:none;background:transparent;", alignment=Qt.AlignmentFlag.AlignCenter))
        self.err = QLabel(); self.err.setStyleSheet(f"background:#FEF2F2;color:{DANGER};border:1px solid #FECACA;border-radius:10px;padding:10px 14px;font-size:12px;")
        self.err.setVisible(False); self.err.setWordWrap(True); cl.addWidget(self.err)
        self.email = QLineEdit(); self.email.setPlaceholderText('📧  Email address')
        self.password = QLineEdit(); self.password.setPlaceholderText('🔒  Password')
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        cl.addWidget(self.email); cl.addWidget(self.password)
        btn = QPushButton('Sign In  →'); btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); btn.setFixedHeight(46)
        btn.setStyleSheet(f"QPushButton{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {PRIMARY},stop:1 #2E8BF0);color:white;border:none;border-radius:23px;font-size:15px;font-weight:700;}}QPushButton:hover{{background:{PRIMARY_DARK};}}")
        btn.clicked.connect(self._login); self.password.returnPressed.connect(self._login); cl.addWidget(btn)
        lnk = QLabel("Don't have an account? <a href='#' style='color:#1A6ED8;font-weight:600;'>Create one</a>")
        lnk.setAlignment(Qt.AlignmentFlag.AlignCenter); lnk.setStyleSheet(f"font-size:12px;color:{TEXT_MUTED};border:none;background:transparent;")
        lnk.linkActivated.connect(lambda: self.go_register.emit()); cl.addWidget(lnk); outer.addWidget(c)

    def _login(self):
        email = self.email.text().strip(); pwd = self.password.text()
        if not email or not pwd: self.err.setText('Please enter your email and password.'); self.err.setVisible(True); return
        result = api('POST', '/login/', {'email': email, 'password': pwd})
        if result.get('ok'): self.login_success.emit(result['user'])
        else: self.err.setText(result.get('error','Login failed.')); self.err.setVisible(True)


class RegisterPage(QWidget):
    register_success = pyqtSignal()
    go_login         = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {BG_SIDEBAR},stop:0.6 #1E2A5E,stop:1 #1A6ED8);")
        outer = QVBoxLayout(self); outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c = QFrame(); c.setFixedWidth(460)
        c.setStyleSheet(f"QFrame{{background:{WHITE};border:none;border-radius:20px;}}")
        cl = QVBoxLayout(c); cl.setContentsMargins(36,32,36,32); cl.setSpacing(12)
        cl.addWidget(QLabel('Create Account', styleSheet=f"font-size:22px;font-weight:800;color:{TEXT_DARK};border:none;background:transparent;", alignment=Qt.AlignmentFlag.AlignCenter))
        self.err = QLabel(); self.err.setStyleSheet(f"background:#FEF2F2;color:{DANGER};border:1px solid #FECACA;border-radius:10px;padding:10px 14px;font-size:12px;")
        self.err.setVisible(False); self.err.setWordWrap(True); cl.addWidget(self.err)
        r1 = QHBoxLayout()
        self.first = QLineEdit(); self.first.setPlaceholderText('First name')
        self.last  = QLineEdit(); self.last.setPlaceholderText('Last name')
        r1.addWidget(self.first); r1.addWidget(self.last); cl.addLayout(r1)
        self.email = QLineEdit(); self.email.setPlaceholderText('Email address')
        self.uname = QLineEdit(); self.uname.setPlaceholderText('Username')
        self.pwd   = QLineEdit(); self.pwd.setPlaceholderText('Password (min 6 chars)'); self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd2  = QLineEdit(); self.pwd2.setPlaceholderText('Confirm password'); self.pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        for w in [self.email, self.uname, self.pwd, self.pwd2]: cl.addWidget(w)
        r2 = QHBoxLayout()
        self.dept = QComboBox()
        for code, name in _meta['departments'].items(): self.dept.addItem(name, code)
        self.year = QComboBox()
        for y in range(1,5): self.year.addItem(f'Year {y}', y)
        r2.addWidget(self.dept); r2.addWidget(self.year); cl.addLayout(r2)
        btn = QPushButton('Create Account  →'); btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); btn.setFixedHeight(46)
        btn.setStyleSheet(f"QPushButton{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {PRIMARY},stop:1 #2E8BF0);color:white;border:none;border-radius:23px;font-size:15px;font-weight:700;}}QPushButton:hover{{background:{PRIMARY_DARK};}}")
        btn.clicked.connect(self._register); cl.addWidget(btn)
        lnk = QLabel("Already have an account? <a href='#' style='color:#1A6ED8;font-weight:600;'>Sign in</a>")
        lnk.setAlignment(Qt.AlignmentFlag.AlignCenter); lnk.setStyleSheet(f"font-size:12px;color:{TEXT_MUTED};border:none;background:transparent;")
        lnk.linkActivated.connect(lambda: self.go_login.emit()); cl.addWidget(lnk); outer.addWidget(c)

    def _register(self):
        first=self.first.text().strip(); last=self.last.text().strip()
        email=self.email.text().strip(); uname=self.uname.text().strip()
        pwd=self.pwd.text(); pwd2=self.pwd2.text()
        if not all([first,last,email,uname,pwd]): self.err.setText('All fields are required.'); self.err.setVisible(True); return
        if pwd != pwd2: self.err.setText('Passwords do not match.'); self.err.setVisible(True); return
        if len(pwd) < 6: self.err.setText('Password must be at least 6 characters.'); self.err.setVisible(True); return
        result = api('POST', '/register/', {'email':email,'username':uname,'first_name':first,'last_name':last,'password':pwd,'department':self.dept.currentData(),'year_level':self.year.currentData()})
        if result.get('ok'): self.register_success.emit()
        else: self.err.setText(result.get('error','Registration failed.')); self.err.setVisible(True)


# ── Main Window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('AUPP Connect')
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        self.current_user = None
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.login_page = LoginPage()
        self.login_page.login_success.connect(self._on_login)
        self.login_page.go_register.connect(lambda: self.stack.setCurrentIndex(1))
        self.register_page = RegisterPage()
        self.register_page.register_success.connect(lambda: self.stack.setCurrentIndex(0))
        self.register_page.go_login.connect(lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.login_page)    # 0
        self.stack.addWidget(self.register_page) # 1
        self.stack.setCurrentIndex(0)

    def _on_login(self, user):
        self.current_user = user
        self._build_app()

    def _build_app(self):
        root = QWidget(); root.setStyleSheet(f"background:{BG_APP};")
        hl = QHBoxLayout(root); hl.setContentsMargins(0,0,0,0); hl.setSpacing(0)
        self.sidebar = Sidebar(self.current_user)
        self.sidebar.nav_changed.connect(self._nav)
        hl.addWidget(self.sidebar)
        self.pages = QStackedWidget(); self.pages.setStyleSheet(f"background:{BG_APP};")
        self.feed_page      = FeedPage(self.current_user)
        self.bookmarks_page = BookmarksPage(self.current_user)
        self.stats_page     = StatsPage(self.current_user)

        def wrap(w):
            sa = QScrollArea(); sa.setWidgetResizable(True); sa.setStyleSheet("background:transparent;border:none;")
            ww = QWidget(); ww.setStyleSheet("background:transparent;")
            wl = QVBoxLayout(ww); wl.setContentsMargins(28,24,28,24); wl.addWidget(w)
            sa.setWidget(ww); return sa

        self.pages.addWidget(wrap(self.feed_page))
        self.pages.addWidget(wrap(self.bookmarks_page))
        self.pages.addWidget(wrap(self.stats_page))
        hl.addWidget(self.pages, 1)
        self.stack.addWidget(root)
        self.stack.setCurrentWidget(root)

    def _nav(self, key):
        if key == 'logout':
            self.current_user = None; self.stack.setCurrentIndex(0)
        elif key == 'feed':
            self.pages.setCurrentIndex(0); self.feed_page._load()
        elif key == 'bookmarks':
            self.pages.setCurrentIndex(1); self.bookmarks_page.load()
        elif key == 'stats':
            self.pages.setCurrentIndex(2)


# ── Entry ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    load_metadata()
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
#!/usr/bin/env python3
## make sure to have PyQt6 and minecraft-launcher-lib installed on your crrent machine or else it would not work

import sys, os, re, json, math, shutil, hashlib, uuid, zipfile, shlex, time
from pathlib import Path

try:
    import minecraft_launcher_lib as mll
    from PyQt6.QtCore import (Qt, QThread, QTimer, QProcess, QEvent, QUrl, QPointF, QFile,
                              pyqtSignal)
    from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QRadialGradient, QDesktopServices
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit, QComboBox,
        QCheckBox, QSlider, QProgressBar, QListWidget, QListWidgetItem, QPlainTextEdit,
        QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QButtonGroup, QFileDialog,
        QMessageBox)
except ImportError as e:
    sys.exit(f"Missing dependency ({e}).\nInstall with:  pip install minecraft-launcher-lib PyQt6")

APP_VERSION = "1.0"
HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "sculk-launcher"
CONF = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "sculk-launcher" / "config.json"
SHARED_ROOT = DATA / "minecraft"          # versions / libraries / assets for launcher-made instances
OWN_INSTANCES = DATA / "instances"
CACHE = DATA / "versions-cache.json"      # lets the Download page work with no network

KINDS = [("mods", "Mods"), ("shaderpacks", "Shaders"), ("resourcepacks", "Resource packs")]
KIND_LABEL = {"mods": ("mod", "mods"), "shaderpacks": ("shader", "shaders"),
              "resourcepacks": ("resource pack", "resource packs")}
SOURCE_LABEL = {"own": "Sculk", "vanilla": "Official launcher", "prism": "Prism / MultiMC",
                "modrinth": "Modrinth App", "curseforge": "CurseForge", "custom": "Mapped folder"}

# ------------------------------------------------------------------ palette
DEEPSLATE, PANEL, VEIN = "#0a0f12", "#10181d", "#1c2b31"
SCULK, SCULK_DIM = "#3be8f0", "#0f3b45"
BONE, MOSS, EMBER = "#cfe0e3", "#6d8b91", "#ff6b57"

STYLE = f"""
* {{ font-family:"Inter","Noto Sans","Cantarell","DejaVu Sans",sans-serif; font-size:13px; color:{BONE}; }}
QMainWindow {{ background:{DEEPSLATE}; }}
QToolTip {{ background:{PANEL}; color:{BONE}; border:1px solid {SCULK}; padding:4px 6px; }}
QLabel#title {{ font-size:24px; font-weight:700; color:#eefcfd; }}
QLabel#name {{ font-size:22px; font-weight:700; color:#eefcfd; }}
QLabel#dim {{ color:{MOSS}; font-size:12px; }}
QLabel#toast {{ color:{SCULK}; font-size:12px; }}
QLabel#field {{ color:#8fb0b6; font-size:12px; }}
QLabel#zone {{ border:1px dashed #2a6670; background:rgba(59,232,240,0.04); color:#7fe9ee;
              padding:20px; font-size:14px; }}
QLabel#zone:hover {{ border-color:{SCULK}; background:rgba(59,232,240,0.09); }}
QFrame#side {{ background:rgba(6,10,12,0.84); border-right:1px solid #16242a; }}
QFrame#card {{ background:rgba(14,22,27,0.88); border:1px solid {VEIN}; }}
QFrame#card QLabel {{ border:none; background:transparent; }}
QPushButton {{ background:#0e161b; border:1px solid {VEIN}; padding:8px 16px; }}
QPushButton:hover {{ border-color:{SCULK}; color:#eefcfd; }}
QPushButton:pressed {{ background:{SCULK_DIM}; }}
QPushButton:disabled {{ color:#3a4f55; border-color:#141f24; }}
QPushButton#nav {{ text-align:left; padding:13px 20px; border:none; border-left:3px solid transparent;
                  background:transparent; color:#7c9aa0; font-size:14px; }}
QPushButton#nav:hover {{ color:#eefcfd; background:rgba(59,232,240,0.06); }}
QPushButton#nav:checked {{ color:{SCULK}; border-left:3px solid {SCULK}; background:rgba(59,232,240,0.10); }}
QPushButton#tab {{ border:none; border-bottom:2px solid transparent; background:transparent; padding:8px 18px;
                  color:#7c9aa0; font-size:14px; }}
QPushButton#tab:hover {{ color:#eefcfd; }}
QPushButton#tab:checked {{ color:{SCULK}; border-bottom:2px solid {SCULK}; }}
QPushButton#play {{ background:{SCULK_DIM}; border:1px solid {SCULK}; color:#eefcfd; font-size:20px;
                   font-weight:700; padding:14px 64px; }}
QPushButton#play:hover {{ background:#145664; }}
QPushButton#danger:hover {{ border-color:{EMBER}; color:#ff9a8c; }}
QLineEdit, QComboBox, QPlainTextEdit, QListWidget {{ background:rgba(8,13,16,0.92); border:1px solid {VEIN};
    padding:6px 8px; selection-background-color:#145664; selection-color:#ffffff; }}
QLineEdit:focus, QComboBox:focus {{ border-color:{SCULK}; }}
QComboBox::drop-down {{ border:none; width:24px; }}
QComboBox QAbstractItemView {{ background:#0b1216; border:1px solid {SCULK}; selection-background-color:#145664;
    outline:0; padding:0; }}
QPlainTextEdit#console {{ font-family:"JetBrains Mono","DejaVu Sans Mono",monospace; font-size:11px; color:#80a6ac; }}
QListWidget {{ padding:0; outline:0; }}
QListWidget::item {{ padding:9px 12px; border-bottom:1px solid #131e24; }}
QListWidget::item:selected {{ background:{SCULK_DIM}; color:#ffffff; }}
QListWidget::item:hover:!selected {{ background:#0e222a; }}
QListWidget::indicator {{ width:14px; height:14px; border:1px solid #2d4650; background:#0b1216; }}
QListWidget::indicator:checked {{ background:{SCULK}; border-color:{SCULK}; }}
QSlider::groove:horizontal {{ height:4px; background:{VEIN}; }}
QSlider::sub-page:horizontal {{ background:{SCULK}; }}
QSlider::handle:horizontal {{ background:#eefcfd; width:12px; margin:-6px 0; border:1px solid {SCULK}; }}
QProgressBar {{ background:#0b1216; border:1px solid {VEIN}; max-height:8px; min-height:8px; text-align:center; color:transparent; }}
QProgressBar::chunk {{ background:{SCULK}; }}
QCheckBox {{ spacing:8px; }}
QCheckBox::indicator {{ width:14px; height:14px; border:1px solid #2d4650; background:#0b1216; }}
QCheckBox::indicator:checked {{ background:{SCULK}; border-color:{SCULK}; }}
QScrollBar:vertical {{ background:transparent; width:9px; margin:0; }}
QScrollBar::handle:vertical {{ background:{VEIN}; min-height:30px; }}
QScrollBar::handle:vertical:hover {{ background:{SCULK}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QMessageBox {{ background:{PANEL}; }}
"""


# ------------------------------------------------------------------ helpers
def offline_uuid(name: str) -> str:
    """Same UUID the vanilla client derives for an offline player name."""
    import hashlib as _h
    return str(uuid.UUID(bytes=_h.md5(("OfflinePlayer:" + name).encode()).digest(), version=3))


def total_ram_mb() -> int:
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 8192


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def iid(path) -> str:
    return hashlib.sha1(str(path).encode()).hexdigest()[:10]


def open_path(p):
    Path(p).mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))


def trash(path) -> bool:
    try:
        r = QFile.moveToTrash(str(path))
        return bool(r[0] if isinstance(r, tuple) else r)
    except Exception:
        return False


def classify(path: Path):
    """Decide where a dropped file belongs: mods / shaderpacks / resourcepacks / 'modpack' / None."""
    ext = path.suffix.lower()
    if ext == ".mrpack":
        return "modpack"
    if path.is_dir():
        if (path / "shaders").is_dir() and not (path / "assets").is_dir():
            return "shaderpacks"
        if (path / "pack.mcmeta").exists() or (path / "assets").is_dir():
            return "resourcepacks"
        return None
    if ext == ".jar":
        return "mods"
    if ext == ".zip":
        try:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
        except (zipfile.BadZipFile, OSError):
            return None
        tops, nested = set(), set()
        for n in names:
            parts = n.split("/")
            tops.add(parts[0])
            if len(parts) > 1 and parts[1]:
                nested.add(parts[1])
        seen = tops | nested
        if "shaders" in seen and "assets" not in seen:
            return "shaderpacks"
        if "pack.mcmeta" in seen or "assets" in seen:
            return "resourcepacks"
    return None


# ------------------------------------------------------------------ config
class Config:
    DEFAULTS = {"username": "Steve", "last": None, "custom": [], "hidden": [], "overrides": {},
                "java": "", "jvm_extra": "-XX:+UseG1GC"}

    def __init__(self):
        self.d = json.loads(json.dumps(self.DEFAULTS))
        try:
            self.d.update(json.loads(CONF.read_text()))
        except Exception:
            pass

    def save(self):
        CONF.parent.mkdir(parents=True, exist_ok=True)
        CONF.write_text(json.dumps(self.d, indent=2))

    def ov(self, inst_id):
        return self.d["overrides"].get(inst_id, {})

    def set_ov(self, inst_id, **kw):
        self.d["overrides"].setdefault(inst_id, {}).update(kw)
        self.save()


# ------------------------------------------------------------------ instance discovery
def mk(name, source, game_dir, root, mc=None, loader="vanilla", lv=None, pinned=None):
    return {"id": iid(game_dir), "name": name, "source": source, "game_dir": str(game_dir),
            "root": str(root), "mc_version": mc, "loader": loader, "loader_ver": lv, "pinned": pinned}


def prism_instance(d: Path):
    cfg = d / "instance.cfg"
    if not cfg.exists():
        return None
    name = d.name
    for line in cfg.read_text(errors="ignore").splitlines():
        if line.startswith("name="):
            name = line[5:].strip() or name
    gd = next((d / x for x in (".minecraft", "minecraft") if (d / x).is_dir()), d / ".minecraft")
    mc, loader, lv = None, "vanilla", None
    try:
        for c in json.loads((d / "mmc-pack.json").read_text()).get("components", []):
            uid, ver = c.get("uid"), c.get("version")
            if uid == "net.minecraft":
                mc = ver
            elif uid == "net.fabricmc.fabric-loader":
                loader, lv = "fabric", ver
            elif uid == "org.quiltmc.quilt-loader":
                loader, lv = "quilt", ver
            elif uid == "net.minecraftforge":
                loader, lv = "forge", ver
            elif uid == "net.neoforged":
                loader, lv = "neoforge", ver
    except Exception:
        pass
    return mk(name, "prism", gd, SHARED_ROOT, mc, loader, lv)


def curse_instance(d: Path):
    f = d / "minecraftinstance.json"
    if not f.exists():
        return None
    try:
        j = json.loads(f.read_text())
    except Exception:
        j = {}
    mc, loader, lv = j.get("gameVersion"), "vanilla", None
    m = re.match(r"(fabric|forge|quilt|neoforge)-(.+)", (j.get("baseModLoader") or {}).get("name", ""), re.I)
    if m:
        loader, lv = m.group(1).lower(), m.group(2)
        if mc and lv.endswith("-" + mc):
            lv = lv[: -len(mc) - 1]
    return mk(j.get("name") or d.name, "curseforge", d, SHARED_ROOT, mc, loader, lv)


def inst_from_path(p: Path):
    if not p.is_dir():
        return None
    return (prism_instance(p) or curse_instance(p)
            or mk(p.name, "custom", p, p if (p / "versions").is_dir() else SHARED_ROOT))


def scan_instances(cfg: Config):
    out = []
    if OWN_INSTANCES.is_dir():
        for f in sorted(OWN_INSTANCES.glob("*/instance.json")):
            try:
                m = json.loads(f.read_text())
            except Exception:
                continue
            out.append(mk(m.get("name", f.parent.name), "own", f.parent / "game", SHARED_ROOT,
                          m.get("mc_version"), m.get("loader", "vanilla"), m.get("loader_ver"), m.get("pinned")))
    for p, label in ((HOME / ".minecraft", "Default .minecraft"),
                     (HOME / ".var/app/com.mojang.Minecraft/.minecraft", "Flatpak .minecraft")):
        if p.is_dir():
            out.append(mk(label, "vanilla", p, p))
    prism_roots = [HOME / ".local/share/PrismLauncher/instances",
                   HOME / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances",
                   HOME / ".local/share/multimc/instances", HOME / ".local/share/MultiMC/instances",
                   HOME / "MultiMC/instances", HOME / ".local/share/PolyMC/instances"]
    for r in prism_roots:
        if r.is_dir():
            for d in sorted(r.iterdir()):
                if d.is_dir() and not d.name.startswith("_"):
                    i = prism_instance(d)
                    if i:
                        out.append(i)
    for r in (HOME / ".local/share/ModrinthApp/profiles",
              HOME / ".var/app/com.modrinth.ModrinthApp/data/ModrinthApp/profiles"):
        if r.is_dir():
            for d in sorted(r.iterdir()):
                if d.is_dir():
                    out.append(mk(d.name, "modrinth", d, SHARED_ROOT))
    cf = HOME / "curseforge/minecraft/Instances"
    if cf.is_dir():
        for d in sorted(cf.iterdir()):
            i = d.is_dir() and curse_instance(d)
            if i:
                out.append(i)
    for c in cfg.d["custom"]:
        i = inst_from_path(Path(c))
        if i:
            out.append(i)
    seen, final = set(), []
    for i in out:
        if i["id"] not in seen and i["id"] not in cfg.d["hidden"]:
            seen.add(i["id"])
            final.append(i)
    return final


def unique_instance_dir(name: str) -> Path:
    safe = re.sub(r"[^\w .\-]", "_", name).strip(" .") or "instance"
    d, n = OWN_INSTANCES / safe, 2
    while d.exists():
        d = OWN_INSTANCES / f"{safe}-{n}"
        n += 1
    return d


def write_instance(folder: Path, meta: dict):
    (folder / "game").mkdir(parents=True, exist_ok=True)
    (folder / "instance.json").write_text(json.dumps(meta, indent=2))
    return folder / "game"


# ------------------------------------------------------------------ install logic (runs in threads)
def installed_ids(root):
    """Version folders that contain their json. Scanned by hand so one odd custom version can't hide the rest."""
    vdir = Path(root) / "versions"
    try:
        return sorted((d.name for d in vdir.iterdir() if (d / f"{d.name}.json").is_file()), reverse=True)
    except OSError:
        return []


def find_installed(root, mc, loader, lv):
    ids = installed_ids(root)
    if loader == "vanilla":
        return mc if mc in ids else None
    if lv:
        try:
            v = mll.mod_loader.get_mod_loader(loader).get_installed_version(mc, lv)
            return v if v in ids else None
        except Exception:
            return None
    key = {"fabric": "fabric-loader-", "quilt": "quilt-loader-"}.get(loader)
    cand = []
    for i in ids:
        low = i.lower()
        if mc not in i:
            continue
        if key and i.startswith(key) and i.endswith("-" + mc):
            cand.append(i)
        elif not key and loader in low and (loader != "forge" or "neoforge" not in low):
            cand.append(i)
    return sorted(cand)[-1] if cand else None


def ensure_loader(root, mc, loader, lv, cb):
    root = str(root)
    found = find_installed(root, mc, loader, lv)
    if found:
        return found
    if loader == "vanilla":
        mll.install.install_minecraft_version(mc, root, callback=cb)
        return mc
    ml = mll.mod_loader.get_mod_loader(loader)
    if not ml.is_minecraft_version_supported(mc):
        raise RuntimeError(f"{loader} has no build for Minecraft {mc}")
    return ml.install(mc, root, loader_version=lv, callback=cb)


def prepare_version(root, sel, mc, loader, lv, cb):
    """Resolve what to launch, installing whatever is missing, then verify files (best effort, offline-safe)."""
    vid = sel if sel and sel != "AUTO" else ensure_loader(root, mc, loader, lv, cb)
    try:
        mll.install.install_minecraft_version(vid, str(root), callback=cb)
    except Exception as e:
        cb["setStatus"](f"File check skipped ({type(e).__name__}); launching from local files")
    return vid


class Task(QThread):
    status = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        mx = [1]
        cb = {"setStatus": lambda t: self.status.emit(str(t)),
              "setMax": lambda m: mx.__setitem__(0, max(1, int(m))),
              "setProgress": lambda v: self.progress.emit(int(v), mx[0])}
        try:
            self.done.emit(self.fn(cb))
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")


class ManifestTask(QThread):
    got = pyqtSignal(list, str)

    def run(self):
        try:
            data = [{"id": v["id"], "type": v["type"], "time": str(v.get("releaseTime", ""))}
                    for v in mll.utils.get_version_list()]
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(data))
            self.got.emit(data, "live")
        except Exception:
            try:
                self.got.emit(json.loads(CACHE.read_text()), "cached")
            except Exception:
                self.got.emit([], "none")


# ------------------------------------------------------------------ custom widgets
GLYPHS = {
    "S": [".####", "#....", ".###.", "....#", "####."],
    "C": [".####", "#....", "#....", "#....", ".####"],
    "U": ["#...#", "#...#", "#...#", "#...#", ".###."],
    "L": ["#....", "#....", "#....", "#....", "#####"],
    "K": ["#...#", "#..#.", "###..", "#..#.", "#...#"],
}


class Wordmark(QWidget):
    """Pixel-built wordmark that flares when the launcher 'hears' something."""
    CELL = 6

    def __init__(self, text="SCULK"):
        super().__init__()
        self.text, self.glow = text, 0.0
        self.setFixedSize(len(text) * 6 * self.CELL, 5 * self.CELL + 2)
        self.t = QTimer(self)
        self.t.timeout.connect(self._decay)

    def pulse(self):
        self.glow = 1.0
        self.t.start(40)

    def _decay(self):
        self.glow = max(0.0, self.glow - 0.05)
        if self.glow == 0:
            self.t.stop()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        c = self.CELL
        for li, ch in enumerate(self.text):
            for r, row in enumerate(GLYPHS[ch]):
                for col, v in enumerate(row):
                    if v != "#":
                        continue
                    k = r / 4
                    base = QColor(int(59 - 30 * k), int(232 - 85 * k), int(240 - 80 * k))
                    lift = 1 + 0.9 * self.glow * (1 - abs(((li * 5 + col) % 7) - 3) / 4)
                    base = QColor(min(255, int(base.red() * lift)), min(255, int(base.green() * lift)),
                                  min(255, int(base.blue() * lift)))
                    p.fillRect(li * 6 * c + col * c, r * c, c - 1, c - 1, base)


class SculkBG(QWidget):
    """Deepslate grid. Events send pixel-ring vibrations across it. Idle = no animation, no CPU."""
    CELL = 24

    def __init__(self):
        super().__init__()
        self.ripples = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def ripple(self, pos: QPointF, strength=1.0):
        self.ripples.append([pos.x(), pos.y(), 0.0, strength])
        if not self.timer.isActive():
            self.timer.start(33)

    def _limit(self):
        return math.hypot(self.width(), self.height()) * 0.75

    def _tick(self):
        lim = self._limit()
        for r in self.ripples:
            r[2] += 13
        self.ripples = [r for r in self.ripples if r[2] < lim]
        if not self.ripples:
            self.timer.stop()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        w, h, C = self.width(), self.height(), self.CELL
        p.fillRect(self.rect(), QColor(DEEPSLATE))
        g = QRadialGradient(QPointF(w * 0.12, h * 1.08), w * 0.85)
        g.setColorAt(0, QColor(59, 232, 240, 46))
        g.setColorAt(1, QColor(59, 232, 240, 0))
        p.fillRect(self.rect(), QBrush(g))
        p.setPen(QPen(QColor(59, 232, 240, 11), 1))
        for x in range(0, w, C):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, C):
            p.drawLine(0, y, w, y)
        p.setPen(Qt.PenStyle.NoPen)
        lim = self._limit()
        for cx, cy, rad, s in self.ripples:
            fade = max(0.0, 1 - rad / lim)
            n = max(12, int(2 * math.pi * rad / C * 2))
            cells = set()
            for i in range(n):
                a = 2 * math.pi * i / n
                cells.add((int((cx + rad * math.cos(a)) // C), int((cy + rad * math.sin(a)) // C)))
            for gx, gy in cells:
                p.fillRect(gx * C + 1, gy * C + 1, C - 1, C - 1, QColor(59, 232, 240, int(120 * fade * s)))


class DropOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.target = ""
        self.hide()

    def begin(self, target):
        self.target = target
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()

    def end(self):
        self.hide()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(5, 12, 15, 150))
        r = self.rect().adjusted(26, 26, -26, -26)
        p.setPen(QPen(QColor(SCULK), 2, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(r)
        f = QFont(self.font())
        f.setPixelSize(30)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#eefcfd"))
        p.drawText(r.adjusted(0, -20, 0, -20), Qt.AlignmentFlag.AlignCenter, f"Release to add to {self.target}")
        f.setPixelSize(14)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor("#8fd9de"))
        p.drawText(r.adjusted(0, 50, 0, 50), Qt.AlignmentFlag.AlignCenter,
                   "Mods, shaders, resource packs and .mrpack modpacks are sorted automatically")


class ClickLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, e):
        self.clicked.emit()


def field(text):
    l = QLabel(text)
    l.setObjectName("field")
    return l


def dim(text=""):
    l = QLabel(text)
    l.setObjectName("dim")
    l.setWordWrap(True)
    return l


# ------------------------------------------------------------------ pages
class PlayPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.proc = win, None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        g = QGridLayout(card)
        g.setContentsMargins(22, 20, 22, 20)
        g.setHorizontalSpacing(18)
        g.setVerticalSpacing(10)
        self.name = QLabel("No instance")
        self.name.setObjectName("name")
        self.path = dim()
        g.addWidget(self.name, 0, 0, 1, 2)
        g.addWidget(self.path, 1, 0, 1, 2)
        self.version = QComboBox()
        self.user = QLineEdit(win.cfg.d["username"])
        self.user.setMaxLength(16)
        self.user.setPlaceholderText("Offline player name")
        g.addWidget(field("Version"), 2, 0)
        g.addWidget(field("Player name (offline)"), 2, 1)
        g.addWidget(self.version, 3, 0)
        g.addWidget(self.user, 3, 1)
        self.demo = QCheckBox("Demo mode: Mojang's official free trial build")
        g.addWidget(self.demo, 4, 0, 1, 2)
        self.ram = QSlider(Qt.Orientation.Horizontal)
        total = total_ram_mb()
        self.ram.setRange(2, max(4, (total - 1024) // 512))
        self.ram.setPageStep(2)
        self.ram_lbl = QLabel()
        self.ram_lbl.setMinimumWidth(60)
        row = QHBoxLayout()
        row.addWidget(self.ram, 1)
        row.addWidget(self.ram_lbl)
        g.addWidget(field("Memory"), 5, 0, 1, 2)
        g.addLayout(row, 6, 0, 1, 2)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        lay.addWidget(card)

        row = QHBoxLayout()
        self.play = QPushButton("Play")
        self.play.setObjectName("play")
        self.play.clicked.connect(self.on_play)
        row.addWidget(self.play)
        self.status = dim()
        row.addWidget(self.status, 1)
        lay.addLayout(row)

        self.console = QPlainTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(4000)
        self.console.setPlaceholderText("Game output appears here.")
        lay.addWidget(self.console, 1)

        self.version.currentIndexChanged.connect(self._save_version)
        self.ram.valueChanged.connect(self._save_ram)
        self.demo.toggled.connect(self._save_demo)
        self.user.editingFinished.connect(self._save_user)

    # -- state
    def refresh(self):
        inst = self.win.current_instance()
        for w in (self.version, self.ram, self.demo):
            w.blockSignals(True)
        self.version.clear()
        if not inst:
            self.name.setText("No instance yet")
            self.path.setText("Map an existing one in Instances, or install a version in Download.")
            self.version.addItem("Nothing to launch", None)
            self.play.setEnabled(False)
        else:
            self.play.setEnabled(True)
            ov = self.win.cfg.ov(inst["id"])
            self.name.setText(inst["name"])
            self.path.setText(f"{SOURCE_LABEL.get(inst['source'], inst['source'])}   {inst['game_dir']}")
            if inst["mc_version"]:
                self.version.addItem(f"Auto: {inst['mc_version']} {inst['loader']}", "AUTO")
            for v in installed_ids(inst["root"]):
                self.version.addItem(v, v)
            if self.version.count() == 0:
                self.version.addItem("No versions installed (see Download)", None)
            want = ov.get("version") or inst.get("pinned")
            idx = self.version.findData(want) if want else -1
            self.version.setCurrentIndex(max(0, idx))
            default_ram = 4096 if total_ram_mb() >= 7000 else max(1024, total_ram_mb() // 2 // 512 * 512)
            self.ram.setValue(max(self.ram.minimum(), min(self.ram.maximum(), ov.get("ram", default_ram) // 512)))
            self.demo.setChecked(bool(ov.get("demo", False)))
        self.ram_lbl.setText(f"{self.ram.value() * 512 / 1024:g} GB")
        for w in (self.version, self.ram, self.demo):
            w.blockSignals(False)

    def _inst_id(self):
        i = self.win.current_instance()
        return i["id"] if i else None

    def _save_version(self):
        d, i = self.version.currentData(), self._inst_id()
        if i and d:
            self.win.cfg.set_ov(i, version=d)

    def _save_ram(self, v):
        self.ram_lbl.setText(f"{v * 512 / 1024:g} GB")
        if self._inst_id():
            self.win.cfg.set_ov(self._inst_id(), ram=v * 512)

    def _save_demo(self, on):
        if self._inst_id():
            self.win.cfg.set_ov(self._inst_id(), demo=on)

    def _save_user(self):
        self.win.cfg.d["username"] = self.user.text().strip()
        self.win.cfg.save()
        self.win.update_footer()

    def log(self, text):
        self.console.appendPlainText(text.rstrip("\n"))

    # -- launching
    def on_play(self):
        if self.proc and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.proc.kill()
            return
        inst = self.win.current_instance()
        if not inst:
            return
        name = self.user.text().strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", name):
            self.win.toast("Player name needs 3 to 16 letters, digits or underscores.")
            return
        self._save_user()
        sel = self.version.currentData()
        if sel is None:
            self.win.toast("No version installed yet. Open Download to get one.")
            return
        self.win.bg.ripple(QPointF(self.play.mapTo(self.win.bg, self.play.rect().center())))
        self.win.mark.pulse()
        root, mc, loader, lv = inst["root"], inst["mc_version"], inst["loader"], inst["loader_ver"]
        self.status.setText("Checking files...")
        self.play.setEnabled(False)
        self.win.run_task(Task(lambda cb: prepare_version(root, sel, mc, loader, lv, cb)),
                          lambda vid: self.launch(inst, vid), on_fail=self._reset)

    def _reset(self, *_):
        self.play.setEnabled(True)
        self.play.setText("Play")
        self.status.setText("")

    def launch(self, inst, vid):
        cfg, ov = self.win.cfg, self.win.cfg.ov(inst["id"])
        gd = Path(inst["game_dir"])
        gd.mkdir(parents=True, exist_ok=True)
        name, demo = self.user.text().strip(), self.demo.isChecked()
        try:
            extra = shlex.split(cfg.d["jvm_extra"])
        except ValueError:
            extra = []
        opts = {"username": name, "uuid": offline_uuid(name), "token": "", "gameDirectory": str(gd),
                "jvmArguments": [f"-Xmx{self.ram.value() * 512}M", "-Xms512M"] + extra,
                "launcherName": "sculk-launcher", "launcherVersion": APP_VERSION, "demo": demo}
        if cfg.d["java"]:
            opts["executablePath"] = cfg.d["java"]
        try:
            cmd = mll.command.get_minecraft_command(vid, inst["root"], opts)
        except Exception as e:
            self.log(f"[launcher] could not build the launch command: {e}")
            self.win.toast("Launch command failed. See the console.")
            self._reset()
            return
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.setWorkingDirectory(str(gd))
        self.proc.readyRead.connect(lambda: self.log(bytes(self.proc.readAll()).decode(errors="replace")))
        self.proc.finished.connect(self._finished)
        self.proc.errorOccurred.connect(lambda e: self.log(f"[launcher] process error: {e.name}"))
        self.log(f"[launcher] {vid} as {name}{' (demo)' if demo else ''}")
        self.proc.start(cmd[0], cmd[1:])
        self.play.setEnabled(True)
        self.play.setText("Stop")
        self.status.setText(f"Running {vid}")

    def _finished(self, code, _status):
        self.log(f"[launcher] game exited with code {code}")
        self.win.toast(f"Game closed (exit code {code}).")
        self.win.mark.pulse()
        self._reset()


class InstancesPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        self.info = dim()
        lay.addWidget(self.info)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._picked)
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        for text, fn, obj in (("Rescan", win.rescan, None), ("Map a folder...", self.map_folder, None),
                              ("Open folder", self.open_folder, None), ("Remove", self.remove, "danger")):
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(lambda _=False, f=fn: f())
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

    def refresh(self):
        self.list.blockSignals(True)
        self.list.clear()
        cur = self.win.cfg.d["last"]
        for i in self.win.instances:
            ver = f"{i['mc_version']} {i['loader']}" if i["mc_version"] else "version chosen at launch"
            it = QListWidgetItem(f"{i['name']}\n{SOURCE_LABEL.get(i['source'], i['source'])}   {ver}   {i['game_dir']}")
            it.setData(Qt.ItemDataRole.UserRole, i["id"])
            self.list.addItem(it)
            if i["id"] == cur:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        n = len(self.win.instances)
        self.info.setText(f"{n} instance{'s' if n != 1 else ''} found. Existing launchers are mapped in place; "
                          "nothing is copied or changed until you launch or drop files into them.")

    def _picked(self, item, _prev):
        if item:
            self.win.set_current(item.data(Qt.ItemDataRole.UserRole), from_list=True)

    def map_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Pick an instance or game folder", str(HOME))
        if d:
            if d not in self.win.cfg.d["custom"]:
                self.win.cfg.d["custom"].append(d)
            if iid(d) in self.win.cfg.d["hidden"]:
                self.win.cfg.d["hidden"].remove(iid(d))
            self.win.cfg.save()
            self.win.rescan(select=iid(d))

    def open_folder(self):
        i = self.win.current_instance()
        if i:
            open_path(i["game_dir"])

    def remove(self):
        i = self.win.current_instance()
        if not i:
            return
        if i["source"] == "own":
            if QMessageBox.question(self, "Move to trash", f"Move “{i['name']}” and everything in it to the trash?\n"
                                    "Worlds and mods inside it go too.") != QMessageBox.StandardButton.Yes:
                return
            if trash(Path(i["game_dir"]).parent):
                self.win.toast(f"{i['name']} moved to the trash.")
            else:
                self.win.toast("Could not move it to the trash. Delete the folder by hand.")
        else:
            self.win.cfg.d["hidden"].append(i["id"])
            if i["game_dir"] in self.win.cfg.d["custom"]:
                self.win.cfg.d["custom"].remove(i["game_dir"])
            self.win.cfg.save()
            self.win.toast(f"{i['name']} hidden. Its files were not touched (Settings can unhide).")
        self.win.rescan()


class LibraryPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.kind = win, "mods"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        tabs = QHBoxLayout()
        self.group = QButtonGroup(self)
        for k, label in KINDS:
            b = QPushButton(label)
            b.setObjectName("tab")
            b.setCheckable(True)
            b.setChecked(k == "mods")
            b.clicked.connect(lambda _=False, kk=k: self.set_kind(kk))
            self.group.addButton(b)
            tabs.addWidget(b)
        tabs.addStretch(1)
        lay.addLayout(tabs)
        self.zone = ClickLabel("Drop files here, or anywhere on this window.\nClick to browse instead.")
        self.zone.setObjectName("zone")
        self.zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zone.clicked.connect(self.browse)
        lay.addWidget(self.zone)
        self.where = dim()
        lay.addWidget(self.where)
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list.itemChanged.connect(self._toggled)
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        for text, fn, obj in (("Open folder", self.open_folder, None), ("Refresh", self.refresh, None),
                              ("Remove selected", self.remove, "danger")):
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(lambda _=False, f=fn: f())
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

    def set_kind(self, k):
        self.kind = k
        self.refresh()

    def folder(self):
        i = self.win.current_instance()
        return Path(i["game_dir"]) / self.kind if i else None

    def refresh(self):
        self.list.blockSignals(True)
        self.list.clear()
        f = self.folder()
        if not f:
            self.where.setText("Pick an instance first.")
        else:
            self.where.setText(str(f))
            entries = sorted(f.iterdir(), key=lambda p: p.name.lower()) if f.is_dir() else []
            for p in entries:
                if p.name.startswith("."):
                    continue
                size = "folder" if p.is_dir() else fmt_size(p.stat().st_size)
                it = QListWidgetItem(f"{p.name}      {size}")
                it.setData(Qt.ItemDataRole.UserRole, str(p))
                if self.kind == "mods" and p.is_file() and (p.suffix == ".jar" or p.name.endswith(".jar.disabled")):
                    it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    it.setCheckState(Qt.CheckState.Unchecked if p.name.endswith(".disabled") else Qt.CheckState.Checked)
                self.list.addItem(it)
            if not entries:
                self.where.setText(f"{f}   (empty)")
        self.list.blockSignals(False)

    def _toggled(self, item):
        p = Path(item.data(Qt.ItemDataRole.UserRole))
        try:
            if item.checkState() == Qt.CheckState.Checked and p.name.endswith(".disabled"):
                p.rename(p.with_name(p.name[:-9]))
            elif item.checkState() == Qt.CheckState.Unchecked and not p.name.endswith(".disabled"):
                p.rename(p.with_name(p.name + ".disabled"))
        except OSError as e:
            self.win.toast(f"Could not toggle {p.name}: {e}")
        QTimer.singleShot(0, self.refresh)

    def browse(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Add files", str(HOME / "Downloads"))
        if files:
            self.win.handle_drop([Path(f) for f in files])

    def open_folder(self):
        f = self.folder()
        if f:
            open_path(f)

    def remove(self):
        items = self.list.selectedItems()
        if not items:
            return
        if QMessageBox.question(self, "Move to trash", f"Move {len(items)} item(s) to the trash?") \
                != QMessageBox.StandardButton.Yes:
            return
        bad = sum(0 if trash(it.data(Qt.ItemDataRole.UserRole)) else 1 for it in items)
        self.win.toast(f"Removed {len(items) - bad}." + (f" {bad} could not be trashed." if bad else ""))
        self.refresh()


class DownloadPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.versions, self.loaded = win, [], False
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(18)

        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search versions, like 1.20.1")
        self.search.textChanged.connect(self.fill)
        left.addWidget(self.search)
        row = QHBoxLayout()
        self.chk = {}
        for key, label, on in (("release", "Releases", True), ("snapshot", "Snapshots", False), ("old", "Old alpha and beta", False)):
            c = QCheckBox(label)
            c.setChecked(on)
            c.toggled.connect(self.fill)
            self.chk[key] = c
            row.addWidget(c)
        row.addStretch(1)
        left.addLayout(row)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._picked)
        left.addWidget(self.list, 1)
        self.src = dim()
        left.addWidget(self.src)
        lay.addLayout(left, 3)

        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(22, 20, 22, 20)
        v.setSpacing(8)
        self.sel = QLabel("Pick a version")
        self.sel.setObjectName("name")
        v.addWidget(self.sel)
        v.addWidget(dim("Files come straight from Mojang's servers. Once installed the launcher needs no network."))
        v.addSpacing(8)
        v.addWidget(field("Mod loader"))
        self.loader = QComboBox()
        for label, key in (("Vanilla", "vanilla"), ("Fabric", "fabric"), ("Quilt", "quilt"), ("Forge", "forge"), ("NeoForge", "neoforge")):
            self.loader.addItem(label, key)
        v.addWidget(self.loader)
        v.addWidget(field("Instance name"))
        self.iname = QLineEdit()
        v.addWidget(self.iname)
        self.demo = QCheckBox("Free demo build (Mojang's official trial, no account needed)")
        self.demo.setChecked(True)
        v.addWidget(self.demo)
        v.addSpacing(6)
        self.btn = QPushButton("Install and create instance")
        self.btn.setObjectName("play")
        self.btn.setStyleSheet("font-size:15px; padding:12px 18px;")
        self.btn.setEnabled(False)
        self.btn.clicked.connect(self.install)
        v.addWidget(self.btn)
        v.addStretch(1)
        lay.addWidget(card, 2)

    def on_show(self):
        if not self.loaded:
            self.loaded = True
            self.src.setText("Loading version list...")
            self.mt = ManifestTask()
            self.mt.got.connect(self._got)
            self.mt.start()

    def _got(self, data, how):
        self.versions = data
        self.src.setText({"live": f"{len(data)} versions from Mojang.",
                          "cached": f"Offline: showing the cached list of {len(data)} versions.",
                          "none": "Offline and no cached list yet. Connect once to fetch it."}[how])
        self.fill()

    def fill(self, *_):
        self.list.clear()
        q = self.search.text().strip().lower()
        allowed = set()
        if self.chk["release"].isChecked():
            allowed.add("release")
        if self.chk["snapshot"].isChecked():
            allowed.add("snapshot")
        if self.chk["old"].isChecked():
            allowed |= {"old_beta", "old_alpha"}
        for v in self.versions:
            if v["type"] in allowed and q in v["id"].lower():
                it = QListWidgetItem(v["id"] if v["type"] == "release" else f"{v['id']}   ({v['type'].replace('_', ' ')})")
                it.setData(Qt.ItemDataRole.UserRole, v["id"])
                self.list.addItem(it)

    def _picked(self, item, _):
        if item:
            vid = item.data(Qt.ItemDataRole.UserRole)
            self.sel.setText(f"Minecraft {vid}")
            self.iname.setText(vid)
            self.btn.setEnabled(True)

    def install(self):
        it = self.list.currentItem()
        if not it:
            return
        mc, loader = it.data(Qt.ItemDataRole.UserRole), self.loader.currentData()
        name = self.iname.text().strip() or mc
        demo = self.demo.isChecked()
        self.btn.setEnabled(False)

        def done(vid):
            folder = unique_instance_dir(name)
            game = write_instance(folder, {"name": name, "mc_version": mc, "loader": loader, "loader_ver": None, "pinned": vid})
            if demo:
                self.win.cfg.set_ov(iid(game), demo=True)
            self.btn.setEnabled(True)
            self.win.toast(f"{name} is ready.")
            self.win.bg.ripple(QPointF(self.win.bg.width() * 0.6, self.win.bg.height() * 0.5), 1.4)
            self.win.rescan(select=iid(game))
            self.win.go("play")

        self.win.run_task(Task(lambda cb: ensure_loader(SHARED_ROOT, mc, loader, None, cb)), done,
                          on_fail=lambda *_: self.btn.setEnabled(True))


class SettingsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(22, 20, 22, 20)
        v.setSpacing(8)
        v.addWidget(field("Java executable (leave empty to use the one Minecraft ships with)"))
        row = QHBoxLayout()
        self.java = QLineEdit(win.cfg.d["java"])
        self.java.setPlaceholderText("/usr/lib/jvm/java-21-openjdk/bin/java")
        b = QPushButton("Browse...")
        b.clicked.connect(self.pick_java)
        row.addWidget(self.java, 1)
        row.addWidget(b)
        v.addLayout(row)
        v.addWidget(field("Extra JVM arguments"))
        self.args = QLineEdit(win.cfg.d["jvm_extra"])
        v.addWidget(self.args)
        row = QHBoxLayout()
        for text, fn in (("Save", self.save), ("Open launcher data folder", lambda: open_path(DATA)),
                         ("Unhide all instances", self.unhide)):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, f=fn: f())
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        lay.addWidget(card)
        lay.addWidget(dim(
            "How accounts work here: the launcher signs in offline with the player name from the Play page. "
            "That is enough for singleplayer, LAN and servers that run in offline mode. Servers that check Mojang "
            "accounts will refuse it, and this launcher does nothing to get around that. "
            "Demo mode is Mojang's own free trial build and needs no account at all."))
        lay.addStretch(1)

    def pick_java(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choose java", "/usr/lib/jvm")
        if f:
            self.java.setText(f)

    def save(self):
        self.win.cfg.d["java"] = self.java.text().strip()
        self.win.cfg.d["jvm_extra"] = self.args.text().strip()
        self.win.cfg.save()
        self.win.toast("Settings saved.")

    def unhide(self):
        self.win.cfg.d["hidden"] = []
        self.win.cfg.save()
        self.win.rescan()
        self.win.toast("All instances are visible again.")


# ------------------------------------------------------------------ main window
class Main(QMainWindow):
    PAGES = [("play", "Play"), ("instances", "Instances"), ("library", "Library"),
             ("download", "Download"), ("settings", "Settings")]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sculk Launcher")
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)
        self.setAcceptDrops(True)
        self.cfg, self.instances, self.worker, self._keep = Config(), [], None, []
        self._last_rip = 0.0

        self.bg = SculkBG()
        self.setCentralWidget(self.bg)
        self.overlay = DropOverlay(self.bg)
        root = QHBoxLayout(self.bg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sidebar
        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(230)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 26, 0, 18)
        sv.setSpacing(2)
        self.mark = Wordmark()
        wrap = QHBoxLayout()
        wrap.setContentsMargins(22, 0, 0, 0)
        wrap.addWidget(self.mark)
        wrap.addStretch(1)
        sv.addLayout(wrap)
        sub = dim("offline launcher")
        sub.setContentsMargins(24, 6, 0, 22)
        sv.addWidget(sub)
        self.nav = QButtonGroup(self)
        self.nav_btns = {}
        for i, (key, label) in enumerate(self.PAGES):
            b = QPushButton(label)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.go(k))
            self.nav.addButton(b)
            self.nav_btns[key] = b
            sv.addWidget(b)
        sv.addStretch(1)
        self.footer = dim()
        self.footer.setContentsMargins(24, 0, 12, 0)
        sv.addWidget(self.footer)
        root.addWidget(side)

        # right column
        right = QVBoxLayout()
        right.setContentsMargins(30, 24, 30, 16)
        right.setSpacing(14)
        head = QHBoxLayout()
        tv = QVBoxLayout()
        tv.setSpacing(2)
        self.title = QLabel("Play")
        self.title.setObjectName("title")
        self.toast_lbl = QLabel("")
        self.toast_lbl.setObjectName("toast")
        self.toast_lbl.setWordWrap(True)
        tv.addWidget(self.title)
        tv.addWidget(self.toast_lbl)
        head.addLayout(tv, 1)
        head.addWidget(field("Instance"))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(300)
        self.combo.currentIndexChanged.connect(self._combo_changed)
        head.addWidget(self.combo)
        right.addLayout(head)

        self.stack = QStackedWidget()
        self.pages = {"play": PlayPage(self), "instances": InstancesPage(self), "library": LibraryPage(self),
                      "download": DownloadPage(self), "settings": SettingsPage(self)}
        for k, _ in self.PAGES:
            self.stack.addWidget(self.pages[k])
        right.addWidget(self.stack, 1)

        bar = QHBoxLayout()
        self.task_lbl = dim()
        self.task_bar = QProgressBar()
        self.task_bar.setFixedWidth(260)
        bar.addWidget(self.task_lbl, 1)
        bar.addWidget(self.task_bar)
        self.task_lbl.hide()
        self.task_bar.hide()
        right.addLayout(bar)
        root.addLayout(right, 1)

        self._toast_t = QTimer(self)
        self._toast_t.setSingleShot(True)
        self._toast_t.timeout.connect(lambda: self.toast_lbl.setText(""))
        self._leave = QTimer(self)
        self._leave.setSingleShot(True)
        self._leave.timeout.connect(self.overlay.end)
        QApplication.instance().installEventFilter(self)

        self.rescan()
        self.go("play")

    # -- navigation / state
    def go(self, key):
        self.nav_btns[key].setChecked(True)
        self.stack.setCurrentWidget(self.pages[key])
        self.title.setText(dict(self.PAGES)[key])
        page = self.pages[key]
        for fn in ("refresh", "on_show"):
            if hasattr(page, fn):
                getattr(page, fn)()

    def current_instance(self):
        cur = self.cfg.d["last"]
        for i in self.instances:
            if i["id"] == cur:
                return i
        return self.instances[0] if self.instances else None

    def rescan(self, select=None):
        self.instances = scan_instances(self.cfg)
        if select:
            self.cfg.d["last"] = select
        self.combo.blockSignals(True)
        self.combo.clear()
        for i in self.instances:
            self.combo.addItem(f"{i['name']}  ({SOURCE_LABEL.get(i['source'], i['source'])})", i["id"])
        cur = self.current_instance()
        if cur:
            self.cfg.d["last"] = cur["id"]
            self.combo.setCurrentIndex(self.combo.findData(cur["id"]))
        self.combo.blockSignals(False)
        self.cfg.save()
        self.pages["instances"].refresh()
        self.pages["play"].refresh()
        self.pages["library"].refresh()
        self.update_footer()

    def set_current(self, inst_id, from_list=False):
        self.cfg.d["last"] = inst_id
        self.cfg.save()
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(self.combo.findData(inst_id))
        self.combo.blockSignals(False)
        self.pages["play"].refresh()
        self.pages["library"].refresh()
        if not from_list:
            self.pages["instances"].refresh()

    def _combo_changed(self, idx):
        d = self.combo.itemData(idx)
        if d:
            self.set_current(d)

    def update_footer(self):
        self.footer.setText(f"Signed in offline as {self.cfg.d['username'] or 'Steve'}")

    def toast(self, text):
        self.toast_lbl.setText(text)
        self._toast_t.start(7000)

    # -- background tasks
    def run_task(self, worker, on_done, on_fail=None):
        if self.worker is not None:
            self.toast("Another install is still running.")
            if on_fail:
                on_fail("busy")
            return
        self.worker = worker
        self._keep.append(worker)
        worker.finished.connect(lambda w=worker: self._keep.remove(w) if w in self._keep else None)
        self.task_lbl.setText("Working...")
        self.task_bar.setRange(0, 0)
        self.task_lbl.show()
        self.task_bar.show()
        worker.status.connect(self.task_lbl.setText)
        worker.progress.connect(self._progress)

        def finish():
            self.worker = None
            self.task_lbl.hide()
            self.task_bar.hide()

        def ok(res):
            finish()
            self.bg.ripple(QPointF(self.bg.width() * 0.5, self.bg.height() * 0.5), 0.8)
            on_done(res)

        def bad(msg):
            finish()
            self.pages["play"].log(f"[launcher] {msg}")
            self.toast(f"Failed: {msg[:140]}")
            if on_fail:
                on_fail(msg)

        worker.done.connect(ok)
        worker.failed.connect(bad)
        worker.start()

    def _progress(self, v, m):
        self.task_bar.setRange(0, m)
        self.task_bar.setValue(min(v, m))

    # -- drag and drop (handled app-wide so no child widget can swallow a drop)
    def eventFilter(self, obj, ev):
        if not isinstance(obj, QWidget) or obj.window() is not self:
            return False
        t = ev.type()
        if t in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            if ev.mimeData().hasUrls():
                ev.acceptProposedAction()
                self._leave.stop()
                if not self.overlay.isVisible():
                    cur = self.current_instance()
                    self.overlay.begin(cur["name"] if cur else "your instance")
                now = time.monotonic()
                if now - self._last_rip > 0.5:
                    self._last_rip = now
                    self.bg.ripple(QPointF(obj.mapTo(self.bg, ev.position().toPoint())))
                return True
        elif t == QEvent.Type.DragLeave:
            self._leave.start(150)
        elif t == QEvent.Type.Drop:
            if ev.mimeData().hasUrls():
                self.overlay.end()
                ev.acceptProposedAction()
                paths = [Path(u.toLocalFile()) for u in ev.mimeData().urls() if u.isLocalFile()]
                QTimer.singleShot(0, lambda: self.handle_drop(paths))
                return True
        return False

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.overlay.setGeometry(self.bg.rect())

    def handle_drop(self, paths):
        inst = self.current_instance()
        if not inst:
            self.toast("No instance to drop into. Map one in Instances or install one in Download.")
            return
        lib = self.pages["library"]
        fallback = lib.kind if self.stack.currentWidget() is lib else None
        counts, notes = {}, []
        for p in paths:
            kind = classify(p) or fallback
            if kind == "modpack":
                self.import_mrpack(p)
                continue
            if not kind:
                notes.append(f"Skipped {p.name}: not sure what it is. Open the right Library tab and drop it again.")
                continue
            dest_dir = Path(inst["game_dir"]) / kind
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dst = dest_dir / p.name
                if p.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(p, dst)
                else:
                    shutil.copy2(p, dst)
                counts[kind] = counts.get(kind, 0) + 1
            except OSError as e:
                notes.append(f"{p.name}: {e.strerror or e}")
        if counts:
            msg = ", ".join(f"{n} {KIND_LABEL[k][n != 1]}" for k, n in counts.items())
            self.toast(f"Added {msg} to {inst['name']}." + (" " + notes[0] if notes else ""))
            self.mark.pulse()
        elif notes:
            self.toast(notes[0])
        lib.refresh()

    def import_mrpack(self, path: Path):
        try:
            info = mll.mrpack.get_mrpack_information(str(path))
        except Exception as e:
            self.toast(f"Could not read {path.name}: {e}")
            return
        name = info["name"]
        folder = unique_instance_dir(name)
        game = folder / "game"

        def job(cb):
            game.mkdir(parents=True, exist_ok=True)
            mll.mrpack.install_mrpack(str(path), str(SHARED_ROOT), modpack_directory=str(game), callback=cb)
            return mll.mrpack.get_mrpack_launch_version(str(path))

        def done(vid):
            write_instance(folder, {"name": name, "mc_version": None, "loader": "vanilla", "loader_ver": None, "pinned": vid})
            self.toast(f"Modpack {name} installed.")
            self.rescan(select=iid(game))
            self.go("play")

        self.toast(f"Installing modpack {name}...")
        self.run_task(Task(job), done)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("sculk-launcher")
    app.setStyleSheet(STYLE)
    w = Main()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

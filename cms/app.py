#!/usr/bin/env python3
# Swan Clinic CMS — đơn giản cho nhân viên cập nhật nội dung website
# Chạy: uvicorn app:app --host 127.0.0.1 --port 8300
import os, json, uuid, hashlib, hmac, time, re, shutil
from datetime import date
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware
from PIL import Image, ImageOps

# ==== cấu hình ====
CONTENT_DIR = os.environ.get("SWAN_CONTENT", "/var/www/swanclinic/content")
UPLOAD_DIR  = os.path.join(CONTENT_DIR, "uploads")
DATA_DIR    = os.environ.get("SWAN_CMS_DATA", "/opt/swan-cms/data")   # users.json + secret (ngoài web root)
MAX_UPLOAD  = 10 * 1024 * 1024
CATS = {"1": "Tin tức Swan Clinic", "2": "Giáo dục sức khỏe & Làm đẹp", "3": "Chính sách, pháp luật y tế"}
DOCTORS = {"quang": "ThS.BSCKI Nguyễn Bá Quang", "loc": "BSCKI Trần Đức Lộc", "hieu": "BSCKI Nguyễn Trung Hiếu"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def _secret():
    p = os.path.join(DATA_DIR, "secret")
    if not os.path.exists(p):
        with open(p, "w") as f: f.write(uuid.uuid4().hex + uuid.uuid4().hex)
    return open(p).read().strip()

def jload(path, default):
    try:
        with open(path) as f: return json.load(f)
    except Exception:
        return default

def jsave(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f: json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

P_SITE    = os.path.join(CONTENT_DIR, "site.json")
P_NEWS    = os.path.join(CONTENT_DIR, "news.json")
P_DOCTORS = os.path.join(CONTENT_DIR, "doctors.json")
P_TEXTS   = os.path.join(CONTENT_DIR, "texts.json")
P_USERS   = os.path.join(DATA_DIR, "users.json")

LANGS = [("vi","Tiếng Việt"),("en","English"),("th","ไทย (Thái)"),("zh","中文 (Trung)"),("fr","Français (Pháp)"),("ko","한국어 (Hàn)"),("km","ខ្មែរ (Campuchia)")]

# (key, nhãn hiển thị, ô lớn?) — nhóm theo mục trên website
EDITABLE = [
 ("— TRANG ĐẦU (HERO) —", None, False),
 ("hero.eyebrow","Dòng nhỏ trên tiêu đề",False),
 ("hero.title","Tiêu đề lớn (cho phép <em>, <br>)",True),
 ("hero.lead","Đoạn mô tả",True),
 ("hero.cta2","Nút 1 (Đặt lịch tư vấn)",False),
 ("hero.cta1","Nút 2 (Khám phá dịch vụ)",False),
 ("— DẢI SỐ LIỆU —", None, False),
 ("trust.1a","Ô 1 — chữ lớn",False),("trust.1b","Ô 1 — chữ nhỏ",False),
 ("trust.2a","Ô 2 — chữ lớn",False),("trust.2b","Ô 2 — chữ nhỏ",False),
 ("trust.3b","Ô 3 — chữ nhỏ (dưới 98%)",False),
 ("trust.4a","Ô 4 — chữ lớn",False),("trust.4b","Ô 4 — chữ nhỏ",False),
 ("— GIỚI THIỆU —", None, False),
 ("about.title","Tiêu đề (cho phép <br>)",True),
 ("about.body","Đoạn giới thiệu",True),
 ("about.p1b","Điểm 1 — đậm",False),("about.p1s","Điểm 1 — mô tả",False),
 ("about.p2b","Điểm 2 — đậm",False),("about.p2s","Điểm 2 — mô tả",False),
 ("about.p3b","Điểm 3 — đậm",False),("about.p3s","Điểm 3 — mô tả",False),
 ("— DỊCH VỤ —", None, False),
 ("svc.title","Tiêu đề mục",False),("svc.sub","Mô tả mục",True),
 ("svc.tiem_h","Tiêm thẩm mỹ — tên",False),("svc.tiem_p","Tiêm thẩm mỹ — mô tả",True),
 ("svc.cang_h","Căng chỉ — tên",False),("svc.cang_p","Căng chỉ — mô tả",True),
 ("svc.mui_h","Nâng mũi — tên",False),("svc.mui_p","Nâng mũi — mô tả",True),
 ("svc.mi_h","Mắt/mí — tên",False),("svc.mi_p","Mắt/mí — mô tả",True),
 ("svc.nguc_h","Nâng ngực — tên",False),("svc.nguc_p","Nâng ngực — mô tả",True),
 ("svc.hutmo_h","Hút mỡ — tên",False),("svc.hutmo_p","Hút mỡ — mô tả",True),
 ("svc.note","Ghi chú (bệnh viện hợp tác)",True),
 ("svc.cap1","Ảnh dịch vụ 1 — chú thích",False),("svc.cap2","Ảnh dịch vụ 2 — chú thích",False),
 ("svc.cap3","Ảnh dịch vụ 3 — chú thích",False),("svc.cap4","Ảnh dịch vụ 4 — chú thích",False),
 ("— KHÔNG GIAN —", None, False),
 ("gal.title","Tiêu đề mục",False),("gal.sub","Mô tả mục",True),
 ("gal.cap1","Ảnh 1 — chú thích",False),("gal.cap2","Ảnh 2 — chú thích",False),
 ("gal.cap3","Ảnh 3 — chú thích",False),("gal.cap4","Ảnh 4 — chú thích",False),
 ("— BẢNG GIÁ —", None, False),
 ("price.title","Tiêu đề mục",False),("price.sub","Mô tả mục",True),
 ("price.tiem_d","Tiêm thẩm mỹ — mô tả",False),("price.cang_d","Căng chỉ — mô tả",False),
 ("price.mui_d","Nâng mũi — mô tả",False),("price.mi_d","Mắt/mí — mô tả",False),
 ("price.nguc_d","Nâng ngực — mô tả",False),("price.hutmo_d","Hút mỡ — mô tả",False),
 ("price.note_a","Ghi chú cuối bảng (phần đầu)",True),
 ("— ĐỘI NGŨ BÁC SĨ —", None, False),
 ("doc.title","Tiêu đề mục",False),("doc.sub","Mô tả mục",True),
 ("doc.d1_spec","BS Quang — chuyên môn",False),("doc.d1_bio","BS Quang — giới thiệu",True),
 ("doc.d2_spec","BS Lộc — chuyên môn",False),("doc.d2_bio","BS Lộc — giới thiệu",True),
 ("doc.d3_spec","BS Hiếu — chuyên môn",False),("doc.d3_bio","BS Hiếu — giới thiệu",True),
 ("— TIN TỨC & KÊU GỌI —", None, False),
 ("news.title","Tin tức — tiêu đề",False),("news.sub","Tin tức — mô tả",True),
 ("cta.title","Dải kêu gọi — tiêu đề",False),("cta.sub","Dải kêu gọi — mô tả",True),
 ("cta.btn","Dải kêu gọi — nút",False),
 ("— LIÊN HỆ & CHÂN TRANG —", None, False),
 ("contact.title","Liên hệ — tiêu đề",False),
 ("contact.v_hours","Giờ hoạt động (cho phép <br>)",True),
 ("foot.tagline","Chân trang — mô tả",True),
]

IMAGE_SLOTS = [
 ("hero","Ảnh lớn trang đầu (quầy lễ tân)","img/hero-recep.jpg"),
 ("about","Ảnh mục Giới thiệu","img/svc-tiem.jpg"),
 ("band1","Dịch vụ — ảnh 1 (phòng phẫu thuật)","img/svc-phau2.jpg"),
 ("band2","Dịch vụ — ảnh 2 (bác sĩ)","img/svc-phau4.jpg"),
 ("band3","Dịch vụ — ảnh 3 (thủ thuật)","img/svc-phau1.jpg"),
 ("band4","Dịch vụ — ảnh 4 (chăm sóc)","img/svc-tiem.jpg"),
 ("gal1","Không gian — ảnh 1","img/gal-2.jpg"),
 ("gal2","Không gian — ảnh 2","img/gal-1.jpg"),
 ("gal3","Không gian — ảnh 3","img/gal-3.jpg"),
 ("gal4","Không gian — ảnh 4","img/gal-4.jpg"),
 ("doc_quang","Chân dung BS Quang","img/doc-quang.jpg"),
 ("doc_loc","Chân dung BS Lộc","img/doc-loc.jpg"),
 ("doc_hieu","Chân dung BS Hiếu","img/doc-hieu.jpg"),
 ("logo_header","Logo đầu trang","img/brand-dark.png"),
 ("logo_footer","Logo chân trang","img/brand-light.png"),
]

# ==== users (pbkdf2) ====
def hashpw(pw, salt=None):
    salt = salt or uuid.uuid4().hex
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
    return salt, h

def users():
    u = jload(P_USERS, None)
    if not u:  # tạo admin mặc định
        salt, h = hashpw("SwanClinic@2026")
        u = {"admin": {"salt": salt, "hash": h, "role": "admin"}}
        jsave(P_USERS, u)
    return u

def check_login(username, pw):
    u = users().get(username)
    if not u: return False
    _, h = hashpw(pw, u["salt"])
    return hmac.compare_digest(h, u["hash"])

# ==== app ====
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=_secret(), session_cookie="swancms",
                   max_age=60*60*12, same_site="lax", https_only=False)

def me(req: Request):
    return req.session.get("user")

def is_admin(req: Request):
    u = me(req)
    return u and users().get(u, {}).get("role") == "admin"

def save_upload(f: UploadFile, kind="img"):
    """Lưu file upload; ảnh được resize + nén. Trả về đường dẫn tương đối từ web root."""
    raw = f.file.read()
    if len(raw) > MAX_UPLOAD:
        raise ValueError("File quá lớn (tối đa 10MB)")
    ext = os.path.splitext(f.filename or "")[1].lower()
    uid = uuid.uuid4().hex[:12]
    if kind == "pdf" and ext == ".pdf":
        name = f"{uid}.pdf"
        with open(os.path.join(UPLOAD_DIR, name), "wb") as out: out.write(raw)
        return f"content/uploads/{name}"
    # ảnh
    from io import BytesIO
    im = Image.open(BytesIO(raw)); im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "P") and ext == ".png":
        if im.width > 1600: im = im.resize((1600, int(im.height*1600/im.width)), Image.LANCZOS)
        name = f"{uid}.png"; im.save(os.path.join(UPLOAD_DIR, name), "PNG", optimize=True)
    else:
        im = im.convert("RGB")
        if im.width > 1600: im = im.resize((1600, int(im.height*1600/im.width)), Image.LANCZOS)
        name = f"{uid}.jpg"; im.save(os.path.join(UPLOAD_DIR, name), "JPEG", quality=84, optimize=True, progressive=True)
    return f"content/uploads/{name}"

# ==== giao diện ====
CSS = """
:root{--brand:#00ADBE;--deep:#017E8C;--ink:#0C3138;--soft:#48626B;--bg:#F3FAFB;--line:#CDE8EB}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.6}
a{color:var(--deep);text-decoration:none}
.top{background:#024A56;color:#fff;padding:.8rem 1.2rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}
.top b{font-size:1.05rem}.top .u{font-size:.85rem;opacity:.9}
.tabs{display:flex;gap:.4rem;background:#fff;border-bottom:1px solid var(--line);padding:.6rem 1.2rem;flex-wrap:wrap}
.tabs a{padding:.5em 1.1em;border-radius:999px;font-weight:600;font-size:.9rem;color:var(--soft)}
.tabs a.on{background:var(--brand);color:#fff}
.wrap{max-width:960px;margin:1.4rem auto;padding:0 1rem}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:1.2rem 1.3rem;margin-bottom:1rem}
h2{font-size:1.2rem;margin-bottom:.8rem}h3{font-size:1rem;margin:.8rem 0 .4rem}
label{display:block;font-weight:600;font-size:.85rem;margin:.7rem 0 .25rem}
input[type=text],input[type=password],input[type=date],select,textarea{width:100%;padding:.6em .8em;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:.95rem}
textarea{min-height:220px;resize:vertical}
.btn{display:inline-block;background:var(--brand);color:#fff;border:0;border-radius:999px;padding:.6em 1.4em;font-weight:600;cursor:pointer;font-size:.9rem}
.btn:hover{background:var(--deep)}
.btn.gray{background:#8aa4ab}.btn.red{background:#d9534f}
.btn.sm{padding:.35em .9em;font-size:.8rem}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th,td{text-align:left;padding:.55em .6em;border-bottom:1px solid var(--line);vertical-align:middle}
.badge{display:inline-block;background:#EAF6F7;color:var(--deep);border-radius:999px;padding:.15em .7em;font-size:.72rem;font-weight:700}
.badge.off{background:#f3e3e3;color:#a33}
.thumb{height:56px;border-radius:6px;border:1px solid var(--line)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.msg{background:#e6f7ee;border:1px solid #bfe6cf;color:#1c6b3c;border-radius:8px;padding:.6em .9em;margin-bottom:1rem;font-size:.9rem}
.err{background:#fdecec;border:1px solid #f3c1c1;color:#a33}
.note{font-size:.8rem;color:var(--soft)}
.creds{display:flex;gap:.6rem;flex-wrap:wrap;margin:.4rem 0}
.creds .c{position:relative}
.creds img{height:84px;border-radius:8px;border:1px solid var(--line)}
@media(max-width:700px){.grid2{grid-template-columns:1fr}}
"""

def page(req, tab, body, msg="", err=""):
    u = me(req)
    tabs = [("news","📰 Tin tức"),("content","🌐 Nội dung"),("images","🖼 Hình ảnh"),("doctors","👨‍⚕️ Bác sĩ"),("legal","📜 Pháp lý"),("settings","⚙️ Cài đặt")]
    if is_admin(req): tabs.append(("users","👥 Tài khoản"))
    nav = "".join(f'<a href="/admin/{k}" class="{"on" if k==tab else ""}">{t}</a>' for k,t in tabs)
    m = f'<div class="msg">{msg}</div>' if msg else ""
    e = f'<div class="msg err">{err}</div>' if err else ""
    return HTMLResponse(f"""<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Swan CMS</title>
<style>{CSS}</style></head><body>
<div class="top"><b>🦢 Swan Clinic — Quản trị nội dung</b>
<span class="u">Xin chào <b>{u}</b> · <a href="/admin/logout" style="color:#9fe3ec">Đăng xuất</a> · <a href="/" target="_blank" style="color:#9fe3ec">Xem website ↗</a></span></div>
<div class="tabs">{nav}</div><div class="wrap">{m}{e}{body}</div></body></html>""")

def need_login(req):
    if not me(req):
        return RedirectResponse("/admin/login", 302)
    return None

# ==== đăng nhập ====
@app.get("/admin/login", response_class=HTMLResponse)
def login_page(req: Request, err: str = ""):
    e = '<div class="msg err">Sai tên đăng nhập hoặc mật khẩu.</div>' if err else ""
    return HTMLResponse(f"""<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Đăng nhập — Swan CMS</title>
<style>{CSS}
.login{{max-width:380px;margin:10vh auto;background:#fff;border:1px solid var(--line);border-radius:14px;padding:2rem}}
.login h1{{font-size:1.3rem;margin-bottom:1rem;text-align:center}}</style></head><body>
<div class="login"><h1>🦢 Swan Clinic CMS</h1>{e}
<form method="post" action="/admin/login">
<label>Tên đăng nhập</label><input type="text" name="username" required autofocus>
<label>Mật khẩu</label><input type="password" name="password" required>
<div style="margin-top:1.1rem;text-align:center"><button class="btn">Đăng nhập</button></div>
</form></div></body></html>""")

@app.post("/admin/login")
def do_login(req: Request, username: str = Form(...), password: str = Form(...)):
    time.sleep(0.4)  # chống brute-force thô
    if check_login(username.strip(), password):
        req.session["user"] = username.strip()
        return RedirectResponse("/admin/news", 302)
    return RedirectResponse("/admin/login?err=1", 302)

@app.get("/admin/logout")
def logout(req: Request):
    req.session.clear()
    return RedirectResponse("/admin/login", 302)

@app.get("/admin")
def root_admin(req: Request):
    return RedirectResponse("/admin/news" if me(req) else "/admin/login", 302)

# ==== TIN TỨC ====
@app.get("/admin/news", response_class=HTMLResponse)
def news_list(req: Request, msg: str = ""):
    r = need_login(req)
    if r: return r
    N = jload(P_NEWS, {"posts": []})
    rows = ""
    for p in sorted(N["posts"], key=lambda x: x.get("date",""), reverse=True):
        pub = '<span class="badge">Đang hiện</span>' if p.get("published", True) else '<span class="badge off">Đang ẩn</span>'
        cover = f'<img class="thumb" src="/{p["cover"]}">' if p.get("cover") else ""
        rows += f"""<tr><td>{cover}</td><td><b>{p['title']}</b><br><span class="note">{CATS.get(str(p.get('cat','1')),'')} · {p.get('date','')}</span></td>
        <td>{pub}</td><td style="white-space:nowrap">
        <a class="btn sm" href="/admin/news/edit/{p['id']}">Sửa</a>
        <a class="btn sm gray" href="/admin/news/toggle/{p['id']}">{'Ẩn' if p.get('published',True) else 'Hiện'}</a>
        <a class="btn sm red" href="/admin/news/delete/{p['id']}" onclick="return confirm('Xoá bài này?')">Xoá</a></td></tr>"""
    body = f"""<div class="card"><h2>Bài viết ({len(N['posts'])})
    <a class="btn" style="float:right" href="/admin/news/new">+ Viết bài mới</a></h2>
    <table><tr><th></th><th>Tiêu đề</th><th>Trạng thái</th><th></th></tr>{rows or '<tr><td colspan=4 class=note>Chưa có bài viết nào.</td></tr>'}</table></div>"""
    return page(req, "news", body, msg=msg)

def news_form(p=None):
    p = p or {}
    opts = "".join(f'<option value="{k}" {"selected" if str(p.get("cat"))==k else ""}>{v}</option>' for k,v in CATS.items())
    imgs = "".join(f'<div class="c"><img src="/{u}"><br><a class="btn sm red" href="/admin/news/rmimg/{p.get("id")}?u={u}">Xoá ảnh</a></div>' for u in p.get("images", []))
    imgs_existing = "|".join(p.get("images", []))
    return f"""<div class="card"><h2>{'Sửa bài' if p else 'Viết bài mới'}</h2>
<form method="post" enctype="multipart/form-data">
<input type="hidden" name="cover_existing" value="{p.get('cover','')}">
<input type="hidden" name="images_existing" value="{imgs_existing}">
<label>Tiêu đề *</label><input type="text" name="title" value="{p.get('title','')}" required>
<div class="grid2">
<div><label>Chuyên mục</label><select name="cat">{opts}</select></div>
<div><label>Ngày đăng</label><input type="date" name="date" value="{p.get('date', date.today().isoformat())}"></div>
</div>
<label>Ảnh bìa {'(đang có — chọn file mới để thay)' if p.get('cover') else ''}</label>
{f'<img class="thumb" src="/{p["cover"]}" style="height:80px;margin-bottom:.4rem"><br>' if p.get('cover') else ''}
<input type="file" name="cover" accept="image/*">
<label>Nội dung bài viết *</label>
<p class="note">Mỗi đoạn cách nhau 1 dòng trống. Ảnh upload thêm bên dưới sẽ hiện ở cuối bài.</p>
<textarea name="body" required>{p.get('body','')}</textarea>
<label>Thêm ảnh vào bài (chọn được nhiều ảnh)</label>
<input type="file" name="images" accept="image/*" multiple>
<div class="creds">{imgs}</div>
<label><input type="checkbox" name="published" {"checked" if p.get("published", True) else ""}> Hiển thị công khai</label>
<div style="margin-top:1rem"><button class="btn">💾 Lưu bài viết</button>
<button class="btn gray" formaction="/admin/news/preview" formtarget="_blank" formnovalidate>👁 Xem trước</button>
<a class="btn gray" href="/admin/news">Huỷ</a></div>
</form></div>"""

@app.get("/admin/news/new", response_class=HTMLResponse)
def news_new(req: Request):
    r = need_login(req)
    if r: return r
    return page(req, "news", news_form())

@app.post("/admin/news/new")
async def news_create(req: Request):
    r = need_login(req)
    if r: return r
    form = await req.form()
    N = jload(P_NEWS, {"posts": []})
    p = {"id": uuid.uuid4().hex[:10], "title": str(form.get("title","")).strip(),
         "cat": str(form.get("cat","1")), "date": str(form.get("date","")) or date.today().isoformat(),
         "body": str(form.get("body","")), "published": bool(form.get("published")),
         "cover": "", "images": []}
    c = form.get("cover")
    if c and getattr(c, "filename", ""): p["cover"] = save_upload(c)
    for f in form.getlist("images"):
        if getattr(f, "filename", ""): p["images"].append(save_upload(f))
    N["posts"].append(p); jsave(P_NEWS, N)
    return RedirectResponse("/admin/news?msg=Đã đăng bài.", 302)

@app.get("/admin/news/edit/{pid}", response_class=HTMLResponse)
def news_edit(req: Request, pid: str):
    r = need_login(req)
    if r: return r
    N = jload(P_NEWS, {"posts": []})
    p = next((x for x in N["posts"] if x["id"] == pid), None)
    if not p: return RedirectResponse("/admin/news", 302)
    return page(req, "news", news_form(p))

@app.post("/admin/news/edit/{pid}")
async def news_save(req: Request, pid: str):
    r = need_login(req)
    if r: return r
    form = await req.form()
    N = jload(P_NEWS, {"posts": []})
    p = next((x for x in N["posts"] if x["id"] == pid), None)
    if not p: return RedirectResponse("/admin/news", 302)
    p.update({"title": str(form.get("title","")).strip(), "cat": str(form.get("cat","1")),
              "date": str(form.get("date","")), "body": str(form.get("body","")),
              "published": bool(form.get("published"))})
    c = form.get("cover")
    if c and getattr(c, "filename", ""): p["cover"] = save_upload(c)
    for f in form.getlist("images"):
        if getattr(f, "filename", ""): p.setdefault("images", []).append(save_upload(f))
    jsave(P_NEWS, N)
    return RedirectResponse("/admin/news?msg=Đã lưu.", 302)

@app.get("/admin/news/toggle/{pid}")
def news_toggle(req: Request, pid: str):
    r = need_login(req)
    if r: return r
    N = jload(P_NEWS, {"posts": []})
    for p in N["posts"]:
        if p["id"] == pid: p["published"] = not p.get("published", True)
    jsave(P_NEWS, N)
    return RedirectResponse("/admin/news", 302)

@app.get("/admin/news/delete/{pid}")
def news_delete(req: Request, pid: str):
    r = need_login(req)
    if r: return r
    N = jload(P_NEWS, {"posts": []})
    N["posts"] = [p for p in N["posts"] if p["id"] != pid]
    jsave(P_NEWS, N)
    return RedirectResponse("/admin/news?msg=Đã xoá.", 302)

@app.get("/admin/news/rmimg/{pid}")
def news_rmimg(req: Request, pid: str, u: str = ""):
    r = need_login(req)
    if r: return r
    N = jload(P_NEWS, {"posts": []})
    for p in N["posts"]:
        if p["id"] == pid and u in p.get("images", []): p["images"].remove(u)
    jsave(P_NEWS, N)
    return RedirectResponse(f"/admin/news/edit/{pid}", 302)

# ==== BÁC SĨ (văn bằng & chứng chỉ) ====
@app.get("/admin/doctors", response_class=HTMLResponse)
def doctors_page(req: Request, msg: str = ""):
    r = need_login(req)
    if r: return r
    D = jload(P_DOCTORS, {})
    body = '<div class="card"><h2>Văn bằng &amp; chứng chỉ của bác sĩ</h2><p class="note">Ảnh sẽ hiện trên website ở nút "Văn bằng &amp; chứng chỉ" trong thẻ từng bác sĩ. Lưu ý làm mờ thông tin cá nhân (số CCCD, địa chỉ nhà...) trước khi upload.</p></div>'
    for key, name in DOCTORS.items():
        creds = D.get(key, {}).get("creds", [])
        imgs = "".join(f'<div class="c"><img src="/{c["img"]}"><br><a class="btn sm red" href="/admin/doctors/rm/{key}?u={c["img"]}" onclick="return confirm(\'Xoá ảnh?\')">Xoá</a></div>' for c in creds)
        body += f"""<div class="card"><h3>{name} <span class="badge">{len(creds)} ảnh</span></h3>
<div class="creds">{imgs or '<span class="note">Chưa có ảnh.</span>'}</div>
<form method="post" action="/admin/doctors/add/{key}" enctype="multipart/form-data">
<input type="file" name="files" accept="image/*" multiple required>
<button class="btn sm" style="margin-top:.5rem">⬆ Tải ảnh lên</button></form></div>"""
    return page(req, "doctors", body, msg=msg)

@app.post("/admin/doctors/add/{key}")
async def doctors_add(req: Request, key: str):
    r = need_login(req)
    if r: return r
    if key not in DOCTORS: return RedirectResponse("/admin/doctors", 302)
    form = await req.form()
    D = jload(P_DOCTORS, {})
    D.setdefault(key, {"creds": []})
    for f in form.getlist("files"):
        if getattr(f, "filename", ""):
            D[key]["creds"].append({"img": save_upload(f), "label": ""})
    jsave(P_DOCTORS, D)
    return RedirectResponse("/admin/doctors?msg=Đã tải ảnh lên.", 302)

@app.get("/admin/doctors/rm/{key}")
def doctors_rm(req: Request, key: str, u: str = ""):
    r = need_login(req)
    if r: return r
    D = jload(P_DOCTORS, {})
    if key in D:
        D[key]["creds"] = [c for c in D[key].get("creds", []) if c.get("img") != u]
    jsave(P_DOCTORS, D)
    return RedirectResponse("/admin/doctors", 302)

# ==== PHÁP LÝ ====
@app.get("/admin/legal", response_class=HTMLResponse)
def legal_page(req: Request, msg: str = ""):
    r = need_login(req)
    if r: return r
    S = jload(P_SITE, {})
    gphd = f'<img class="thumb" style="height:110px" src="/{S["gphd_image"]}"><br><a class="btn sm red" href="/admin/legal/rmgphd">Gỡ ảnh</a>' if S.get("gphd_image") else '<span class="note">Chưa có ảnh.</span>'
    kt = S.get("kythuat_file", "")
    ktv = S.get("kythuat_visible", False)
    body = f"""<div class="card"><h2>Giấy phép hoạt động (GPHĐ)</h2>
<p class="note">Đăng bản chụp GPHĐ. Nhớ che/làm mờ các thông tin cần bảo mật nội bộ trước khi upload.</p>
<div style="margin:.6rem 0">{gphd}</div>
<form method="post" action="/admin/legal/gphd" enctype="multipart/form-data">
<input type="file" name="file" accept="image/*" required>
<button class="btn sm" style="margin-top:.5rem">⬆ Tải ảnh GPHĐ</button></form></div>

<div class="card"><h2>Danh mục kỹ thuật được phê duyệt</h2>
<p class="note">Upload file (ảnh hoặc PDF). Có thể để chế độ ẨN — chỉ bật hiện khi cần.</p>
<div style="margin:.6rem 0">{f'<a href="/{kt}" target="_blank">📄 Xem file hiện tại</a> · <a class="btn sm red" href="/admin/legal/rmkt">Gỡ file</a>' if kt else '<span class="note">Chưa có file.</span>'}
&nbsp; Trạng thái: {'<span class="badge">Đang HIỆN trên web</span>' if ktv and kt else '<span class="badge off">Đang ẨN</span>'}</div>
<form method="post" action="/admin/legal/kythuat" enctype="multipart/form-data">
<input type="file" name="file" accept="image/*,.pdf">
<label><input type="checkbox" name="visible" {"checked" if ktv else ""}> Hiện trên website</label>
<button class="btn sm" style="margin-top:.5rem">💾 Lưu</button></form></div>"""
    return page(req, "legal", body, msg=msg)

@app.post("/admin/legal/gphd")
async def legal_gphd(req: Request):
    r = need_login(req)
    if r: return r
    form = await req.form()
    f = form.get("file")
    if f and getattr(f, "filename", ""):
        S = jload(P_SITE, {}); S["gphd_image"] = save_upload(f); jsave(P_SITE, S)
    return RedirectResponse("/admin/legal?msg=Đã cập nhật GPHĐ.", 302)

@app.get("/admin/legal/rmgphd")
def legal_rmgphd(req: Request):
    r = need_login(req)
    if r: return r
    S = jload(P_SITE, {}); S["gphd_image"] = ""; jsave(P_SITE, S)
    return RedirectResponse("/admin/legal", 302)

@app.post("/admin/legal/kythuat")
async def legal_kt(req: Request):
    r = need_login(req)
    if r: return r
    form = await req.form()
    S = jload(P_SITE, {})
    f = form.get("file")
    if f and getattr(f, "filename", ""):
        kind = "pdf" if str(f.filename).lower().endswith(".pdf") else "img"
        S["kythuat_file"] = save_upload(f, kind)
    S["kythuat_visible"] = bool(form.get("visible"))
    jsave(P_SITE, S)
    return RedirectResponse("/admin/legal?msg=Đã lưu.", 302)

@app.get("/admin/legal/rmkt")
def legal_rmkt(req: Request):
    r = need_login(req)
    if r: return r
    S = jload(P_SITE, {}); S["kythuat_file"] = ""; S["kythuat_visible"] = False; jsave(P_SITE, S)
    return RedirectResponse("/admin/legal", 302)

# ==== CÀI ĐẶT ====
PRICE_LABELS = {"tiem":"Tiêm thẩm mỹ","cang":"Căng chỉ","mui":"Nâng mũi","mi":"Thẩm mỹ mắt / mí","nguc":"Nâng ngực","hutmo":"Hút mỡ"}

@app.get("/admin/settings", response_class=HTMLResponse)
def settings_page(req: Request, msg: str = ""):
    r = need_login(req)
    if r: return r
    S = jload(P_SITE, {})
    pr = S.get("prices", {})
    price_inputs = "".join(f'<div><label>{v}</label><input type="text" name="price_{k}" value="{pr.get(k,"")}" placeholder="vd: 5.000.000đ"></div>' for k,v in PRICE_LABELS.items())
    body = f"""<div class="card"><h2>Thông tin liên hệ &amp; nút Đặt hẹn</h2>
<form method="post" action="/admin/settings">
<div class="grid2">
<div><label>Hotline</label><input type="text" name="hotline" value="{S.get('hotline','')}" placeholder="0934 37 31 37"></div>
<div><label>Email</label><input type="text" name="email" value="{S.get('email','')}" placeholder="swanclinic.khth@gmail.com"></div>
</div>
<label>Link Messenger (nút "Đặt hẹn")</label>
<input type="text" name="messenger" value="{S.get('messenger','')}" placeholder="https://m.me/ten-trang-facebook">
<h3>Bảng giá (Chi phí từ)</h3><div class="grid2">{price_inputs}</div>
<p class="note" style="margin-top:.6rem">Bỏ trống ô nào thì website giữ giá trị mặc định của ô đó.</p>
<div style="margin-top:1rem"><button class="btn">💾 Lưu cài đặt</button></div></form></div>
<div class="card"><h2>Đổi mật khẩu của tôi</h2>
<form method="post" action="/admin/settings/password">
<div class="grid2"><div><label>Mật khẩu mới</label><input type="password" name="pw1" required minlength="8"></div>
<div><label>Nhập lại</label><input type="password" name="pw2" required minlength="8"></div></div>
<div style="margin-top:.8rem"><button class="btn">Đổi mật khẩu</button></div></form></div>"""
    return page(req, "settings", body, msg=msg)

@app.post("/admin/settings")
async def settings_save(req: Request):
    r = need_login(req)
    if r: return r
    form = await req.form()
    S = jload(P_SITE, {})
    for k in ("hotline", "email", "messenger"):
        S[k] = str(form.get(k, "")).strip()
    S["prices"] = {k: str(form.get(f"price_{k}", "")).strip() for k in PRICE_LABELS}
    jsave(P_SITE, S)
    return RedirectResponse("/admin/settings?msg=Đã lưu cài đặt.", 302)

@app.post("/admin/settings/password")
def change_pw(req: Request, pw1: str = Form(...), pw2: str = Form(...)):
    r = need_login(req)
    if r: return r
    if pw1 != pw2 or len(pw1) < 8:
        return RedirectResponse("/admin/settings?msg=Mật khẩu không khớp hoặc quá ngắn.", 302)
    U = users(); u = me(req)
    salt, h = hashpw(pw1); U[u] = {**U[u], "salt": salt, "hash": h}
    jsave(P_USERS, U)
    return RedirectResponse("/admin/settings?msg=Đã đổi mật khẩu.", 302)

# ==== NỘI DUNG (chữ mọi mục, theo ngôn ngữ) ====
@app.get("/admin/content", response_class=HTMLResponse)
def content_page(req: Request, lang: str = "vi", msg: str = ""):
    r = need_login(req)
    if r: return r
    if lang not in dict(LANGS): lang = "vi"
    O = jload(P_TEXTS, {})
    langopts = "".join(f'<option value="{c}" {"selected" if c==lang else ""}>{n}</option>' for c,n in LANGS)
    rows = ""
    for key, label, big in EDITABLE:
        if label is None:
            rows += f'<tr><td colspan="2" style="background:#EAF6F7;font-weight:700;color:var(--deep)">{key}</td></tr>'
            continue
        cur = O.get(key, {}).get(lang, "")
        field = (f'<textarea name="t_{key}" rows="3" data-key="{key}">{cur}</textarea>' if big
                 else f'<input type="text" name="t_{key}" value="{cur.replace(chr(34),"&quot;")}" data-key="{key}">')
        rows += f'<tr><td style="width:34%"><b>{label}</b><div class="note df" data-def="{key}"></div></td><td>{field}</td></tr>'
    body = f"""<div class="card"><h2>Sửa nội dung website</h2>
<p class="note">Bỏ trống = dùng nội dung mặc định (hiện màu xám bên dưới nhãn). Nhập chữ = thay thế trên website. Mỗi ngôn ngữ sửa riêng.</p>
<form method="get" action="/admin/content" style="margin:.6rem 0">
<label>Ngôn ngữ đang sửa</label><select name="lang" onchange="this.form.submit()">{langopts}</select></form>
<form method="post" action="/admin/content?lang={lang}">
<table>{rows}</table>
<div style="margin-top:1rem"><button class="btn">💾 Lưu nội dung ({dict(LANGS)[lang]})</button></div>
</form></div>
<script>
fetch('/index.html').then(function(r){{return r.text();}}).then(function(s){{
  var m=s.match(/var T=\\{{[\\s\\S]*?\\}};/); if(!m)return;
  var T=new Function('return '+m[0].slice(6,-1))();
  document.querySelectorAll('.df').forEach(function(el){{
    var k=el.dataset.def; var d=(T[k]&&T[k]['{lang}'])||'';
    el.textContent='Mặc định: '+d.replace(/<[^>]+>/g,' ');
    var inp=document.querySelector('[data-key="'+CSS.escape(k)+'"]');
    if(inp&&!inp.value)inp.placeholder=d.replace(/<br>/g,' ');
  }});
}}).catch(function(){{}});
</script>"""
    return page(req, "content", body, msg=msg)

@app.post("/admin/content")
async def content_save(req: Request, lang: str = "vi"):
    r = need_login(req)
    if r: return r
    if lang not in dict(LANGS): lang = "vi"
    form = await req.form()
    O = jload(P_TEXTS, {})
    for key, label, _ in EDITABLE:
        if label is None: continue
        v = str(form.get(f"t_{key}", "")).strip()
        if v:
            O.setdefault(key, {})[lang] = v
        elif key in O and lang in O[key]:
            del O[key][lang]
            if not O[key]: del O[key]
    jsave(P_TEXTS, O)
    return RedirectResponse(f"/admin/content?lang={lang}&msg=Đã lưu nội dung.", 302)

# ==== HÌNH ẢNH (mọi vị trí trên web) ====
@app.get("/admin/images", response_class=HTMLResponse)
def images_page(req: Request, msg: str = ""):
    r = need_login(req)
    if r: return r
    S = jload(P_SITE, {})
    imgs = S.get("images", {})
    rows = ""
    for slot, label, default in IMAGE_SLOTS:
        cur = imgs.get(slot, "")
        src = "/" + (cur or default)
        state = '<span class="badge">Đã thay</span> <a class="btn sm gray" href="/admin/images/reset/' + slot + '">Về mặc định</a>' if cur else '<span class="note">Mặc định</span>'
        rows += f"""<tr><td style="width:30%"><b>{label}</b><br>{state}</td>
<td><img class="thumb" style="height:70px" src="{src}"></td>
<td><form method="post" action="/admin/images/{slot}" enctype="multipart/form-data">
<input type="file" name="file" accept="image/*" required>
<button class="btn sm" style="margin-top:.4rem">⬆ Thay ảnh</button></form></td></tr>"""
    body = f"""<div class="card"><h2>Hình ảnh trên website</h2>
<p class="note">Ảnh thay sẽ tự nén về ≤1600px. "Về mặc định" = quay lại ảnh gốc trong bộ code.</p>
<table>{rows}</table></div>"""
    return page(req, "images", body, msg=msg)

@app.post("/admin/images/{slot}")
async def images_upload(req: Request, slot: str):
    r = need_login(req)
    if r: return r
    if slot not in {s for s,_,_ in IMAGE_SLOTS}: return RedirectResponse("/admin/images", 302)
    form = await req.form()
    f = form.get("file")
    if f and getattr(f, "filename", ""):
        S = jload(P_SITE, {})
        S.setdefault("images", {})[slot] = save_upload(f)
        jsave(P_SITE, S)
    return RedirectResponse("/admin/images?msg=Đã thay ảnh.", 302)

@app.get("/admin/images/reset/{slot}")
def images_reset(req: Request, slot: str):
    r = need_login(req)
    if r: return r
    S = jload(P_SITE, {})
    S.get("images", {}).pop(slot, None)
    jsave(P_SITE, S)
    return RedirectResponse("/admin/images?msg=Đã trả về mặc định.", 302)

# ==== XEM TRƯỚC BÀI VIẾT (không lưu) ====
@app.post("/admin/news/preview", response_class=HTMLResponse)
async def news_preview(req: Request):
    r = need_login(req)
    if r: return r
    form = await req.form()
    import base64
    title = str(form.get("title","(Chưa có tiêu đề)")).strip() or "(Chưa có tiêu đề)"
    cat = CATS.get(str(form.get("cat","1")), "")
    d = str(form.get("date","")) or date.today().isoformat()
    bodytxt = str(form.get("body",""))
    cover_src = ""
    c = form.get("cover")
    if c and getattr(c, "filename", ""):
        raw = c.file.read()
        if raw:
            ext = (os.path.splitext(c.filename)[1] or ".jpg").lower().strip(".")
            cover_src = f"data:image/{'png' if ext=='png' else 'jpeg'};base64," + base64.b64encode(raw).decode()
    if not cover_src:
        ce = str(form.get("cover_existing",""))
        if ce: cover_src = "/" + ce
    imgs_existing = [u for u in str(form.get("images_existing","")).split("|") if u]
    def esc(s):
        return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
    paras = []
    for t in re.split(r"\n\s*\n", bodytxt):
        t = t.strip()
        if not t: continue
        m = re.match(r"^!\[\]\((.+)\)$", t)
        if m: paras.append(f'<img src="{esc(m.group(1))}" alt="">')
        else: paras.append("<p>" + esc(t).replace("\n","<br>") + "</p>")
    body_html = "".join(paras) + "".join(f'<img src="/{esc(u)}" alt="">' for u in imgs_existing)
    cover_html = f'<div class="cover"><img src="{cover_src}"></div>' if cover_src else ""
    return HTMLResponse(f"""<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Xem trước — {esc(title)}</title>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700&family=Cormorant+Garamond:wght@600&display=swap" rel="stylesheet">
<style>body{{font-family:'Be Vietnam Pro',sans-serif;background:#FBFAF6;color:#0C3138;line-height:1.7;margin:0}}
.bar{{background:#024A56;color:#fff;padding:.7rem 1rem;font-size:.85rem;position:sticky;top:0}}
.bar b{{color:#7fe3ec}}
.article{{max-width:760px;margin:2rem auto;padding:0 1rem 3rem}}
.cat{{font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#017E8C}}
h1{{font-family:'Cormorant Garamond',serif;font-size:2.4rem;line-height:1.15;margin:.4rem 0}}
.meta{{color:#48626B;font-size:.85rem;margin-bottom:1.4rem}}
.cover{{border-radius:14px;overflow:hidden;margin-bottom:1.6rem}}
.cover img,img{{max-width:100%;display:block;border-radius:12px}}
p{{margin-bottom:1.1rem;color:#233c43}}img{{margin:1.2rem 0}}</style></head><body>
<div class="bar">👁 <b>BẢN XEM TRƯỚC</b> — bài chưa được lưu. Đóng tab này rồi bấm "💾 Lưu bài viết" nếu ưng ý.</div>
<div class="article"><span class="cat">{esc(cat)}</span><h1>{esc(title)}</h1>
<div class="meta">{esc(d)}</div>{cover_html}{body_html or '<p class="meta">(Chưa có nội dung)</p>'}</div></body></html>""")

# ==== TÀI KHOẢN (admin) ====
@app.get("/admin/users", response_class=HTMLResponse)
def users_page(req: Request, msg: str = ""):
    r = need_login(req)
    if r: return r
    if not is_admin(req): return RedirectResponse("/admin/news", 302)
    U = users()
    rows = ""
    for n, d in U.items():
        if n == me(req):
            act = ""
        else:
            act = ('<a class="btn sm red" href="/admin/users/delete/' + n +
                   '" onclick="return confirm(&quot;Xoá tài khoản ' + n + '?&quot;)">Xoá</a>')
        rows += f"<tr><td><b>{n}</b></td><td>{d.get('role','staff')}</td><td>{act}</td></tr>"
    body = f"""<div class="card"><h2>Tài khoản nhân viên</h2>
<table><tr><th>Tên đăng nhập</th><th>Vai trò</th><th></th></tr>{rows}</table></div>
<div class="card"><h3>Thêm tài khoản</h3>
<form method="post" action="/admin/users/add"><div class="grid2">
<div><label>Tên đăng nhập</label><input type="text" name="username" required pattern="[a-zA-Z0-9_.-]+"></div>
<div><label>Mật khẩu (≥8 ký tự)</label><input type="password" name="password" required minlength="8"></div></div>
<label>Vai trò</label><select name="role"><option value="staff">Nhân viên</option><option value="admin">Quản trị</option></select>
<div style="margin-top:.8rem"><button class="btn">+ Tạo tài khoản</button></div></form></div>"""
    return page(req, "users", body, msg=msg)

@app.post("/admin/users/add")
def users_add(req: Request, username: str = Form(...), password: str = Form(...), role: str = Form("staff")):
    r = need_login(req)
    if r: return r
    if not is_admin(req): return RedirectResponse("/admin/news", 302)
    U = users(); username = username.strip()
    if username and username not in U and len(password) >= 8:
        salt, h = hashpw(password)
        U[username] = {"salt": salt, "hash": h, "role": "admin" if role == "admin" else "staff"}
        jsave(P_USERS, U)
        return RedirectResponse("/admin/users?msg=Đã tạo tài khoản.", 302)
    return RedirectResponse("/admin/users?msg=Không tạo được (trùng tên hoặc mật khẩu ngắn).", 302)

@app.get("/admin/users/delete/{name}")
def users_del(req: Request, name: str):
    r = need_login(req)
    if r: return r
    if not is_admin(req) or name == me(req): return RedirectResponse("/admin/users", 302)
    U = users(); U.pop(name, None); jsave(P_USERS, U)
    return RedirectResponse("/admin/users?msg=Đã xoá.", 302)

@app.get("/admin/health", response_class=PlainTextResponse)
def health():
    return "ok"

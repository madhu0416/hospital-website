from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os, json

# ---------------- PATHS ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
APPOINTMENTS_FILE = os.path.join(DATA_DIR, "appointments.json")

# ---------------- HELPERS ----------------
def read_file(path, mode="rb"):
    with open(path, mode) as f:
        return f.read()

def ensure_data_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(APPOINTMENTS_FILE):
        with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

def load_appointments():
    ensure_data_file()
    with open(APPOINTMENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_appointments(appts):
    with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(appts, f, indent=2)

def render_template(filename, context=None):
    context = context or {}
    html = read_file(os.path.join(TEMPLATES_DIR, filename), "r")
    for k, v in context.items():
        html = html.replace("{{" + k + "}}", str(v))
    return html.encode("utf-8")

def html_escape(s):
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

def build_rows(appts):
    if not appts:
        return "<tr><td colspan='7'>No appointments yet</td></tr>"

    rows = []
    for a in appts:
        rows.append(
            "<tr>"
            f"<td>{html_escape(a['patient_name'])}</td>"
            f"<td>{html_escape(a['age'])}</td>"
            f"<td>{html_escape(a['gender'])}</td>"
            f"<td>{html_escape(a['phone'])}</td>"
            f"<td>{html_escape(a['doctor_type'])}</td>"
            f"<td>{html_escape(a['date'])}</td>"
            f"<td>{html_escape(a['slot'])}</td>"
            "</tr>"
        )
    return "\n".join(rows)

# ---------------- SERVER ----------------
class Handler(BaseHTTPRequestHandler):

    # ---------- GET ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Serve static files
        if path.startswith("/static/"):
            file_path = os.path.join(STATIC_DIR, path.replace("/static/", ""))
            if os.path.isfile(file_path):
                self.send_response(200)
                if file_path.endswith(".css"):
                    self.send_header("Content-Type", "text/css")
                elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                    self.send_header("Content-Type", "image/jpeg")
                elif file_path.endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(read_file(file_path))
                return

        # Pages
        if path == "/" or path == "/home":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(read_file(os.path.join(TEMPLATES_DIR, "index.html")))
            return

        if path == "/book":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(read_file(os.path.join(TEMPLATES_DIR, "book.html")))
            return

        if path == "/admin":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(read_file(os.path.join(TEMPLATES_DIR, "admin_login.html")))
            return

        self.send_error(404, "Page not found")

    # ---------- POST ----------
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        form = parse_qs(body)

        def get(name):
            return form.get(name, [""])[0].strip()

        # ----- ADMIN LOGIN -----
        if path == "/admin-login":
            username = get("username")
            password = get("password")

            if username == "admin" and password == "admin123":
                appts = load_appointments()
                html = render_template("admin_dashboard.html", {
                    "total": len(appts),
                    "rows": build_rows(appts)
                })
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html)
            else:
                self.send_response(401)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>Invalid login</h2><a href='/admin'>Back</a>")
            return

        # ----- BOOK APPOINTMENT -----
        if path == "/submit":
            patient_name = get("patient_name")
            age = get("age")
            gender = get("gender")
            phone = get("phone")
            doctor_type = get("doctor_type")
            date = get("date")
            slot = get("slot")

            if not all([patient_name, age, gender, phone, doctor_type, date, slot]):
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>All fields required</h2><a href='/book'>Back</a>")
                return

            appts = load_appointments()
            # prevent duplicate slot
            for a in appts:
                if a["doctor_type"] == doctor_type and a["date"] == date and a["slot"] == slot:
                    self.send_response(409)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h2>Slot already booked</h2><a href='/book'>Choose another</a>")
                    return
            new_appt = {
                "patient_name": patient_name,
                "age": age,
                "gender": gender,
                "phone": phone,
                "doctor_type": doctor_type,
                "date": date,
                "slot": slot
            }
            appts.append(new_appt)
            save_appointments(appts)
            html = render_template("success.html", new_appt)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html)
            return

        self.send_error(404, "POST route not found")
if __name__ == "__main__":
    ensure_data_file()
    print("Server running at http://127.0.0.1:8000")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()

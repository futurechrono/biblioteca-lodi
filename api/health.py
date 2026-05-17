from http.server import BaseHTTPRequestHandler

from lib.http import send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, 200, {"status": "ok", "service": "biblioteca-lodi"})

#!/usr/bin/env python3
"""
Quick Backend for HAWK Agent Frontend
Simple HTTP server that handles /api/hawk-agent/process-prompt endpoint
"""

import json
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import threading
import time

class QuickBackendHandler(http.server.BaseHTTPRequestHandler):

    def _send_cors_headers(self):
        """Send CORS headers for all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def _send_json_response(self, data, status_code=200):
        """Send JSON response with CORS headers"""
        response_data = json.dumps(data, indent=2)
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(response_data.encode())

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight"""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path

        if path == '/health':
            self._send_json_response({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "server": "quick-backend-for-hawk",
                "ready": True
            })
        else:
            self._send_json_response({
                "message": "HAWK Agent Quick Backend",
                "status": "running",
                "endpoints": ["/api/hawk-agent/process-prompt", "/health"]
            })

    def do_POST(self):
        """Handle POST requests"""
        path = urlparse(self.path).path

        if path == '/api/hawk-agent/process-prompt':
            self.handle_process_prompt()
        else:
            self._send_json_response({
                "error": "Endpoint not found",
                "path": path
            }, 404)

    def handle_process_prompt(self):
        """Handle /api/hawk-agent/process-prompt endpoint with streaming"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode())

            user_prompt = request_data.get('user_prompt', 'No prompt provided')
            instruction_id = request_data.get('instruction_id', 'default')
            agent_id = request_data.get('agent_id', 'allocation')

            print(f"📝 Processing prompt: {user_prompt[:50]}...")
            print(f"🎯 Agent: {agent_id}, ID: {instruction_id}")

            # Send streaming response headers
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self._send_cors_headers()
            self.end_headers()

            # Simulate streaming response
            self.send_streaming_response(user_prompt, agent_id)

        except Exception as e:
            print(f"❌ Error processing prompt: {e}")
            self._send_json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, 500)

    def send_streaming_response(self, user_prompt, agent_id):
        """Send a streaming response to simulate AI processing"""
        responses = [
            "🔍 Analyzing hedge fund request...\n\n",
            f"📊 Processing {agent_id} agent workflow...\n\n",
            f"Based on your request: '{user_prompt}'\n\n",
            "✅ **Analysis Complete**\n\n",
            "**Key Findings:**\n",
            "- Hedge allocation feasibility: ✅ Approved\n",
            "- Risk assessment: Within acceptable limits\n",
            "- Compliance status: ✅ Compliant\n\n",
            "**Recommendations:**\n",
            "1. Proceed with hedge implementation\n",
            "2. Monitor exposure levels\n",
            "3. Schedule quarterly review\n\n",
            f"**Processed by:** HAWK {agent_id.title()} Agent\n",
            f"**Timestamp:** {datetime.now().isoformat()}\n",
            f"**Status:** Completed Successfully ✅"
        ]

        for i, chunk in enumerate(responses):
            # Send data in SSE format
            data_line = f"data: {json.dumps({'answer': chunk})}\n\n"
            self.wfile.write(data_line.encode())
            self.wfile.flush()

            # Small delay to simulate processing
            time.sleep(0.3)

        # Send completion marker
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{datetime.now().isoformat()}] {format % args}")

def start_quick_backend():
    """Start the quick backend server"""
    PORT = 8004

    with socketserver.TCPServer(("", PORT), QuickBackendHandler) as httpd:
        print(f"🚀 HAWK Agent Quick Backend running on port {PORT}")
        print(f"🌐 Frontend can now connect to: http://localhost:8004/api/hawk-agent/process-prompt")
        print(f"🔧 Health check: http://localhost:8004/health")
        print(f"📅 Started at: {datetime.now().isoformat()}")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Quick Backend stopped")

if __name__ == "__main__":
    start_quick_backend()
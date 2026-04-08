"""
POST /api/generate-script

Body: { "topic": "Honesty", "character_description": "<text>" }

Generates a 6-scene story script via GPT-4o using the same template Khayaal
uses in its production pipeline (each scene is either narration OR character
dialogue, never both).

Returns: { "script": "<full text>", "scenes": [ ... ] }
"""
from http.server import BaseHTTPRequestHandler
import json
import os


DEFAULT_CHARACTER = (
    "A cute round teal/blue animated blob creature named Bubbles with big "
    "expressive dark eyes, a wide happy smile, tiny stick arms and tiny stick "
    "legs. The creature is round and soft like a ball. Pixar-style 3D animation."
)


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return self._send_json(503, {
                "error": "OPENAI_API_KEY not configured on the server",
                "demo": True,
            })

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body) if body else {}
            topic = data.get("topic", "Honesty").strip()
            character_desc = data.get("character_description") or DEFAULT_CHARACTER
        except Exception as e:
            return self._send_json(400, {"error": f"Bad request: {e}"})

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            sys_prompt = f"""You are a children's content writer for animated stories.

The main character in EVERY scene is: {character_desc}

CRITICAL RULES FOR AUDIO:
- Each scene has ONLY narration OR ONLY character dialogue. NEVER BOTH.
- Mark each scene clearly: "NARRATION:" or "CHARACTER SPEAKS:".
- The character should speak in scenes 3 and 6.
- All other scenes use narration only.
- Each scene is about 7-8 seconds long.

Format strictly as:
SCENE 1 (0-8s):
VISUAL: ...
AUDIO TYPE: NARRATION or CHARACTER SPEAKS
AUDIO: "..."
"""

            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Write a 40-second animated story for children aged 4-8 "
                            f"about {topic}. The story should be warm, gentle, and "
                            f"end with a clear positive message."
                        ),
                    },
                ],
                temperature=0.8,
            )
            script = resp.choices[0].message.content.strip()
            return self._send_json(200, {"script": script, "topic": topic})
        except Exception as e:
            return self._send_json(500, {"error": str(e)})

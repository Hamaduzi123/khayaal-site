"""
POST /api/generate-character

Body: { "image": "data:image/jpeg;base64,..." }

Steps:
1. GPT-4 Vision analyses the uploaded drawing and writes a Pixar-style character description.
2. DALL-E 3 generates a polished 1024x1024 character based on that description.

Returns: { "character_url": "<url>", "description": "<text>" }

Requires env var OPENAI_API_KEY (set in Vercel project settings).
Falls back gracefully with HTTP 503 if the key is missing.
"""
from http.server import BaseHTTPRequestHandler
import json
import os


CHARACTER_STYLE_PROMPT = (
    "Take the child's drawing description below and re-imagine it as a polished, "
    "Pixar-style 3D animated character. Keep the original creative spirit and key "
    "features intact, but render it as a friendly, expressive character with big "
    "eyes, soft round shapes, vibrant colors and gentle lighting. The character "
    "should be standing in a neutral pose against a soft pastel background, "
    "centered in frame, full body visible, suitable for a children's story video. "
    "Style: Pixar 3D animation, high quality, HD."
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
            image_data_url = data.get("image")
            if not image_data_url:
                return self._send_json(400, {"error": "Missing 'image' field"})
        except Exception as e:
            return self._send_json(400, {"error": f"Bad request: {e}"})

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            # Step 1: Vision analysis
            vision = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Look at this child's drawing. Describe the character "
                                    "in 2-3 sentences: body shape, colors, eyes, mouth, "
                                    "limbs, and overall personality. Be specific and vivid."
                                ),
                            },
                            {"type": "image_url", "image_url": {"url": image_data_url}},
                        ],
                    }
                ],
                max_tokens=400,
            )
            description = vision.choices[0].message.content.strip()

            # Step 2: DALL-E 3 generation
            full_prompt = (
                f"{CHARACTER_STYLE_PROMPT}\n\nOriginal drawing description:\n{description}"
            )
            image = client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                size="1024x1024",
                quality="hd",
                n=1,
            )
            character_url = image.data[0].url

            return self._send_json(200, {
                "character_url": character_url,
                "description": description,
            })
        except Exception as e:
            return self._send_json(500, {"error": str(e)})

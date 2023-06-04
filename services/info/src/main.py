from dataclasses import dataclass
from typing import Dict, Optional, List
import json
import re
import io

from flask import Flask, send_file, request


@dataclass
class PlayerProfile:
    username: str
    image: Optional[bytes] = None
    image_type: str = ""
    gender: str = ""
    email: str = ""

    def get_info(self):
        return {
            "username": self.username,
            "gender": self.gender,
            "email": self.email,
            "has_image": bool(self.image),
        }


app = Flask(__name__)

profiles: Dict[str, PlayerProfile] = dict()


@app.get("/profile/info")
def get_info():
    username = request.args.get("username")
    if not username:
        return "Missing query parameter: username", 400
    if username not in profiles:
        return f"Unknown username: {username}", 404
    return json.dumps(profiles[username].get_info())


@app.put("/profile/info")
def put_info():
    username = request.args.get("username")
    if not username:
        return "Missing query parameter: username", 400
    if username not in profiles:
        return f"Unknown username: {username}", 404
    return json.dumps(profiles[username].get_info())


@app.post("/profile/info")
def post_info():
    username = request.args.get("username")
    if not username:
        return "Missing query parameter: username", 400
    data = request.get_json(force=True)
    if username not in profiles:
        profiles[username] = PlayerProfile(username)
    if "gender" in data:
        profiles[username].gender = data["gender"]
    if "email" in data:
        profiles[username].gender = data["email"]


@app.delete("/profile/info")
def delete_info():
    username = request.args.get("username")
    if not username:
        return "Missing query parameter: username", 400
    data = request.get_json(force=True)
    if username in profiles:
        return f"Username is already taken: {username}"
    profiles[username] = PlayerProfile(username)
    if "gender" in data:
        profiles[username].gender = data["gender"]
    if "email" in data:
        profiles[username].gender = data["email"]


@app.get("/profile/query")
def get_query():
    username = request.args.get("username")
    if not username:
        return "Missing query parameter: username", 400
    result = []
    for k, v in profiles.items():
        if re.match(username, k):
            result.append(v.get_info())
    return json.dumps(result)


@app.get("/profile/image")
def get_image():
    username = request.args.get("username")
    if not username:
        return "Missing query parameter: username", 400
    if username not in profiles:
        return f"Unknown username: {username}", 404
    image = profiles[username]
    if not image:
        return f"User does not have an image", 404
    return send_file(
        io.BytesIO(image),
        mimetype=profiles[username].image_type,
        as_attachment=True,
        download_name=f"{username}.jpg",
    )


@app.post("/profile/image")
def post_image():
    username = request.args.get("username")
    if not username:
        return "Missing query parameter: username", 400
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400
    if username not in profiles:
        return f"Unknown username: {username}", 404
    profile: PlayerProfile = profiles[username]
    if file and file.mimetype.startswith("image/"):
        profile.image_type = file.mimetype
        profile.image = file.stream.read()
    else:
        return f"Invalid mime-type: {file.mimetype}", 400


@app.delete("/profile/image")
def delete_image():
    username = request.args.get("username")
    if not username:
        return "Missing query parameter: username", 400
    if username not in profiles:
        return f"Unknown username: {username}", 404
    profiles[username].image = None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=False)

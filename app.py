from flask import Flask, request, render_template_string
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
import time
import redis
import json

app = Flask(__name__)
# Redis client (běží v docker-compose síti)
redis_client = redis.Redis(
    host="redis", 
    port=6379,
    decode_responses=True
)

CACHE_TTL = 3600  # 1 hodina

def get_from_cache(url):
    cached = redis_client.get(url)
    if cached:
        return json.loads(cached)
    return None


def save_to_cache(url, data):
    redis_client.setex(url, CACHE_TTL, json.dumps(data))


def measure_request_time(url, method):
    try:
        start_time = time.time()
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "HEAD":
            response = requests.head(url, timeout=5)
        end_time = time.time()
        return end_time - start_time, response
    except requests.ConnectionError:
        return "Chyba připojení", None
    except requests.Timeout:
        return "Timeout při požadavku", None
    except requests.RequestException as e:
        return f"Chyba požadavku: {e}", None

def format_time(value):
    return f"{value:.2f} s" if isinstance(value, (int, float)) else value

def get_image_sizes(html_content, base_url):
    soup = BeautifulSoup(html_content, "html.parser")
    img_tags = soup.find_all("img", src=re.compile(r'\.(jpeg|jpg|png|gif)(\?.*)?$', re.IGNORECASE))
    image_sizes = []
    for img in img_tags:
        img_url = img.get("src", "")
        if img_url:
            full_img_url = urljoin(base_url, img_url)
            try:
                response = requests.get(full_img_url, stream=True, timeout=5)
                size = len(response.content)
                image_sizes.append((full_img_url, size))
            except Exception as e:
                image_sizes.append((full_img_url, f"Chyba: {e}"))
    return image_sizes

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Web Diagnostika</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    input[type=text] { width: 400px; padding: 5px; }
    textarea { width: 100%; height: 300px; }
    table { border-collapse: collapse; width: 100%; margin-top: 15px; }
    th, td { border: 1px solid #ddd; padding: 8px; font-size: 14px; }
    th { background-color: #f2f2f2; }
  </style>
</head>
<body>
  <h1>Diagnostika webové stránky</h1>
  <form method="post">
    <label>Zadejte URL:</label><br>
    <input type="text" name="url" value="{{ url }}" required>
    <button type="submit">Diagnostikovat</button>
  </form>
  {% if result %}
    <h2>Výsledky</h2>
    <pre>{{ result }}</pre>
    {% if images %}
      <h2>Obrázky</h2>
      <table>
        <tr><th>URL</th><th>Velikost (bajtů)</th></tr>
        {% for img, size in images %}
          <tr><td>{{ img }}</td><td>{{ size }}</td></tr>
        {% endfor %}
      </table>
    {% endif %}
  {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def diagnose():
    result = None
    images = []
    url = ""
    if request.method == "POST":
        try:
            redis_client.ping()
            redis_status = "Redis připojen"
        except Exception as e:
            redis_status = f"Redis chyba: {e}"
        url = request.form.get("url")
        try:
            cached_data = get_from_cache(url)

            if cached_data:
                result = cached_data["result"]
                images = cached_data["images"]
                result = "ZDROJ: CACHE\n" + result
            else:
                load_time_get, get_response = measure_request_time(url, "GET")
                load_time_head, head_response = measure_request_time(url, "HEAD")
                head_status = head_response.status_code if head_response else "N/A"

                if not get_response:
                    result = "Chyba připojení nebo timeout."
                else:
                    headers = get_response.headers
                    cache_control = headers.get("Cache-Control", "N/A")
                    images = get_image_sizes(get_response.text, url)

                    result = (
                        f"Diagnostika pro: {url}\n"
                        f"Redis připojen\n"
                        f"Rychlost GET: {format_time(load_time_get)}\n"
                        f"Rychlost HEAD: {format_time(load_time_head)}\n"
                        f"Cache-Control: {cache_control}\n"
                        f"GET status: {get_response.status_code}\n"
                        f"HEAD status: {head_status}\n"
                        f"Počet obrázků: {len(images)}\n\n"
                        "HTTP hlavičky:\n"
                    )

                    for k, v in headers.items():
                        result += f"{k}: {v}\n"

                    result = "ZDROJ: SCRAPER\n" + result
                    
                    save_to_cache(url, {
                        "result": result,
                        "images": images
                    })
        except Exception as e:
            result = f"Chyba při analýze: {e}"
    return render_template_string(HTML_TEMPLATE, result=result, images=images, url=url)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

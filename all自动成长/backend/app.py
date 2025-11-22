import os
import json
import requests
from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
import urllib.parse
import time
import random

# ========== 可选翻译库 ==========
try:
    from deep_translator import GoogleTranslator
    TRANSLATE_ENABLED = True
except ImportError:
    print("⚠️ deep_translator 未安装，联网抓取内容将不会翻译")
    TRANSLATE_ENABLED = False

# ========== 基本配置 ==========
app = Flask(__name__, template_folder="templates")

PASSWORD = "Hjh20131121"
KB_FILE = "knowledge_base.json"
MAX_PAGES = 5
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0 Safari/537.36"
)

# ========== 知识库存取 ==========
def load_kb():
    if os.path.exists(KB_FILE):
        with open(KB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_kb(kb):
    with open(KB_FILE, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

# ========== 搜索与抓取 ==========
def extract_real_url(ddg_url):
    if "uddg=" in ddg_url:
        parsed = urllib.parse.urlparse(ddg_url)
        query = urllib.parse.parse_qs(parsed.query)
        real_url = query.get("uddg", [""])[0]
        return urllib.parse.unquote(real_url)
    return ddg_url

def search_urls(query, max_results=MAX_PAGES):
    search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    try:
        resp = requests.get(search_url, headers={"User-Agent": USER_AGENT}, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        seen = set()
        for a in soup.find_all("a", class_="result__a", href=True):
            url = extract_real_url(a["href"])
            if url and url not in seen:
                seen.add(url)
                links.append(url)
                if len(links) >= max_results:
                    break
        return links
    except Exception as e:
        print(f"搜索失败: {e}")
        return []

def scrape_page(url):
    """抓取网页正文并自动翻译英文"""
    try:
        print(f"📖 抓取内容：{url}")
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        content = "\n".join(paragraphs)
        if not content:
            content = soup.get_text(separator="\n", strip=True)[:2000]

        # 自动翻译英文到中文
        if TRANSLATE_ENABLED and content:
            try:
                translated = GoogleTranslator(source='auto', target='zh-CN').translate(content)
                return translated
            except Exception as e:
                print(f"⚠️ 翻译失败: {e}")
                return content

        return content
    except Exception as e:
        print(f"抓取失败 {url}: {e}")
        return ""

def search_online(query):
    print(f"🔍 正在联网搜索：{query}")
    urls = search_urls(query, max_results=MAX_PAGES)
    results = []
    for url in urls:
        text = scrape_page(url)
        if text:
            results.append(text)
        time.sleep(random.uniform(0.5,1.2))

    if not results:
        return "未能从网上获取到有效内容。"

    return "\n\n".join(results[:3])  # 前3条内容

# ========== 页面 ==========
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

# ========== 聊天接口 ==========
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "❌ 请输入问题。"})

    kb = load_kb()
    for item in kb:
        if user_input in item.get("question", ""):
            return jsonify({"reply": f"[知识库回答]\n{item.get('answer')}"})

    online_answer = search_online(user_input)

    kb.append({
        "question": user_input,
        "answer": online_answer,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    save_kb(kb)

    return jsonify({"reply": f"[联网搜索结果]\n{online_answer}"})

# ========== 后台教学接口 ==========
@app.route("/api/admin", methods=["POST"])
def admin_api():
    data = request.json
    password = data.get("password", "")
    if password != PASSWORD:
        return jsonify({"reply": "❌ 密码错误"})

    action = data.get("action", "").strip()
    kb = load_kb()

    if action == "fetch_page":
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"reply": "❌ URL 不能为空"})
        text = scrape_page(url)
        if not text:
            return jsonify({"reply": "❌ 抓取网页失败"})
        kb.append({
            "question": url,
            "answer": text,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        save_kb(kb)
        return jsonify({"reply": f"✅ 已抓取网页并加入知识库\n{text[:500]}..."})

    elif action == "teach":
        question = data.get("question", "").strip()
        answer = data.get("answer", "").strip()
        if not question or not answer:
            return jsonify({"reply": "❌ 问题或答案不能为空"})
        kb.append({
            "question": question,
            "answer": answer,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        save_kb(kb)
        return jsonify({"reply": f"✅ 已学习问题：{question}"})
    else:
        return jsonify({"reply": "❌ 未知 action 类型"})

# ========== 启动 ==========
if __name__ == "__main__":
    app.run(debug=True, port=5002, host="0.0.0.0")
import os
from app import app  # 导入你的 Flask 实例

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))  # Render 会提供 PORT
    app.run(host="0.0.0.0", port=port)

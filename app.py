import os
from flask import Flask, redirect, url_for
from production import productionBlueprint

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key_for_development")
app.register_blueprint(productionBlueprint, url_prefix="/production")

@app.route("/")
def root():
    return redirect(url_for("production.index"))

if __name__ == "__main__":
    app.run(debug=True)

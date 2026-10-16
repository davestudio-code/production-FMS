import os
from flask import Flask, redirect, url_for
from production import productionBlueprint

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key_for_development")
app.register_blueprint(productionBlueprint, url_prefix="/production")

@app.route("/")
def root():
    return redirect(url_for("production.index"))

@app.teardown_appcontext
def closeRequestContextDb(error=None):
    from flask import g
    conn = getattr(g, "dbConnection", None)
    if conn is not None and conn.closed == 0:
        if error:
            conn.rollback()
        else:
            conn.commit()
        conn.close()
        g.dbConnection = None

if __name__ == "__main__":
    app.run(debug=True)

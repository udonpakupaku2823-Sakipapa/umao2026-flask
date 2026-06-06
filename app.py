from flask import Flask, request, render_template, redirect, session
import os
import sys

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore as admin_firestore
import datetime

#cred = credentials.Certificate("/etc/secrets/serviceAccount.json")
# Render 環境なら /etc/secrets にある
if os.path.exists("/etc/secrets/serviceAccount.json"):
    cred_path = "/etc/secrets/serviceAccount.json"
else:
    # ローカル環境
    cred_path = "serviceAccount.json"

cred = credentials.Certificate(cred_path)

firebase_admin.initialize_app(cred)
db = admin_firestore.client()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = "umao-secret-key"

# 画像ファイル対応
image_files = {
    "2026年うま王": "2026年うま王.png",
    "2026年うま王収支表単勝": "2026年うま王収支表単勝.png",
    "2026年うま王収支表馬連": "2026年うま王収支表馬連.png",
    "2026年うま王収支表三連複": "2026年うま王収支表三連複.png",

    "0607安田記念": "0607安田記念.png",   

    "0531目黒記念": "0531目黒記念.png",
    "0531日本ダービー": "0531日本ダービー.png",
    "0530葵Ｓ": "0530葵Ｓ.png",

    "0524オークス": "0524オークス.png",
    "0523平安Ｓ": "0523平安Ｓ.png",

    "0517ヴィクトリアマイル": "0517ヴィクトリアマイル.png",
    "0516新潟大賞典": "0516新潟大賞典.png",

    "0510ＮＨＫマイルＣ": "0510ＮＨＫマイルＣ.png",
    "0509エプソムＣ": "0509エプソムＣ.png",
    "0509京都新聞杯": "0509京都新聞杯.png",

    "0503天皇賞（春）": "0503天皇賞（春）.png",
    "0502京王杯スプリングＣ": "0502京王杯スプリングＣ.png",
    "0502ユニコーンＳ": "0502ユニコーンＳ.png",

    "0426フローラＳ": "0426フローラＳ.png",
    "0426マイラーズＣ": "0426マイラーズＣ.png",
    "0425青葉賞": "0425青葉賞.png",

    "0419皐月賞": "0419皐月賞.png",
    "0419福島牝馬Ｓ": "0419福島牝馬Ｓ.png",
    "0418アンタレスＳ": "0418アンタレスＳ.png",

    "0412桜花賞": "0412桜花賞.png",
    "0411ニュージーランドＴ": "0411ニュージーランドＴ.png",
    "0411阪神牝馬Ｓ": "0411阪神牝馬Ｓ.png",

    "0405大阪杯": "0405大阪杯.png",
    "0404ダービー卿ＣＴ": "0404ダービー卿ＣＴ.png",
    "0404チャーチルダウンズＣ": "0404チャーチルダウンズＣ.png",

    "0329高松宮記念": "0329高松宮記念.png",
    "0329マーチＳ": "0329マーチＳ.png",
    "0328日経賞": "0328日経賞.png",
    "0328毎日杯": "0328毎日杯.png",

    "0322阪神大賞典": "0322阪神大賞典.png",
    "0322愛知杯": "0322愛知杯.png",
    "0321フラワーカップ": "0321フラワーカップ.png",
    "0321ファルコンＳ": "0321ファルコンＳ.png",

    "0315スプリングＳ": "0315スプリングＳ.png",
    "0315金鯱賞": "0315金鯱賞.png",
    "0308弥生賞": "0308弥生賞.png",
    "0307中山牝馬Ｓ": "0307中山牝馬Ｓ.png",
    "0307フィリーズレビュー": "0307フィリーズレビュー.png",

    "0301中山記念": "0301中山記念.png",
    "0301チューリップ賞": "0301チューリップ賞.png",
    "0228オーシャンＳ": "0228オーシャンＳ.png",

    "0222フェブラリーＳ": "0222フェブラリーＳ.png",
    "0222小倉大賞典": "0222小倉大賞典.png",
    "0221ダイヤモンドＳ": "0221ダイヤモンドＳ.png",
    "0221阪急杯": "0221阪急杯.png",

    "0215共同通信杯": "0215共同通信杯.png",
    "0215京都記念": "0215京都記念.png",
    "0214クイーンカップ": "0214クイーンカップ.png",

    "0210東京新聞杯": "0210東京新聞杯.png",
    "0210きさらぎ賞": "0210きさらぎ賞.png",

    "0201シルクロードＳ": "0201シルクロードＳ.png",
    "0201根岸Ｓ": "0201根岸Ｓ.png",

    "0125アメリカジョッキーＣ": "0125アメリカジョッキーＣ.png",
    "0125プロキオンＳ": "0125プロキオンＳ.png",
    "0124小倉牝馬Ｓ": "0124小倉牝馬Ｓ.png",

    "0118京成杯": "0118京成杯.png",
    "0118日経新春杯": "0118日経新春杯.png",
    "0112シンザン記念": "0112シンザン記念.png",
    "0111フェアリーＳ": "0111フェアリーＳ.png",

    "0104中山金杯": "0104中山金杯.png",
    "0104京都金杯": "0104京都金杯.png",
}

# -------------------------
# ① トップページ（index.html）
# -------------------------
@app.route("/", methods=["GET", "POST", "HEAD"])
def index():
    print("METHOD:", request.method)
    if request.method == "HEAD":
        return "", 200

    # アクセスカウント
    if request.method == "GET":
        counter_ref = db.collection("stats").document("page_counter")
        counter_ref.set({"count": admin_firestore.Increment(1)}, merge=True)

    # アクセスログ
    db.collection("access_logs").add({
        "timestamp": datetime.datetime.now(),
        "ip": request.remote_addr
    })

    # レース選択肢
    options = list(image_files.keys())
    filename = None
    race = None

    if request.method == "POST":
        race = request.form.get("race")
        filename = image_files.get(race)

    # 現在のカウント取得
    counter_ref = db.collection("stats").document("page_counter")
    counter_doc = counter_ref.get()
    count = counter_doc.to_dict().get("count", 0)

   


    return render_template("index.html",
                           options=options,
                           filename=filename,
                           race=race,
                           count=count)

# -------------------------
# ② メイン画面装飾
# -------------------------
@app.route("/main")
def main():
    # レース一覧（index と同じものを使う）
    options = ["2026年うま王","2026年うま王収支表単勝","2026年うま王収支表馬連","2026年うま王収支表三連複",
               "0607安田記念",
               "0531目黒記念","0531日本ダービー","0530葵Ｓ",       
               "0524オークス","0523平安Ｓ",               
               "0517ヴィクトリアマイル","0516新潟大賞典",
               "0510ＮＨＫマイルＣ","0509エプソムＣ","0509京都新聞杯",
               "0503天皇賞（春）","0502京王杯スプリングＣ","0502ユニコーンＳ",
               "0426フローラＳ","0426マイラーズＣ","0425青葉賞",
               "0419皐月賞","0419福島牝馬Ｓ","0418アンタレスＳ",
               "0412桜花賞","0411ニュージーランドＴ","0411阪神牝馬Ｓ",
               "0405大阪杯","0404ダービー卿ＣＴ","0404チャーチルダウンズＣ",
               "0329高松宮記念","0329マーチＳ","0328日経賞","0328毎日杯",
               "0322阪神大賞典","0322愛知杯","0321フラワーカップ","0321ファルコンＳ",
               "0315スプリングＳ","0315金鯱賞","0308弥生賞","0307中山牝馬Ｓ","0307フィリーズレビュー",
               "0301中山記念","0301チューリップ賞","0228オーシャンＳ",
               "0222フェブラリーＳ","0222小倉大賞典","0221ダイヤモンドＳ","0221阪急杯",
               "0215共同通信杯","0215京都記念","0214クイーンカップ",
               "0210東京新聞杯","0210きさらぎ賞",
               "0201シルクロードＳ","0201根岸Ｓ",
               "0125アメリカジョッキーＣ","0125プロキオンＳ","0124小倉牝馬Ｓ",
               "0118京成杯","0118日経新春杯","0112シンザン記念","0111フェアリーＳ",
               "0104中山金杯","0104京都金杯"]
    filename = None
    race = None

    return render_template("main.html", options=options, race=race)

# -------------------------
# ② チャットページ
# -------------------------
@app.route("/chat")
def chat():
    return render_template("chat.html")

# -------------------------
# ③ 最後に app.run()
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)

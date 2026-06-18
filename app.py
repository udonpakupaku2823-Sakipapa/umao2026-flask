from google.cloud import firestore
from flask import Flask, request, render_template, redirect, session, make_response, flash
import os
import sys

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore as admin_firestore
import datetime

# --- ② Firebase 認証（Render / ローカル両対応） ---
import json
import tempfile

import os
from firebase_admin import credentials, initialize_app

# Render の環境変数に Firebase 秘密鍵 JSON を入れておく
firebase_key_json = os.environ.get("FIREBASE_KEY")

if firebase_key_json:
    # Render 本番：環境変数から一時ファイルを作る
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as f:
        f.write(firebase_key_json)
        cred_path = f.name
else:
    # ローカル：serviceAccount.json を使う
    cred_path = "serviceAccount.json"

cred = credentials.Certificate(cred_path)
initialize_app(cred)

db = admin_firestore.client()


# --- ③ PyInstaller 対応（resource_path） ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- ④ Flask アプリ本体 ---
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = "umao-secret-key"

@app.route("/race")
def race_select():
    races = []
    docs = db.collection("races").stream()
    for doc in docs:
        races.append(doc.id)
    print("★★★ race_select.html を返すよ ★★★")
    return render_template("race_select.html", options=races)


# 画像ファイル対応
image_files = {
    "2026年うま王": "2026年うま王.png",
    "2026年うま王収支表単勝": "2026年うま王収支表単勝.png",
    "2026年うま王収支表馬連": "2026年うま王収支表馬連.png",
    "2026年うま王収支表三連複": "2026年うま王収支表三連複.png",

    "0614宝塚記念": "0614宝塚記念.png",
    "0613函館スプリントＳ": "0613函館スプリントＳ.png",   
    
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
#@app.route("/")
#def index():
#    return render_template("index.html")

# -------------------------
# ① レシスター設置
# -------------------------
@app.route("/register", methods=["POST"])
def register():
    nickname = request.form.get("nickname", "").strip()

    # バリデーション
    if not nickname or len(nickname) > 3:
        return render_template("index.html",
                               error="登録名は1〜3文字で入力してください。",
                               nickname=nickname)

    doc_ref = db.collection("users").document(nickname)
    doc = doc_ref.get()

    # Firestore に存在する → 既存ユーザーとして通す
    if doc.exists:
        return redirect("/main?nickname=" + nickname)

    # Firestore に存在しない → 新規登録
    doc_ref.set({"created": firestore.SERVER_TIMESTAMP})

    return redirect("/main?nickname=" + nickname)



# -------------------------
# ② コンテスト比較表作成
# -------------------------
@app.route("/compare/<raceId>")
def compare(raceId):

    # 出走表（馬番を数値としてソート）
    horses_ref = db.collection("races").document(raceId).collection("horses").stream()
    horses = []
    for h in horses_ref:
        d = h.to_dict()
        horses.append({
            "id": h.id,
            "waku": d.get("waku"),
            "number": int(d.get("number")),   # ★ 数値化
            "name": d.get("name")
        })

    horses = sorted(horses, key=lambda x: x["number"])

    # 参加ユーザー一覧（marks の直下のドキュメント名）
    users_ref = db.collection("races").document(raceId).collection("marks").stream()
    users = [u.id for u in users_ref]

    # 印データ（フィールドをそのまま読む）
    predictions = {}
    for user in users:
        doc = db.collection("races").document(raceId).collection("marks").document(user).get()
        data = doc.to_dict() or {}   # ★ フィールドがそのまま入っている
        predictions[user] = data     # ★ 馬名 → 印 の辞書

    return render_template("compare.html",
                           raceId=raceId,
                           horses=horses,
                           users=users,
                           predictions=predictions)

# -------------------------
# ② 予想コンテストエントリ画面表示
# -------------------------
@app.route('/admin/race')
def admin_race():
    return render_template('admin/race.html')

@app.route('/marks/<raceId>')
def marks(raceId):
    # races/{raceId}/horses コレクションから馬名を取得
    #horses_ref = db.collection("races").document(raceId).collection("horses")
    #docs = horses_ref.order_by("number").get()
    #horses = [doc.to_dict().get("name") for doc in docs]
    #return render_template("marks.html", horses=horses, raceId=raceId)

    race_ref = db.collection("races").document(raceId)
    race_doc = race_ref.get()

    # ⑥ レース名を取得
    raceName = race_doc.to_dict().get("name")

    # 馬データ取得
    horses_snap = race_ref.collection("horses").order_by("number").get()
    horses = [
        {
            "name": doc.to_dict().get("name"),
            "number": doc.to_dict().get("number"),
            "waku": doc.to_dict().get("waku")
        }
        for doc in horses_snap
    ]

    # ⑥ raceName をテンプレートに渡す
    return render_template("marks.html", horses=horses, raceId=raceId, raceName=raceName)

@app.route("/select_race")
def select_race():
    races = db.collection("races").order_by("date", direction="DESCENDING").get()

    options = [
        (doc.id, f'{doc.to_dict()["name"]}（{doc.to_dict()["date"]}）')
        for doc in races
    ]

    return render_template("race_select.html", options=options)

@app.route("/marks_go", methods=["POST"])
def marks_go():
    raceId = request.form["raceId"]
    if not raceId:
        # HTML と同じ挙動：選択してないなら戻す
        flash("レースを選択してください")
        return redirect("/contest")

    return redirect(f"/marks/{raceId}")

def contest_select():
    # Firestore からレース一覧を日付降順で取得
    races_ref = db.collection("races").order_by("date", direction="DESCENDING").get()

    options = []
    now = datetime.now()

    for doc in races_ref:
        data = doc.to_dict()

        # レース日付 + 15:00 を締切時刻として扱う
        race_date = datetime.strptime(data["date"] + " 15:00", "%Y-%m-%d %H:%M")

        # 締切済みフラグ
        is_closed = now > race_date

        options.append({
            "id": doc.id,
            "name": data.get("name"),
            "date": data.get("date"),
            "is_closed": is_closed
        })

    return render_template("contest_select.html", options=options)

@app.route("/contest", methods=["GET"])
def contest_select():
    races_ref = db.collection("races").order_by("date", direction="DESCENDING").get()

    options = []
    now = datetime.datetime.now()

    for doc in races_ref:
        data = doc.to_dict()
        race_date = datetime.datetime.strptime(data["date"] + " 15:00", "%Y-%m-%d %H:%M")
        is_closed = now > race_date

        options.append({
            "id": doc.id,
            "name": data.get("name"),
            "date": data.get("date"),
            "is_closed": is_closed
        })

    return render_template("contest_select.html", options=options)


@app.route("/contest/go", methods=["POST"])
def contest_go():
    race_id = request.form.get("raceId")

    # レース情報
    race_ref = db.collection("races").document(race_id)
    race = race_ref.get().to_dict()

    # 馬リスト（horses）
    horses_ref = race_ref.collection("horses")
    horses = [h.to_dict() for h in horses_ref.stream()]

    # 🔥 number でソート（ここが重要）
    horses.sort(key=lambda x: x["number"])

    return render_template(
        "marks.html",
        race=race,
        raceId=race_id,
        horses=horses,
        raceName=race["name"]   # ← これを追加！
    )

#----------------------
# ② メイン画面装飾
# -------------------------
@app.route("/main", methods=["GET", "POST"])
def main():
    print("METHOD:", request.method)

    # ★ アクセスカウント（GET のときだけ）
    #if request.method == "GET":
    #    counter_ref = db.collection("stats").document("page_counter")
    #    counter_ref.set({"count": admin_firestore.Increment(1)}, merge=True)

    # ★ アクセスログ
    db.collection("access_logs").add({
        "timestamp": datetime.datetime.now(),
        "ip": request.remote_addr
    })

    # ★ レース一覧（あなたの現行コードをそのまま使用）
    options = ["2026年うま王","2026年うま王収支表単勝","2026年うま王収支表馬連","2026年うま王収支表三連複",
               "0614宝塚記念","0613函館スプリントＳ",
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

    # ★ POST のときは race を受け取る（main.html のフォーム用）
    if request.method == "POST":
        race = request.form.get("race")
        return redirect(f"/main?race={race}")
    
    # ★ GET のときは URL から race を取得
    race = request.args.get("race", None)

    # ★ race があれば filename を作る
    #filename = f"{race}.png" if race else None
    filename = f"{race}.png" if race else "2026年うま王.png"


    # ★ カウント取得（あなたのコードをそのまま使用）
    counter_ref = db.collection("stats").document("page_counter")
    counter_doc = counter_ref.get()
    count = counter_doc.to_dict().get("count", 0)

    # ★ ニックネーム（URL パラメータから取得）
    nickname = request.args.get("nickname", "")

    return render_template("main.html",
                           nickname=nickname,
                           options=options,
                           race=race,
                           filename=filename,
                           count=count)

@app.route("/", methods=["GET"])
def index():
    # ★ 現在のカウントを取得
    counter_ref = db.collection("stats").document("page_counter")
    counter_doc = counter_ref.get()
    count = counter_doc.to_dict().get("count", 0)

    return render_template("index.html",
                           count=count,
                           original_name="")

@app.route("/countup")
def countup():
    counter_ref = db.collection("stats").document("page_counter")
    counter_ref.set({"count": admin_firestore.Increment(1)}, merge=True)
    return "ok"



@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# -------------------------
# ② レース苑エントリーID取得
# -------------------------
@app.route("/admin/entry")
def admin_entry():
    raceId = request.args.get("raceId")

    race_doc = db.collection("races").document(raceId).get()
    race = race_doc.to_dict()

    return render_template("entry.html", race=race, raceId=raceId)


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

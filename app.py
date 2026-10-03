#from google.cloud import firestore
from flask import Flask, request, render_template, redirect, session, make_response, flash, send_from_directory, jsonify
import os
import sys

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore as admin_firestore
import datetime
from zoneinfo import ZoneInfo

# --- ② Firebase 認証（Render / ローカル両対応） ---
import json
import tempfile

import os
from firebase_admin import credentials, initialize_app

from routes.calc_points import bp as calc_bp

from flask import url_for



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

# --- ポイント集計用 ---
app.register_blueprint(calc_bp)

@app.route("/race")
def race_select():
    races = []
    docs = db.collection("races").stream()
    for doc in docs:
        races.append(doc.id)
    print("★★★ race_select.html を返すよ ★★★")
    return render_template("race_select.html", options=races)


# 画像ファイル対応
#image_files = {
fixed_files = {    
    "2026年うま王": "2026年うま王.png",
    #"2026年うま王Summerコンテスト": "2026年うま王Summerコンテスト.png",
    "2026年うま王収支表単勝": "2026年うま王収支表単勝.png",
    "2026年うま王収支表馬連": "2026年うま王収支表馬連.png",
    "2026年うま王収支表三連複": "2026年うま王収支表三連複.png",
}

#### レース画像チョイスstart
# ★ static フォルダの PNG を自動読み込み
auto_files = {}
for filename in os.listdir("static"):
    if filename.endswith(".png"):
        race_name = filename.replace(".png", "")
        auto_files[race_name] = filename

# ★ 固定 + 自動 を合体
image_files = {**fixed_files, **auto_files}

# ★ レース一覧（options）も自動生成
#options = list(image_files.keys())
options = sorted(image_files.keys(), reverse=True)

#####　レース画像チョイスend
@app.route("/", methods=["GET"])
def index():
    # ★ 初回アクセスだけカウントアップ
    if not session.get("counted"):
        counter_ref = db.collection("stats").document("page_counter")
        counter_ref.set({"count": admin_firestore.Increment(1)}, merge=True)
        session["counted"] = True

    # ★ 現在のカウントを取得
    counter_ref = db.collection("stats").document("page_counter")
    counter_doc = counter_ref.get()
    count = counter_doc.to_dict().get("count", 0)

    return render_template("index.html", count=count)


# -------------------------
# 2026シリーズの入口（Summer / Autumn）
# -------------------------

@app.route("/2026/summer")
def summer2026_menu():
    return render_template("admin/main.html")   # ← 現行Summerのメイン画面


@app.route("/2026/autumn", methods=["GET", "POST"])
def autumn2026_menu():
    print("METHOD:", request.method)

    # ★ Autumn アクセスログ
    db.collection("access_logs_autumn").add({
        "timestamp": datetime.datetime.now(),
        "ip": request.remote_addr
    })

    # ★ Autumn 用 races を取得（Firestore 側で作る必要あり）
    #races_ref = db.collection("races_2026_autumn").get()
    #races_ref = db.collection(""baseCollection"").get()
    races_ref = db.collection("races").get()

    race_info = {}
    for doc in races_ref:
        data = doc.to_dict()
        race_info[doc.id] = data.get("grade", "OTHER")

    # ★ static の PNG 読み込み（Summer と同じ）
    image_files = {**fixed_files, **auto_files}

    # ★ Autumn 用 options
    options = [race_id for race_id in race_info.keys() if race_id in image_files]
    options = sorted(options, reverse=True)

    # ★ 色付け（Summer と同じ）
    options_with_color = []
    for opt in options:
        grade = race_info.get(opt, "OTHER")
        if grade == "G1":
            color = "blue"
        elif grade == "G2":
            color = "red"
        elif grade == "G3":
            color = "green"
        else:
            color = "black"
        options_with_color.append({"name": opt, "color": color})

    # ★ POST のときは race を受け取る
    if request.method == "POST":
        race = request.form.get("race")
        return redirect(f"/2026/autumn?race={race}")

    # ★ GET のとき race を取得
    race = request.args.get("race") or request.form.get("race")

    # ★ Autumn 用のデフォルト画像（必要なら変更）
    filename = image_files.get(race, "2026年うま王.png")

    nickname = request.args.get("nickname", "")

    return render_template("main_autumn.html",
                           nickname=nickname,
                           options=options_with_color,
                           race=race,
                           filename=filename,
                           image_files=fixed_files)


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
    
    # ★ 端末に保存されている前回の名前（＝自分の名前）
    saved_name = request.cookies.get("nickname")

    doc_ref = db.collection("users").document(nickname)
    doc = doc_ref.get()

    # Firestore に存在する場合
    if doc.exists:
        # ★ saved_name と一致 → 自分自身 → OK
        if saved_name == nickname:
            resp = make_response(redirect("/main?nickname=" + nickname))
            resp.set_cookie("nickname", nickname)
            return resp

        # ★ saved_name と違う → 他人の名前 → NG
        return render_template("index.html",
                               error="その登録名は既に使われています。",
                               nickname=nickname)

    # Firestore に存在しない → 新規登録
    doc_ref.set({"created": admin_firestore.SERVER_TIMESTAMP})

    resp = make_response(redirect("/main?nickname=" + nickname))
    resp.set_cookie("nickname", nickname)
    return resp



# -------------------------
# ② コンテスト比較表作成
# -------------------------
@app.route("/compare/<raceId>")
def compare(raceId):

    series = request.args.get("series", "summer")

    if series == "summer":
        baseCollection = "races"
    else:
        baseCollection = f"races_{series}"

    race_ref = db.collection(baseCollection).document(raceId)   
    horses_ref = race_ref.collection("horses").stream()

    # 出走表（馬番を数値としてソート）
    #horses_ref = db.collection("races").document(raceId).collection("horses").stream()
    horses_ref = race_ref.collection("horses").stream()

    horses = []
    for h in horses_ref:
        d = h.to_dict()
        horses.append({
            "id": h.id,
            "waku": d.get("waku"),
            "number": int(d.get("number")),   # ★ 数値化
            "name": d.get("name"),
            "finish": d.get("finish"),      # ← 追加！
            "pop": d.get("pop") or d.get("popularity") or d.get("populality"),  # ← どちらでも読めるように
            "winner": (d.get("finish") == "1")   # ← 追加！
        })

    horses = sorted(horses, key=lambda x: x["number"])

    # 参加ユーザー一覧（marks の直下のドキュメント名）
    #users_ref = db.collection("races").document(raceId).collection("marks").stream()
    users_ref = race_ref.collection("marks").stream()

    users = []
    for u in users_ref:
        d = u.to_dict()
        users.append(d.get("user") or u.id)   # ← user フィールドがあれば使う

    # 印データ（フィールドをそのまま読む）
    predictions = {}
    for user in users:
        #doc = db.collection("races").document(raceId).collection("marks").document(user).get()
        doc = race_ref.collection("marks").document(user).get()

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

@app.route("/admin/race_autumn")
def admin_race_autumn():
    return render_template("admin/race_autumn.html")



@app.route("/admin/race_autumn/entry")
def admin_race_autumn_entry():
    race_id = request.args.get("raceId")
    #★シリーズ切替ポイント★
    #series = request.args.get("series", "summer")
    series = request.args.get("series", "autumn")
    baseCollection = "races_2026_autumn" if series == "autumn" else "races"
    #baseCollection = "races_2027_winter" if series == "winter" else "races"
    #baseCollection = "races_2027_spring" if series == "spring" else "races"


    #horses_ref = db.collection("races_2026_autumn").document(race_id).collection("horses").get()
    horses_ref = db.collection(baseCollection).document(race_id).collection("horses").get()
    horses = [h.to_dict() for h in horses_ref]

    return render_template("admin/entry.html",
                       raceId=race_id,
                       horses=horses)



@app.route("/admin/race_autumn/save_entry", methods=["POST"])
def admin_race_autumn_save_entry():
    race_id = request.form.get("raceId")
    series = request.form.get("series", "summer")
    baseCollection = "races_2026_autumn" if series == "autumn" else "races"
    #series = request.args.get("series", "summer")
    #baseCollection = "races_2026_autumn" if series == "autumn" else "races"
    #baseCollection = "races_2027_winter" if series == "winter" else "races"
    #baseCollection = "races_2027_spring" if series == "spring" else "races"


    #race_doc = db.collection("races_2026_autumn").document(race_id).get()
    race_doc = db.collection(baseCollection).document(race_id).get()
    numHorses = int(race_doc.to_dict().get("numHorses", 6))

    # 参加者数
    numParticipants = request.form.get("numParticipants", "")
    isOfficial = request.form.get("isOfficial") == "on"

    #db.collection("races_2026_autumn").document(race_id).update({
    db.collection(baseCollection).document(race_id).update({
        "numParticipants": numParticipants,
        "isOfficial": isOfficial
    })

    # 馬ごとの情報保存
    for i in range(1, numHorses + 1):
        name = request.form.get(f"horseName{i}", "")
        finish = request.form.get(f"finish{i}", "")
        popularity = request.form.get(f"popularity{i}", "")

        #db.collection("races_2026_autumn").document(race_id).collection("horses").document(str(i)).update({
        db.collection(baseCollection).document(race_id).collection("horses").document(str(i)).update({
            "name": name,
            "finish": finish,
            "popularity": popularity
        })

    return redirect("/admin/menu")



#@app.route('/marks/<raceId>')
#def marks(raceId):

#    #race_ref = db.collection("races").document(raceId)
#    #race_doc = race_ref.get()

#    series = request.args.get("series", "summer")

#    if series == "summer":
#        baseCollection = "races"
#    else:
#        baseCollection = f"races_{series}"

#    race_ref = db.collection(baseCollection).document(raceId)
#    race_doc = race_ref.get()

#    nickname = request.args.get("nickname", "")

#    # ★ これが無かったから NameError が出てた
#    race = race_doc.to_dict()

#    # ⑥ レース名を取得
#    raceName = race_doc.to_dict().get("name")

#    # 馬データ取得
#    #horses_snap = race_ref.collection("horses").order_by("number").get()
#    #horses_snap = race_ref.collection("horses").get()
#    horses_snap = race_ref.collection("horses").order_by("waku").get()

#    horses = [
#        {
#            "name": doc.to_dict().get("name"),
#            "number": doc.to_dict().get("number"),
#            "waku": doc.to_dict().get("waku"),
#            "pop": doc.to_dict().get("pop"),
#            "finish": doc.to_dict().get("finish")
#        }
#        for doc in horses_snap
#    ]

#    # ⑥ raceName をテンプレートに渡す
#    return render_template(
#        "marks.html",
#        horses=horses,
#        raceId=raceId,
#        raceName=raceName,
#        race=race,        # ← これを追加！
#        nickname=nickname,   # ← ★これが必要！
#        series=series   # ← ★これが絶対必要！
#    )

@app.route("/marks_list")  #2026summer用
def marks_list():
    races_ref = db.collection("races").stream()

    race_summary = []
    user_set = set()  # 動的ヘッダー用

    for r in races_ref:
        race_id = r.id
        race = r.to_dict()

        # ★ 公式レースだけ表示（isOfficial が無い古いデータは True 扱い）
        if race.get("isOfficial", True) is not True:
            continue

        # 勝ち馬
        winner_query = db.collection("races").document(race_id)\
            .collection("horses").where("finish", "==", "1").get()

        winner_name = "-"
        winner_pop = "-"

        for w in winner_query:
            wd = w.to_dict()
            winner_name = wd.get("name", "-")
            winner_pop = wd.get("pop") or wd.get("populality")  or wd.get("popularity") or "-"


        # marks（ユーザー名 → 印）
        marks_docs = db.collection("races").document(race_id)\
            .collection("marks").stream()

        marks_dict = {}

        for m in marks_docs:
            user = m.id
            d = m.to_dict()

            if winner_name == "-":
                marks_dict[user] = "-"
            else:
                mark = d.get(winner_name, "-")
                marks_dict[user] = mark

            user_set.add(user)

        race_summary.append({
            "race_id": race_id,
            "grade": race.get("grade", ""),
            "date": race.get("date", ""),
            "race_name": race.get("name", ""),
            "winner_name": winner_name,
            "winner_pop": winner_pop,
            "participants": race.get("participants", "-"),   # ← ★これを追加
            "marks": marks_dict
        })

    user_list = sorted(list(user_set))
    
    # ★★★ 日付降順（新しいレースが上）
    race_summary = sorted(
        race_summary,
        key=lambda x: x["date"],
        reverse=True
    )

    return render_template(
        "marks_list.html",
        race_summary=race_summary,
        user_list=user_list
    )


@app.route("/marks_list_autumn")
def marks_list_autumn():
    baseCollection = "races_2026_autumn"

    races_ref = db.collection(baseCollection).stream()

    race_summary = []
    user_set = set()

    for r in races_ref:
        race_id = r.id
        race = r.to_dict()

        if race.get("isOfficial", True) is not True:
            continue

        # 勝ち馬
        winner_query = db.collection(baseCollection).document(race_id)\
            .collection("horses").where("finish", "==", "1").get()

        winner_name = "-"
        winner_pop = "-"

        for w in winner_query:
            wd = w.to_dict()
            winner_name = wd.get("name", "-")
            winner_pop = wd.get("pop") or wd.get("populality") or wd.get("popularity") or "-"

        # marks
        marks_docs = db.collection(baseCollection).document(race_id)\
            .collection("marks").stream()

        marks_dict = {}

        for m in marks_docs:
            user = m.id
            d = m.to_dict()

            if winner_name == "-":
                marks_dict[user] = "-"
            else:
                mark = d.get(winner_name, "-")
                marks_dict[user] = mark

            user_set.add(user)

        race_summary.append({
            "race_id": race_id,
            "grade": race.get("grade", ""),
            "date": race.get("date", ""),
            "race_name": race.get("name", ""),
            "winner_name": winner_name,
            "winner_pop": winner_pop,
            "participants": race.get("participants", "-"),
            "marks": marks_dict
        })

    user_list = sorted(list(user_set))

    race_summary = sorted(
        race_summary,
        key=lambda x: x["date"],
        reverse=True
    )

    return render_template(
        "marks_list_autumn.html",
        race_summary=race_summary,
        user_list=user_list
    )




@app.route("/select_race")
def select_race():
    races = db.collection("races").order_by("date", direction="DESCENDING").get()

    options = []
    for doc in races:
        d = doc.to_dict()
        options.append({
            "id": doc.id,
            "name": d["name"],
            "date": d["date"],
            "series": d.get("series", "2026_autumn"),   # ← これを追加
            "is_closed": d.get("is_closed", False)
        })

    # ★ 未済 → 済 の境界 index を計算
    boundary_index = None
    for i, r in enumerate(options):
        if r["is_closed"]:
            boundary_index = i
            break

    return render_template(
        "contest_select.html",
        options=options,
        boundary_index=boundary_index
    )




#@app.route("/marks_go", methods=["POST"])
#def marks_go():
#    raceId = request.form["raceId"]
#    if not raceId:
#        # HTML と同じ挙動：選択してないなら戻す
#        flash("レースを選択してください")
#        return redirect("/contest")
#    return redirect(f"/marks/{raceId}")

def contest_select():
    # Firestore からレース一覧を日付降順で取得
    #races_ref = db.collection("races").order_by("date", direction="DESCENDING").get()
    # ★ 現在のシリーズを決める（例：2026_autumn）
    current_series = "2026_autumn"
    # ★ シリーズ別コレクションを読む
    races_ref = db.collection(f"races_{current_series}").order_by("date", direction="DESCENDING").get()

    options = []
    now = datetime.datetime.now()

    for doc in races_ref:
        data = doc.to_dict()

        # レース日付 + 15:00 を締切時刻として扱う
        race_date = datetime.datetime.strptime(data["date"] + " 15:00", "%Y-%m-%d %H:%M")

        # 締切済みフラグ
        is_closed = now > race_date

        options.append({
            "id": doc.id,
            "name": data.get("name"),
            "date": data.get("date"),
            "series": data.get("series"),   # autumn が入るはず
            "is_closed": is_closed
        })

    return render_template("contest_select.html", options=options)

@app.route("/contest", methods=["GET"])
def contest_select():
    #races_ref = db.collection("races").order_by("date", direction="DESCENDING").get()

    #★シリーズ切替ポイント★
    # URLパラメータからシリーズ取得（例：?series=2026_autumn）
    series = request.args.get("series", "summer")

    # シリーズ名 → コレクション名を自動生成
    # 例： "2026_autumn" → "races_2026_autumn"
    #baseCollection = f"races_{series}"
    if series == "summer":
        baseCollection = "races"
    else:
        baseCollection = f"races_{series}"

    races_ref = db.collection(baseCollection).order_by("date", direction="DESCENDING").get()

    options = []
    now = datetime.datetime.now()

    for doc in races_ref:
        data = doc.to_dict()

        # ★ 公式レースだけ表示（isOfficial が無い古いデータは True 扱い）
        if data.get("isOfficial", True) is not True:
            continue

        race_date = datetime.datetime.strptime(data["date"] + " 15:00", "%Y-%m-%d %H:%M")
        is_closed = now > race_date

        options.append({
            "id": doc.id,
            "name": data.get("name"),
            "date": data.get("date"),
            "series": series,   # ★ これを追加するだけ
            "is_closed": is_closed
        })

    #return render_template("contest_select.html", options=options)
    return render_template("contest_select.html", options=options, series=series)


@app.route("/contest/go", methods=["GET", "POST"])
def contest_go():
    #race_id = request.form.get("raceId")
    race_id = request.args.get("raceId")
    mode = request.args.get("mode")  # ← ★これを追加
    nickname = request.args.get("nickname")   # ← ★これが絶対必要



    # レース情報
    #race_ref = db.collection("races").document(race_id)
    #race = race_ref.get().to_dict()

    series = request.args.get("series", "summer")

    if series == "summer":
        baseCollection = "races"
    else:
        baseCollection = f"races_{series}"

    race_ref = db.collection(baseCollection).document(race_id)
    race = race_ref.get().to_dict()

    # 馬リスト（horses）
    #horses_ref = race_ref.collection("horses")
    #horses = [h.to_dict() for h in horses_ref.stream()]
    #horses.sort(key=lambda x: x["number"])
    # 馬リスト（horses）
    horses_ref = race_ref.collection("horses")
    horses = []
    for h in horses_ref.stream():
        d = h.to_dict()
        d["number"] = int(d["number"])   # ★ ここが今回のバグの原因だった
        horses.append(d)
    horses.sort(key=lambda x: int(x["number"]))




    # ★ compare の場合は compare に飛ばす
    if mode == "compare":
        #return redirect(f"/compare/{race_id}")
        return redirect(f"/compare/{race_id}?series={series}")
    
    #if mode == "marks":
    #    return redirect(f"/marks/{race_id}?nickname={nickname}")

    if mode == "marks":
        return render_template(
            "marks.html",
            race=race,
            raceId=race_id,
            horses=horses,
            raceName=race["name"],
            nickname=nickname,
            series=series
        )



    # ★ それ以外（marks）は今まで通り marks.html を返す
    return render_template(
        "marks.html",
        race=race,
        raceId=race_id,
        horses=horses,
        raceName=race["name"],
        series=series
    )

#----------------------
# ② point獲得推移グラフ化（ルート追加）    2026年夏
# -------------------------
@app.route("/graph")
def graph():
    return render_template("graph.html")

#----------------------
# ② point獲得推移グラフ化    2026年夏
# ----------------------
@app.route("/api/summer_points")
def api_summer_points():
    db = admin_firestore.client()

    races_ref = db.collection("races").order_by("date")
    race_docs = races_ref.stream()

    labels = []
    summer_race_ids = []
    race_id_to_name = {}

    start_date = datetime.datetime(2026, 7, 1)
    end_date   = datetime.datetime(2026, 9, 30)

    for doc in race_docs:
        data = doc.to_dict()
        race_date = data["date"]

        # ★ 文字列なら datetime に変換
        if isinstance(race_date, str):
            race_date = datetime.datetime.strptime(race_date, "%Y-%m-%d")
        # ★ Timestamp なら datetime に変換
        elif hasattr(race_date, "timestamp"):
            race_date = race_date.replace(tzinfo=None)

        # Timestamp → datetime
        #if hasattr(race_date, "timestamp"):
        #    race_date = race_date.replace(tzinfo=None)

        if start_date <= race_date <= end_date:
            labels.append(data["name"])
            summer_race_ids.append(doc.id)

        race_id_to_name[doc.id] = data["name"]

    result = {
        "labels": labels,
        "points": {}
    }

    users_ref = db.collection("points")
    users = users_ref.stream()

    for user in users:
        user_id = user.id
        user_races_ref = db.collection("points").document(user_id).collection("races")
        user_race_docs = user_races_ref.stream()

        race_point_list = []

        for doc in user_race_docs:
            data = doc.to_dict()
            race_id = doc.id

            if race_id in summer_race_ids:
                race_point_list.append({
                    "race": race_id_to_name.get(race_id),
                    "point": data.get("point", 0)
                })

        result["points"][user_id] = race_point_list

    return jsonify(result)

#----------------------
# ② グラフ化    2026年夏
# ----------------------
@app.route("/summer_graph")
def summer_graph():
    return render_template("graph.html")


#----------------------
# ② point獲得推移グラフ化（ルート追加）    2026年秋
# -------------------------
@app.route("/autumn_graph")
def autumn_graph():
    return render_template("graph_autumn.html")

#----------------------
# ② point獲得推移グラフ化    2026年秋
# ----------------------
@app.route("/api/autumn_points")
def api_autumn_points():
    db = admin_firestore.client()

    races_ref = db.collection("races_2026_autumn").order_by("date")
    #races_ref = db.collection(baseCollection).order_by("date")
    race_docs = races_ref.stream()

    labels = []
    autumn_race_ids = []
    race_id_to_name = {}

    # Autumn シリーズの期間（例：10月〜12月）
    start_date = datetime.datetime(2026, 10, 1)
    end_date   = datetime.datetime(2026, 12, 31)

    for doc in race_docs:
        data = doc.to_dict()
        race_date = data["date"]

        if isinstance(race_date, str):
            race_date = datetime.datetime.strptime(race_date, "%Y-%m-%d")
        elif hasattr(race_date, "timestamp"):
            race_date = race_date.replace(tzinfo=None)

        if start_date <= race_date <= end_date:
            labels.append(data["name"])
            autumn_race_ids.append(doc.id)

        race_id_to_name[doc.id] = data["name"]

    result = {
        "labels": labels,
        "points": {}
    }

    users_ref = db.collection("points_2026_autumn")
    users = users_ref.stream()

    for user in users:
        user_id = user.id
        user_races_ref = db.collection("points_2026_autumn").document(user_id).collection("races")
        user_race_docs = user_races_ref.stream()

        race_point_list = []

        for doc in user_race_docs:
            data = doc.to_dict()
            race_id = doc.id

            if race_id in autumn_race_ids:
                race_point_list.append({
                    "race": race_id_to_name.get(race_id),
                    "point": data.get("point", 0)
                })

        result["points"][user_id] = race_point_list

    return jsonify(result)


#----------------------
# ② WEBアイコン化
# -------------------------
@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

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
    #options = ["2026年うま王","2026年うま王収支表単勝","2026年うま王収支表馬連","2026年うま王収支表三連複",
    #           "0614宝塚記念","0613函館スプリントＳ",
    #           "0607安田記念",
    #           "0104中山金杯","0104京都金杯"]

    #filename = None
    #race = None

    # ★★★ Firestore から races を全部取得（ここに入れる）
    #★シリーズ切替ポイント★
    #2026summer
    summer2026_ref = db.collection("races").get()
    #2026autumn
    autumn2026_ref = db.collection("races_2026_autumn").get()    

    # 合体
    races_ref = list(summer2026_ref) + list(autumn2026_ref)


    race_info = {}
    for doc in races_ref:
        data = doc.to_dict()
        race_info[doc.id] = data.get("grade", "OTHER")

    # ★★★ static の PNG を読む（固定＋自動）
    image_files = {**fixed_files, **auto_files}

    ###ファイル名検証start
    ##print("=== Firestore race_info keys ===")
    #for key in race_info.keys():
    #    print(repr(key))
    #print("=== image_files keys ===")
    #for key in image_files.keys():
    #    print(repr(key))
    ###ファイル名検証end

    # ★★★ Firestore に存在するレースだけを options にする
    options = [race_id for race_id in race_info.keys() if race_id in image_files]
    # ★ 固定ファイルも追加
    fixed_options = [
    "2026年うま王",
    #"2026年うま王Summerコンテスト",
    "2026年うま王収支表単勝",
    "2026年うま王収支表馬連",
    "2026年うま王収支表三連複"
    ]

    options = fixed_options + sorted(options, reverse=True)

    # ★★★ 色付け
    options_with_color = []
    for opt in options:
        grade = race_info.get(opt, "OTHER")
        if grade == "G1":
            color = "blue"
        elif grade == "G2":
            color = "red"
        elif grade == "G3":
            color = "green"
        else:
            color = "black"
        options_with_color.append({"name": opt, "color": color})

    # ★ POST のときは race を受け取る（main.html のフォーム用）
    if request.method == "POST":
        race = request.form.get("race")
        return redirect(f"/main?race={race}")

    # GET のとき race を取得
    #race = request.args.get("race", None)
    # filename を1回だけ作る
    #filename = image_files.get(race, "2026年うま王.png")
    race = request.args.get("race") or request.form.get("race")
    filename = image_files.get(race, "2026年うま王.png")


    
    # ★ GET のときは URL から race を取得
    #race = request.args.get("race", None)

    # ★ race があれば filename を作る
    #filename = f"{race}.png" if race else None
    #filename = f"{race}.png" if race else "2026年うま王.png"


    # ★ カウント取得（あなたのコードをそのまま使用）
    counter_ref = db.collection("stats").document("page_counter")
    counter_doc = counter_ref.get()
    count = counter_doc.to_dict().get("count", 0)

    # ★ ニックネーム（URL パラメータから取得）
    nickname = request.args.get("nickname", "")

    return render_template("main.html",
                           nickname=nickname,
                           options=options_with_color,
                           race=race,
                           filename=filename,
                           count=count,
                           image_files=fixed_files)

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

    # URL から series を受け取る（ここが必須）
    series = request.args.get("series", "summer")
    # シリーズ判定
    if series == "autumn":
        baseCollection = "races_2026_autumn"
    else:
        baseCollection = "races"

    #race_doc = db.collection("races").document(raceId).get()
    race_doc = db.collection(baseCollection).document(raceId).get()    
    race = race_doc.to_dict()

    #return render_template("admin/entry.html", race=race, raceId=raceId)
    return render_template(
        "admin/entry.html",
        race=race,
        raceId=raceId,
        series=series,
        baseCollection=baseCollection
    )

# -------------------------
# ② 管理者メニュー
# -------------------------
@app.route("/admin/menu")
def admin_menu():
    nickname = request.args.get("nickname")  # ← 追加

    #★シリーズ切替ポイント★
    series_list = ["2026_autumn"]
    #series_list = ["2027_winter"]
    #series_list = ["2027_spring"]
    race_list = []

    # summer（初回シリーズのみ）
    #races_summer = db.collection("races").stream()
    #race_list += [r.id for r in races_summer]

    # 各シリーズ（２回目シリーズ以降）
    for s in series_list:
        races = db.collection(f"races_{s}").stream()
        race_list += [r.id for r in races]

    race_list = sorted(race_list, reverse=True)

    #races_ref = db.collection("races").stream()
    #race_list = sorted([r.id for r in races_ref], reverse=True)

    return render_template("admin_menu.html",
                           race_list=race_list,
                           nickname=nickname)


@app.route("/admin/entry/new")
def admin_entry_new():
    return render_template(
        "admin/entry.html",
        race=None,
        raceId="new",
        series="autumn"   # ← 必須
    )

#@app.route("/admin/entry/select")
#def admin_entry_select():
#    races = db.collection("races").stream()
#    race_list = sorted([r.id for r in races], reverse=True)
#    return render_template("race_select.html", race_list=race_list)

@app.route("/admin/entry/select")
def admin_entry_select():

    series = request.args.get("series", "summer")

    if series == "autumn":
        baseCollection = "races_2026_autumn"
    else:
        baseCollection = "races"

    races = db.collection(baseCollection).stream()
    race_list = sorted([r.id for r in races], reverse=True)

    return render_template("race_select.html", race_list=race_list, series=series)


@app.route("/admin/entry/edit")
def admin_entry_edit():
    series = request.args.get("series", "summer")

    # ★ ここが本丸：シリーズごとにコレクションを切り替える
    if series == "autumn":
        baseCollection = "races_2026_autumn"
    else:
        baseCollection = "races"

    raceId = request.args.get("raceId")
    race_doc = db.collection(baseCollection).document(raceId).get()
    race = race_doc.to_dict()

    return render_template(
        "admin/entry.html",
        race=race,
        raceId=raceId,
        series=series
    )

# -------------------------
# ② マークの結果集計
# -------------------------
@app.route("/admin/marks/<path:race_id>")
def admin_marks(race_id):
    db = admin_firestore.client()

    #★シリーズ切替ポイント★
    #race_ref = db.collection("races").document(race_id)
    #series = request.args.get("series", "summer")
    #baseCollection = "races" if series == "summer" else f"races_{series}"
    series = request.args.get("series", "autumn")
    baseCollection = "races" if series == "summer" else f"races_{series}"

    race_ref = db.collection(baseCollection).document(race_id)

    # --- レース情報 ---
    race_doc = race_ref.get()
    race_data = race_doc.to_dict()

    # --- 勝ち馬（finish=1） ---
    horses_ref = race_ref.collection("horses")
    winner_query = horses_ref.where("finish", "==", "1").stream()

    winner_name = None
    #winner_popularity = None
    winner_populality = None

    print("DEBUG race_id:", race_id)
    print("DEBUG horses:", [h.to_dict() for h in horses_ref.stream()])

    for h in winner_query:
        hdata = h.to_dict()
        print("DEBUG hdata:", hdata)  # ← for の中で使う
        winner_name = hdata.get("name")
        winner_populality = (
        hdata.get("populality")
            or hdata.get("pop")
            or hdata.get("popu")
            or hdata.get("popularity")
            or "1"
        )
        break

    # --- 全ユーザーの印 ---
    marks_ref = race_ref.collection("marks")
    marks_docs = marks_ref.stream()

    marks_data = {}
    for doc in marks_docs:
        nickname = doc.id
        marks_data[nickname] = doc.to_dict()

    return render_template(
        "admin/marks.html",
        race_id=race_id,
        race=race_data,
        winner_name=winner_name,
        winner_populality=winner_populality,
        marks_data=marks_data
    )

# -------------------------
# ② ランキング作成(２０２６Summer)
# -------------------------
@app.route("/summer_ranking")
def summer_ranking():
    db = admin_firestore.client()
    points_ref = db.collection("points").stream()
    #now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")    
    now = datetime.datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")

    ranking_list = []
    for p in points_ref:
        data = p.to_dict()
        data["nickname"] = p.id
        ranking_list.append(data)

    ranking_list = sorted(
    ranking_list,
    key=lambda x: (
        x["total"],
        x["hitUma"],
        x["hitMaru"],
        x["hitSankaku"],
        x["hitBatsu"],
        x["hitG1"],
        x["hitG2"],
        x["hitG3"]
    ),
    reverse=True
)


    return render_template(
        "ranking.html", 
        ranking_list=ranking_list,
        now=now,
        series="summer"
    )

# -------------------------
# ② ランキング作成(2026Autumn)
# -------------------------
@app.route("/autumn_ranking")
def autumn_ranking():
    db = admin_firestore.client()
    points_ref = db.collection("points_2026_autumn").stream()
    now = datetime.datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")

    ranking_list = []

    for p in points_ref:
        data = p.to_dict()
        data["nickname"] = p.id
        ranking_list.append(data)


    ranking_list = sorted(
        ranking_list,
        key=lambda x: (
            x["total"],
            x["hitUma"],
            x["hitMaru"],
            x["hitSankaku"],
            x["hitBatsu"],
            x["hitG1"],
            x["hitG2"],
            x["hitG3"]
        ),
        reverse=True
    )

    #return render_template("ranking_autumn.html", ranking_list=ranking_list, now=now)
    return render_template(
        "ranking_autumn.html",
        ranking_list=ranking_list,
        now=now,
        series="2026_autumn"
    )


# -------------------------
# ② 大会対象レースのチェック
# -------------------------
# 2026summer専用
@app.route("/admin/race/save", methods=["POST"])
def admin_race_save():

    # ★ SUMMER 固定（必須）
    series = "summer"
    baseCollection = "races"

    #race_id = request.form.get("raceId")
    race_name = request.form.get("raceName")
    race_date = request.form.get("raceDate")
    race_grade = request.form.get("raceGrade")   # ← ★これが必要！
    numHorses = request.form.get("numHorses")  # ★ これを必ず追加！

    # ★ raceId を自動生成（これが必要）
    race_id = f"{race_date.replace('-', '')}_{race_name}"

    # ★ デフォルト true（公式レース）
    isOfficial = request.form.get("isOfficial", "true") == "true"
     
    db.collection(baseCollection).document(race_id).set({
        "name": race_name,
        "date": race_date,
        "grade": race_grade,        # ← ★追加
        "numHorses": numHorses,   # ← ★これが必要
        "isOfficial": isOfficial
    })

    return redirect(f"/admin/entry?raceId={race_id}&series=summer")

# 2026autumn専用
@app.route("/admin/race/save_autumn", methods=["POST"])
def admin_race_save_autumn():

    # ★シリーズ切り替え（必須）
    series = request.form.get("series", "autumn")   # autumn固定でもOK
    baseCollection = "races_2026_autumn" if series == "autumn" else "races"    
    race_name = request.form.get("raceName")
    race_date = request.form.get("raceDate")
    race_grade = request.form.get("raceGrade")
    numHorses = request.form.get("numHorses")

    race_id = f"{race_date.replace('-', '')}_{race_name}"
    isOfficial = request.form.get("isOfficial", "true") == "true"

    #db.collection("races_2026_autumn").document(race_id).set({
    db.collection(baseCollection).document(race_id).set({
        "name": race_name,
        "date": race_date,
        "grade": race_grade,
        "numHorses": numHorses,
        "isOfficial": isOfficial
    })

    return redirect(f"/admin/entry?raceId={race_id}&series=autumn")

#★シリーズ切替ポイント★
# 2027winter専用作ってください
#@app.route("/admin/race/save_2027_winter", methods=["POST"])
#def admin_race_save_winter():


@app.route("/admin/race_list")
def admin_race_list():
    races_ref = db.collection("races").order_by("date").stream()

    races = []
    for doc in races_ref:
        data = doc.to_dict()
        races.append({
            "id": doc.id,
            "name": data.get("name"),
            "date": data.get("date"),
            "grade": data.get("grade"),
            "isOfficial": data.get("isOfficial", True)
        })

    return render_template("admin/race_list.html", races=races)

@app.route("/admin/race_edit/<race_id>", methods=["GET"])
def admin_race_edit(race_id):
    race_ref = db.collection("races").document(race_id)
    race_doc = race_ref.get()

    if not race_doc.exists:
        return "Race not found", 404

    race = race_doc.to_dict()
    race["id"] = race_id

    return render_template("admin/race_edit.html", race=race)

@app.route("/admin/race_update/<race_id>", methods=["POST"])
def admin_race_update(race_id):
    race_ref = db.collection("races").document(race_id)

    name = request.form.get("name")
    date = request.form.get("date")
    grade = request.form.get("grade")
    isOfficial = request.form.get("isOfficial") == "true"

    race_ref.update({
        "name": name,
        "date": date,
        "grade": grade,
        "isOfficial": isOfficial
    })

    return redirect("/admin/race_list")


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

from flask import Blueprint, jsonify
from firebase_admin import firestore

bp = Blueprint('calc', __name__)

# 印ポイント
MARK_POINTS = {
    "◎": 10,
    "○": 5,
    "〇": 5,
    "▲": 3,
    "x": 1,
    "×": 1
}

# 格倍率
GRADE_MULTI = {
    "G1": 3,
    "G2": 2,
    "G3": 1
}

@bp.route("/calc_points/<race_id>", methods=["POST"])
def calc_points(race_id):
    db = firestore.client()

    race_ref = db.collection("races").document(race_id)

    # --- ① レース情報取得 ---
    race_doc = race_ref.get()
    if not race_doc.exists:
        return jsonify({"error": "race not found"}), 404

    race_data = race_doc.to_dict()

    # ★ 管理者が対象外にしたレースは集計しない
    if not race_data.get("isOfficial", False):
        return jsonify({"error": "this race is not official"}), 400

    grade = race_data.get("grade", "G3")
    multiplier = GRADE_MULTI.get(grade, 1)

    # --- ② 勝ち馬を取得（finish=1） ---
    horses_ref = race_ref.collection("horses")
    winner_query = horses_ref.where("finish", "==", "1").stream()

    winner_name = None
    winner_data = None

    for h in winner_query:
        winner_data = h.to_dict()
        winner_name = winner_data.get("name")
        break

    if not winner_name:
        return jsonify({"error": "winner not found"}), 400

    # --- ③ marks の全ユーザーを取得 ---
    marks_ref = race_ref.collection("marks")
    marks_docs = marks_ref.stream()

    for doc in marks_docs:
        nickname = doc.id
        marks = doc.to_dict()

        # --- ④ 勝ち馬の印を取得 ---
        mark = marks.get(winner_name, "")

        if mark not in MARK_POINTS:
            base_point = 0
        else:
            base_point = MARK_POINTS[mark]

        # 人気（pop / popularity / populality）を取得
        raw_pop = (
            winner_data.get("pop")
            or winner_data.get("popularity")
            or winner_data.get("populality")
            or "1"
        )
        popularity = int(str(raw_pop).translate(str.maketrans("０１２３４５６７８９", "0123456789")))

        # --- ⑤ final_point 計算 ---
        final_point = base_point * multiplier * popularity

        # --- ⑥ レース単位の結果を保存（mark と grade も保存） ---
        # --- ⑥ レース単位の結果を保存（mark と grade も保存） ---
        race_point_ref = (
            db.collection("points")
            .document(nickname)
            .collection("races")
            .document(race_id)
        )
        race_point_ref.set({
            "point": final_point,
            "mark": mark,
            "grade": grade
        })

        # ★★★ 俊裕さんに「ここに races_ref を再取得しろ」と言ってる ★★★
        races_ref = (
            db.collection("points")
            .document(nickname)
            .collection("races")
            .stream()
        )
        # ★★★ さらにもう一度 stream() を呼ぶ（これが必要） ★★★
        # Firestore の反映遅延対策
        races_ref = (
            db.collection("points")
            .document(nickname)
            .collection("races")
            .stream()
        )

        # ★★★ ここからここまで ★★★

        #--- ⑦ total（全レースのポイント合計）を再計算 ---
        total = 0
        for r in races_ref:
            d = r.to_dict()
            raceId2 = r.id

            race_doc2 = db.collection("races").document(raceId2).get()
            race_data2 = race_doc2.to_dict()

            if race_data2.get("isOfficial", False):
                total += d.get("point", 0)

        # --- ⑧ 的中数再計算（★ここで races_ref を再取得する必要がある）
        races_ref = (
            db.collection("points")
            .document(nickname)
            .collection("races")
            .stream()
        )
   

        hitUma = hitMaru = hitSankaku = hitBatsu = 0
        hitG1 = hitG2 = hitG3 = 0

        for r in races_ref:
            d = r.to_dict()
            raceId2 = r.id

            # レース情報を取得
            race_doc2 = db.collection("races").document(raceId2).get()
            race_data2 = race_doc2.to_dict()

            # ★ 公式レースだけカウントする
            if not race_data2.get("isOfficial", False):
                continue

            # ★ 公式レースかつ当たりレースだけ
            if d.get("point", 0) > 0:
                m = d.get("mark")
                g = d.get("grade")

                if m == "◎":
                    hitUma += 1
                elif m in ["○", "〇"]:
                    hitMaru += 1
                elif m == "▲":
                    hitSankaku += 1
                elif m in ["x", "×"]:
                    hitBatsu += 1

                if g == "G1":
                    hitG1 += 1
                elif g == "G2":
                    hitG2 += 1
                elif g == "G3":
                    hitG3 += 1

        # --- ⑨ 累積結果を保存 ---
        point_ref = db.collection("points").document(nickname)
        point_ref.set({
            "total": total,
            "hitUma": hitUma,
            "hitMaru": hitMaru,
            "hitSankaku": hitSankaku,
            "hitBatsu": hitBatsu,
            "hitG1": hitG1,
            "hitG2": hitG2,
            "hitG3": hitG3
        })

    return jsonify({
        "race": race_id,
        "winner": winner_name,
        "grade": grade,
        "multiplier": multiplier
    })

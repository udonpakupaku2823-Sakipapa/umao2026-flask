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

        # --- ⑦ total（全レースのポイント合計）を再計算 ---
        races_ref = (
            db.collection("points")
            .document(nickname)
            .collection("races")
            .stream()
        )

        total = 0
        for r in races_ref:
            d = r.to_dict()
            total += d.get("point", 0)

        # --- ⑧ 全レースの累積件数を再計算 ---
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
            if d.get("point", 0) > 0:  # 当たりレースだけ
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

console.log("STEP2 entry.js 読み込み完了");

// Firestore
const db = firebase.firestore();

// raceId を URL から取得
const urlParams = new URLSearchParams(window.location.search);
const raceId = urlParams.get("raceId");

if (!raceId) {
    alert("raceId が URL にありません");
    throw new Error("raceId missing");
}

// 枠番ロジック（俊裕さん仕様）
function generateWaku(num) {
    let wakuList = [];

    if (num <= 8) {
        for (let w = 1; w <= num; w++) {
            wakuList.push({ waku: w, count: 1 });
        }
        return wakuList;
    }

    if (num <= 16) {
        let remaining = num;
        for (let w = 1; w <= 8; w++) {
            wakuList.push({ waku: w, count: 1 });
            remaining--;
        }
        for (let w = 8; w >= 1 && remaining > 0; w--) {
            wakuList[w - 1].count++;
            remaining--;
        }
        return wakuList;
    }

    if (num <= 18) {
        let remaining = num;
        for (let w = 1; w <= 8; w++) {
            wakuList.push({ waku: w, count: 2 });
            remaining -= 2;
        }
        for (let w = 8; w >= 1 && remaining > 0; w--) {
            wakuList[w - 1].count++;
            remaining--;
        }
        return wakuList;
    }
}

// STEP2 初期ロード
async function loadEntry() {
    // レース情報取得
    const raceDoc = await db.collection("races").doc(raceId).get();
    if (!raceDoc.exists) {
        alert("レースデータが存在しません");
        return;
    }

    const race = raceDoc.data();
    const num = Number(race.numHorses);

    // ★ 参加者数を呼び出して反映
    if (race.participants) {
        document.getElementById("participants").value = race.participants;
    }

    // 既存の馬データを取得
    const horsesSnap = await db.collection("races")
        .doc(raceId)
        .collection("horses")
        .get();

    let existing = {};
    horsesSnap.forEach(doc => {
        existing[doc.id] = doc.data();
    });

    // 枠番生成
    let wakuList = generateWaku(num);
    wakuList.sort((a, b) => a.waku - b.waku);

    // HTML 生成
    let html = "<table border='1'><tr><th>枠</th><th>馬</th><th>馬名</th><th>着</th><th>人</th></tr>";

    let horseNumber = 1;
    for (const block of wakuList) {
        for (let i = 0; i < block.count; i++) {

            const ex = existing[String(horseNumber)] || {};

            html += `
                <tr>
                    <td>${block.waku}</td>
                    <td>${horseNumber}</td>
                    <td><input type="text" id="horse-${horseNumber}" value="${ex.name || ""}" placeholder="馬名"></td>
                    <td><input type="number" id="finish-${horseNumber}" min="1" max="18" value="${ex.finish || ""}" placeholder="着"></td>
                    <td><input type="number" id="pop-${horseNumber}" min="1" max="18" value="${ex.populality || ""}" placeholder="人"></td>
                </tr>
            `;



            horseNumber++;
        }
    }

    html += "</table>";

    document.getElementById("entry-area").innerHTML = html;
    document.getElementById("save-btn").style.display = "inline-block";
}


// 保存処理
document.getElementById("save-btn").addEventListener("click", async () => {
    const raceDoc = await db.collection("races").doc(raceId).get();
    const num = Number(raceDoc.data().numHorses);

    let wakuList = generateWaku(num);
    wakuList.sort((a, b) => a.waku - b.waku);

    let horseNumber = 1;

    for (const block of wakuList) {
        for (let i = 0; i < block.count; i++) {

            const name = document.getElementById(`horse-${horseNumber}`).value;
            if (!name) {
                alert("馬名が未入力です");
                return;
            }

            const finish = document.getElementById(`finish-${horseNumber}`).value || null;
            const pop = document.getElementById(`pop-${horseNumber}`).value || null;

            await db.collection("races")
                .doc(raceId)
                .collection("horses")
                .doc(String(horseNumber))
                .set({
                    name: name,
                    number: horseNumber,
                    waku: block.waku,
                    finish: finish,
                    populality: pop
                });

            horseNumber++;
        }
    }

    //document.getElementById("go-marks").addEventListener("click", () => {
    //const nickname = localStorage.getItem("nickname");
    //window.location.href = `/marks/${raceId}?nickname=${nickname}`;
    //});


    //参加者数を保存
    const participantsValue = document.getElementById("participants").value.trim();
    const participants = participantsValue ? Number(participantsValue) : null;

    await db.collection("races").doc(raceId).update({
        participants: participants
    });



    // ★★★ ここに追加する（公開チェック保存） ★★★
    const isOfficial = document.getElementById("isOfficial").checked;

    await db.collection("races").doc(raceId).update({
        isOfficial: isOfficial
    });
    // ★★★★★★★★★★★★★★★★★★★★★★★★★★★★

    document.getElementById("msg").textContent = "保存しました！";
});

// ★ 枠番・馬番生成ボタン（ここが最適）
document.getElementById("generate-btn").addEventListener("click", () => {
    loadEntry();

    // 参加者数欄を生成して表示
    document.getElementById("participants-area").innerHTML = `
        <label for="participants">参加者数：</label>
        <input type="number" id="participants" min="1" placeholder="例：12">
    `;
    document.getElementById("participants-area").style.display = "block";

});

// 初期ロード実行
//loadEntry();
console.log("entry.js 読み込まれた");
//console.log("★ この entry.js は最新のファイルです");
if (!raceIdFromServer) {
    console.log("新規レース登録モード");
} else {
    console.log("既存レース編集モード：", raceIdFromServer);
}



const db = firebase.firestore();

// ★ 枠番ロジック（俊裕の表を完全再現）
function generateWaku(num) {
    let wakuList = [];

    // --- ① 1〜8頭：1枠1頭 ---
    if (num <= 8) {
        for (let w = 1; w <= num; w++) {
            wakuList.push({ waku: w, count: 1 });
        }
        return wakuList;
    }

    // --- ② 9〜16頭：外枠から2頭ずつ、余りは内枠に1頭 ---
    if (num <= 16) {
        let remaining = num;

        // まず全枠に1頭ずつ（8頭）
        for (let w = 1; w <= 8; w++) {
            wakuList.push({ waku: w, count: 1 });
            remaining--;
        }

        // 残りを外枠から2頭目として追加
        for (let w = 8; w >= 1 && remaining > 0; w--) {
            wakuList[w - 1].count++;
            remaining--;
        }

        return wakuList;
    }

    // --- ③ 17〜18頭：外枠から3頭、残りは2頭ずつ ---
    if (num <= 18) {
        let remaining = num;

        // まず全枠に2頭ずつ（16頭）
        for (let w = 1; w <= 8; w++) {
            wakuList.push({ waku: w, count: 2 });
            remaining -= 2;
        }

        // 残りを外枠から3頭目として追加
        for (let w = 8; w >= 1 && remaining > 0; w--) {
            wakuList[w - 1].count++;
            remaining--;
        }

        return wakuList;
    }
}

// STEP1 の races を読み込んでプルダウンに表示
async function loadRaces() {
    const snap = await db.collection("races").get();
    const select = document.getElementById("race-select");

    snap.forEach(doc => {
        const opt = document.createElement("option");
        opt.value = doc.id;
        opt.textContent = doc.data().name + "（" + doc.data().date + "）";
        select.appendChild(opt);
    });
}

// 枠番・馬番を生成
document.getElementById("load-btn").addEventListener("click", async () => {
    const raceId = document.getElementById("race-select").value;
    const raceDoc = await db.collection("races").doc(raceId).get();
    //const num = raceDoc.data().numHorses;
    const num = Number(raceDoc.data().numHorses);

    let html = "<table border='1'><tr><th>枠</th><th>馬</th><th>馬名</th></tr>";
///////////////////////////////////////////////////////////////////

    let wakuList = generateWaku(num);

    // --- 馬番を割り振る前に枠順でソート ---
    wakuList.sort((a, b) => a.waku - b.waku);

    let horseNumber = 1;
    for (const block of wakuList) {
        for (let i = 0; i < block.count; i++) {
            html += `
                <tr>
                    <td>${block.waku}</td>
                    <td>${horseNumber}</td>
                    <td><input type="text" id="horse-${horseNumber}" placeholder="馬名"></td>

                    ${nickname === "うま王" ? `
                        <td><input type="number" id="finish-${horseNumber}" min="1" max="18" placeholder="着"></td>
                        <td><input type="number" id="pop-${horseNumber}" min="1" max="18" placeholder="人"></td>
                    ` : ""}
                </tr>
            `;

            horseNumber++;
        }
    }

    // --- 馬番を割り振る ---
    //let horseNumber = 1;
    //for (const block of wakuList) {
    //    for (let i = 0; i < block.count; i++) {
    //        html += `
    //            <tr>
    //                <td>${block.waku}</td>
    //                <td>${horseNumber}</td>
    //                <td><input type="text" id="horse-${horseNumber}"></td>
    //            </tr>
    //        `;
    //        horseNumber++;
    //    }
    //}

    html += "</table>";

    document.getElementById("entry-area").innerHTML = html;
    document.getElementById("save-btn").style.display = "inline-block";
});



// Firestore に保存
document.getElementById("save-btn").addEventListener("click", async () => {
    const raceId = document.getElementById("race-select").value;
    const raceDoc = await db.collection("races").doc(raceId).get();
    const num = Number(raceDoc.data().numHorses);

    let wakuList = generateWaku(num);
    wakuList.sort((a, b) => a.waku - b.waku);

    console.log("wakuList:", wakuList);  // ← これ追加

    let horseNumber = 1;

    for (const block of wakuList) {
        for (let i = 0; i < block.count; i++) {

            const name = document.getElementById(`horse-${horseNumber}`).value;
            if (!name) {
                alert("馬名が未入力です");
                return;
            }

            /// ★ 修正④：ここ！！
            const finish = document.getElementById(`finish-${horseNumber}`)?.value || null;
            const pop = document.getElementById(`pop-${horseNumber}`)?.value || null;

            await db.collection("races")
                .doc(raceId)
               .collection("horses")
               .doc(String(horseNumber))
               .set({
                    name: name,
                    number: horseNumber,
                    waku: block.waku,
                    finish: finish,
                    popularity: pop
                });

            horseNumber++;
        }
    }

    document.getElementById("msg").textContent = "保存しました！";
});

<script>
    const raceIdFromServer = "{{ raceId }}";  // None か 実際のID
    const nickname = "{{ nickname }}";        // うま王判定用
</script>


// 初期ロード
//loadRaces();
if (!raceIdFromServer) {
    loadRaces();   // 新規登録モード
} else {
    // 既存レース編集モード → race-select を固定
    const select = document.getElementById("race-select");
    const opt = document.createElement("option");
    opt.value = raceIdFromServer;
    opt.textContent = raceIdFromServer;
    select.appendChild(opt);
}


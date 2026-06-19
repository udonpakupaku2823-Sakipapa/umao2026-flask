// Firestore 初期化（あなたの設定に合わせて書き換え）
const db = firebase.firestore();

document.getElementById("save-btn").addEventListener("click", async () => {

    const name = document.getElementById("race-name").value;
    const grade = document.getElementById("race-grade").value;
    const date = document.getElementById("race-date").value;
    const num = Number(document.getElementById("race-num").value);

    if (!name || !date || !num) {
        document.getElementById("msg").textContent = "未入力があります。";
        return;
    }

    // Firestore に保存
    // raceId を「日付＋レース名」で固定 
    const raceId = date.replace(/-/g, "") + "_" + name;

    await db.collection("races").doc(raceId).set({
        name: name,
        grade: grade,
        date: date,
        numHorses: num
    });
   
    document.getElementById("msg").textContent =
        `登録しました！ レースID：${raceId}`;

    // ★ 登録後にSTEP2へ自動遷移    
    window.location.href = "/admin/entry";    
});

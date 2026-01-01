pxt.editor.initFieldEditorAsync = function (field, options) {
    const width = options.width || 8;
    const height = options.height || 8;

    const container = document.getElementById("led-editor");
    container.innerHTML = "";

    let grid = [];

    // ドラッグ塗りつぶし用フラグ
    let isDrawing = false;
    let drawValue = "1";

    // -------------------------
    // 8×8 グリッド生成
    // -------------------------
    for (let y = 0; y < height; y++) {
        grid[y] = [];
        for (let x = 0; x < width; x++) {
            const cell = document.createElement("div");
            cell.style.width = "18px";
            cell.style.height = "18px";
            cell.style.border = "1px solid #888";
            cell.style.margin = "1px";
            cell.style.background = "white";
            cell.dataset.value = "0";

            // クリック開始（反転 & ドラッグ開始）
            cell.onmousedown = () => {
                isDrawing = true;
                drawValue = cell.dataset.value === "0" ? "1" : "0";
                cell.dataset.value = drawValue;
                cell.style.background = drawValue === "1" ? "black" : "white";
                updateField();
            };

            // ドラッグ中に通過したセルを塗る
            cell.onmouseover = () => {
                if (isDrawing) {
                    cell.dataset.value = drawValue;
                    cell.style.background = drawValue === "1" ? "black" : "white";
                    updateField();
                }
            };

            // セル上でマウスを離したとき
            cell.onmouseup = () => {
                isDrawing = false;
            };

            container.appendChild(cell);
            grid[y][x] = cell;
        }
    }

    // -------------------------
    // GUI → Bxxxxxxxx 変換
    // -------------------------
    function updateField() {
        let rows = [];
        for (let y = 0; y < height; y++) {
            let bits = "";
            for (let x = 0; x < width; x++) {
                bits += grid[y][x].dataset.value;
            }
            rows.push("B" + bits);
        }
        field.setValue(rows.join(","));
    }

    // -------------------------
    // 画面外でマウスを離したときの対策
    // -------------------------
    document.onmouseup = () => {
        isDrawing = false;
    };

    return Promise.resolve();
};

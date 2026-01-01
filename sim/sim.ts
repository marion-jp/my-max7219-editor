namespace pxsim.max7219editor {
    // 8x8 LED Display simulator
    // シミュレータ側の 8×8 LED 表示
    export function showPattern(pattern: string) {
        const rows = pattern.split(",");
        const matrix = document.getElementById("sim-matrix");
        if (!matrix) return;

        matrix.innerHTML = "";

        for (let y = 0; y < 8; y++) {
            const bits = rows[y].replace("B", "");
            for (let x = 0; x < 8; x++) {
                const led = document.createElement("div");
                led.style.background = bits[x] === "1" ? "#ff0000" : "#222";
                matrix.appendChild(led);
            }
        }
    }
}

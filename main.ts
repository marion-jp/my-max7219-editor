//% color=#ff6600 icon="\uf00a"
//    機能： 8x8 LEDの描画
//    カテゴリアイコン:  テーブル模様 [fontawesome v4からアイコン選択]、橙色
namespace max7219editor {
    //% block="LED editor simple %name with pattern %pattern"
    //% name.defl="simplePattern"
    //% pattern.fieldEditor="ledmatrix_simple"
    //% pattern.fieldOptions.width=8
    //% pattern.fieldOptions.height=8
    export function definePattern(name: string, pattern: string): string {
        // pattern は "B00001000,B00011000,..." の形式で渡される
        console.log(name + " = " + pattern)
        // シミュレータに送る
        pxsim.max7219editor.showPattern(pattern);
        return pattern;
    }
}

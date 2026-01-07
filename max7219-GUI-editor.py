import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os

GRID_SIZE = 8
CELL_SIZE = 30  # 初期サイズ

ON_COLOR = "black"
OFF_COLOR = "white"

LIB_FILE = "led_library.json"


class LedMatrixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MAX7219 8x8 LED GUI")

        # 8x8 の状態
        self.grid_state = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]

        # Undo スタック
        self.stack = []

        # ライブラリ（名前＋byte-array-string）
        self.library = []
        self.library_window = None

        # ドラッグ状態
        self.dragging = False
        self.drag_value = None

        # --- メイン 8x8 Canvas ---
        self.canvas = tk.Canvas(root, bg="gray90")
        self.canvas.grid(row=1, column=1, padx=10, pady=10)

        self.rects = [[None]*GRID_SIZE for _ in range(GRID_SIZE)]
        self.redraw_canvas()

        # マウスイベント
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)

        # --- 上下左右ボタン ---
        tk.Button(root, text="▲", width=4, command=lambda: self.push_and(self.shift_up)).grid(row=0, column=1)
        tk.Button(root, text="▼", width=4, command=lambda: self.push_and(self.shift_down)).grid(row=2, column=1)
        tk.Button(root, text="◀", width=4, command=lambda: self.push_and(self.shift_left)).grid(row=1, column=0)
        tk.Button(root, text="▶", width=4, command=lambda: self.push_and(self.shift_right)).grid(row=1, column=2)

        # --- 右側 UI ---
        right = tk.Frame(root)
        right.grid(row=1, column=3, padx=10, pady=10, sticky="n")

        tk.Label(right, text="byte-array string").grid(row=0, column=0, sticky="w")
        self.text = tk.Text(right, width=40, height=4)
        self.text.grid(row=1, column=0, columnspan=3, pady=5)

        tk.Button(right, text="書き出し", command=self.export_to_text).grid(row=2, column=0, sticky="w")
        tk.Button(right, text="読み込み", command=self.load_from_text).grid(row=2, column=1, sticky="e")
        tk.Button(right, text="Undo", width=10, command=self.undo).grid(row=2, column=2, padx=5)

        # --- サイズ変更 ---
        size_frame = tk.Frame(right)
        size_frame.grid(row=3, column=0, columnspan=3, pady=10)
        tk.Button(size_frame, text="大", width=6, command=lambda: self.change_size(40)).grid(row=0, column=0, padx=5)
        tk.Button(size_frame, text="中", width=6, command=lambda: self.change_size(30)).grid(row=0, column=1, padx=5)
        tk.Button(size_frame, text="小", width=6, command=lambda: self.change_size(20)).grid(row=0, column=2, padx=5)

        # --- 操作ボタン ---
        ops = tk.Frame(right)
        ops.grid(row=4, column=0, columnspan=3, pady=10)

        tk.Button(ops, text="白黒反転", width=10, command=lambda: self.push_and(self.invert)).grid(row=0, column=0, padx=5, pady=2)
        tk.Button(ops, text="時計回転", width=10, command=lambda: self.push_and(self.rotate_90)).grid(row=0, column=1, padx=5, pady=2)
        tk.Button(ops, text="左右反転", width=10, command=lambda: self.push_and(self.mirror_lr)).grid(row=1, column=0, padx=5, pady=2)
        tk.Button(ops, text="上下反転", width=10, command=lambda: self.push_and(self.flip_ud)).grid(row=1, column=1, padx=5, pady=2)
        tk.Button(ops, text="リセット", width=10, command=lambda: self.push_and(self.reset_grid)).grid(row=2, column=0, padx=5, pady=2)
        tk.Button(ops, text="全セット", width=10, command=lambda: self.push_and(self.set_all)).grid(row=2, column=1, padx=5, pady=2)

        # --- ライブラリ一覧ボタン ---
        tk.Button(right, text="ライブラリ一覧", width=12, command=self.toggle_library_window).grid(row=5, column=0, pady=5, sticky="w")

        # --- Stack Viewer（別ウィンドウ） ---
        self.stack_window = tk.Toplevel(self.root)
        self.stack_window.title("Stack Viewer")
        self.stack_window.geometry("200x400")

        self.stack_canvas = tk.Canvas(self.stack_window, width=180, height=380)
        self.stack_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(self.stack_window, orient="vertical", command=self.stack_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.stack_canvas.configure(yscrollcommand=scrollbar.set)

        self.stack_inner = tk.Frame(self.stack_canvas)
        self.stack_canvas.create_window((0, 0), window=self.stack_inner, anchor="nw")
        self.stack_inner.bind("<Configure>", lambda e: self.stack_canvas.configure(scrollregion=self.stack_canvas.bbox("all")))

        # --- ライブラリ読み込み ---
        self.load_library()

        # --- 終了処理 ---
        self.root.protocol("WM_DELETE_WINDOW", self.close_all)
        
    # ============================================================
    # push / pop / undo
    # ============================================================

    def push(self):
        """現在のテキストボックス内容をスタックに保存し、StackViewer にミニ8x8を追加"""
        txt = self.text.get("1.0", tk.END).strip()
        self.stack.append(txt)

        import copy
        snapshot = copy.deepcopy(self.grid_state)

        # StackViewer にミニ8x8を追加（クリックでライブラリ保存可能）
        self.draw_mini_matrix(
            parent=self.stack_inner,
            state=snapshot,
            clickable_for_library=True
        )

    def pop(self):
        """スタックから取り出し、StackViewer の最後のミニ8x8を削除"""
        if not self.stack:
            return None

        children = self.stack_inner.winfo_children()
        if children:
            children[-1].destroy()

        return self.stack.pop()

    def undo(self):
        """pop → テキスト更新 → 読み込み"""
        data = self.pop()
        if data is None:
            messagebox.showinfo("Undo", "これ以上戻れません")
            return

        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, data)
        self.load_from_text()

    def push_and(self, func):
        """状態変更前に push → 処理 → 書き出し"""
        self.export_to_text()
        self.push()
        func()
        self.export_to_text()

    # ============================================================
    # ミニ 8×8 描画（StackViewer / Library 共通）
    # ============================================================

    def draw_mini_matrix(self, parent, state, clickable_for_library=False, lib_index=None):
        """ミニ8x8を描画し、必要ならクリックイベントを付与"""
        size = 12  # ライブラリ用指定サイズ
        canvas = tk.Canvas(parent, width=GRID_SIZE*size, height=GRID_SIZE*size, bg="white")
        canvas.pack(pady=3)

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x1 = c * size
                y1 = r * size
                x2 = x1 + size
                y2 = y1 + size
                color = "black" if state[r][c] else "white"
                canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="gray")

        # StackViewer → ライブラリ保存
        if clickable_for_library:
            canvas.bind("<Button-1>", lambda e, s=state: self.save_to_library_from_state(s))

        # ライブラリ一覧 → 項目クリック
        if lib_index is not None:
            canvas.bind("<Button-1>", lambda e, idx=lib_index: self.library_item_clicked(idx))

        return canvas

    # ============================================================
    # ライブラリ保存処理
    # ============================================================

    def grid_to_bytes_string(self, state):
        """8x8 の状態を byte-array-string に変換"""
        bytes_list = []
        for r in range(GRID_SIZE):
            bits = 0
            for c in range(GRID_SIZE):
                if state[r][c] == 1:
                    bits |= (1 << (7 - c))
            bytes_list.append("B" + format(bits, "08b"))
        return ",".join(bytes_list)

    def bytes_string_to_grid(self, bytes_str):
        """byte-array-string を 8x8 の状態に変換"""
        parts = [p.strip() for p in bytes_str.split(",") if p.strip()]
        if len(parts) != GRID_SIZE:
            raise ValueError("8 個の Bxxxxxxxx が必要です")

        new_state = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
        for r, item in enumerate(parts):
            if not item.startswith("B") or len(item) != 9:
                raise ValueError(f"形式エラー: {item}")
            bits_str = item[1:]
            for c in range(GRID_SIZE):
                new_state[r][c] = int(bits_str[c])
        return new_state

    def save_to_library_from_state(self, state):
        """StackViewer のミニ8x8クリック → 名前を付けてライブラリ保存"""
        name = simpledialog.askstring("ライブラリ保存", "このパターンに名前を付けてください：", parent=self.root)
        if not name:
            return

        bytes_str = self.grid_to_bytes_string(state)
        self.library.append({"name": name, "bytes": bytes_str})
        self.save_library()

        # ライブラリ一覧が開いていれば更新
        if self.library_window is not None and tk.Toplevel.winfo_exists(self.library_window):
            self.refresh_library_window()

    # ============================================================
    # ライブラリ一覧ウィンドウ（600x800）
    # ============================================================

    def toggle_library_window(self):
        """ライブラリ一覧ウィンドウの表示/非表示トグル"""
        if self.library_window is not None and tk.Toplevel.winfo_exists(self.library_window):
            self.library_window.destroy()
            self.library_window = None
        else:
            self.open_library_window()

    def open_library_window(self):
        """ライブラリ一覧ウィンドウを開く"""
        self.library_window = tk.Toplevel(self.root)
        self.library_window.title("ライブラリ一覧")
        self.library_window.geometry("600x800")

        # --- 上部操作パネル ---
        top = tk.Frame(self.library_window)
        top.pack(fill="x", pady=5)

        # 検索欄
        self.search_var = tk.StringVar()
        tk.Entry(top, textvariable=self.search_var, width=30).pack(side="left", padx=5)

        tk.Button(top, text="検索", command=self.apply_search_filter).pack(side="left")
        tk.Button(top, text="クリア", command=self.clear_search_filter).pack(side="left", padx=5)

        # ソートボタン
        tk.Button(top, text="名前順", command=self.sort_library_asc).pack(side="left", padx=10)
        tk.Button(top, text="逆順", command=self.sort_library_desc).pack(side="left")

        # --- スクロール領域 ---
        frame = tk.Frame(self.library_window)
        frame.pack(fill="both", expand=True)

        self.lib_canvas = tk.Canvas(frame)
        self.lib_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.lib_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.lib_canvas.configure(yscrollcommand=scrollbar.set)

        self.lib_inner = tk.Frame(self.lib_canvas)
        self.lib_canvas.create_window((0, 0), window=self.lib_inner, anchor="nw")
        self.lib_inner.bind("<Configure>", lambda e: self.lib_canvas.configure(scrollregion=self.lib_canvas.bbox("all")))

        self.refresh_library_window()
        
    # ============================================================
    # ライブラリ一覧の更新（検索・ソート対応）
    # ============================================================

    def refresh_library_window(self):
        """ライブラリ一覧ウィンドウを最新状態に更新（検索・ソート対応）"""
        if self.library_window is None:
            return

        # 一旦クリア
        for w in self.lib_inner.winfo_children():
            w.destroy()

        keyword = self.search_var.get().strip()

        for idx, item in enumerate(self.library):
            # --- 絞り込み検索 ---
            if keyword and keyword not in item["name"]:
                continue

            row = tk.Frame(self.lib_inner, bd=1, relief="solid", padx=5, pady=5)
            row.pack(fill="x", pady=3)

            # --- 名前ラベル ---
            name_label = tk.Label(row, text=item["name"], anchor="w")
            name_label.pack(side="left", padx=5)
            name_label.bind("<Button-1>", lambda e, i=idx: self.library_item_clicked(i))

            # --- ミニ8x8 ---
            try:
                state = self.bytes_string_to_grid(item["bytes"])
            except Exception:
                state = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]

            mini = self.draw_mini_matrix(
                parent=row,
                state=state,
                clickable_for_library=False,
                lib_index=idx
            )
            mini.pack(side="right")

    # ============================================================
    # ソート機能
    # ============================================================

    def sort_library_asc(self):
        """名前順（昇順）"""
        self.library.sort(key=lambda x: x["name"])
        self.save_library()
        self.refresh_library_window()

    def sort_library_desc(self):
        """名前順（降順）"""
        self.library.sort(key=lambda x: x["name"], reverse=True)
        self.save_library()
        self.refresh_library_window()

    # ============================================================
    # 検索機能
    # ============================================================

    def apply_search_filter(self):
        """検索欄の文字列で絞り込み"""
        self.refresh_library_window()

    def clear_search_filter(self):
        """検索欄クリア"""
        self.search_var.set("")
        self.refresh_library_window()

    # ============================================================
    # ライブラリ項目クリック → ダイアログ
    # ============================================================

    def library_item_clicked(self, index):
        """ライブラリ項目（名前 or ミニ8x8）クリック時のダイアログ"""
        item = self.library[index]

        dlg = tk.Toplevel(self.root)
        dlg.title(f"ライブラリ: {item['name']}")
        dlg.grab_set()

        tk.Label(dlg, text=f"名前: {item['name']}").pack(pady=5)

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=10)

        # --- 取り込み ---
        def do_import():
            self.text.delete("1.0", tk.END)
            self.text.insert(tk.END, item["bytes"])
            self.load_from_text()
            dlg.destroy()

        # --- 名前変更 ---
        def do_rename():
            new_name = simpledialog.askstring(
                "名前変更",
                "新しい名前を入力:",
                initialvalue=item["name"]
            )
            if new_name:
                self.library[index]["name"] = new_name
                self.save_library()
                if self.library_window:
                    self.refresh_library_window()
            dlg.destroy()

        # --- 削除 ---
        def do_delete():
            if messagebox.askyesno("削除確認", f"「{item['name']}」を削除しますか？"):
                del self.library[index]
                self.save_library()
                if self.library_window:
                    self.refresh_library_window()
            dlg.destroy()

        tk.Button(btn_frame, text="取り込み", width=12, command=do_import).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="名前変更", width=12, command=do_rename).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="ライブラリから削除", width=16, command=do_delete).grid(row=0, column=2, padx=5)

    # ============================================================
    # ライブラリ JSON 保存・読み込み
    # ============================================================

    def save_library(self):
        """ライブラリを JSON に保存"""
        try:
            with open(LIB_FILE, "w", encoding="utf-8") as f:
                json.dump(self.library, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("保存エラー", f"ライブラリ保存に失敗しました: {e}")

    def load_library(self):
        """JSON からライブラリ読み込み"""
        if not os.path.exists(LIB_FILE):
            return
        try:
            with open(LIB_FILE, "r", encoding="utf-8") as f:
                self.library = json.load(f)
        except Exception:
            self.library = []

    # ============================================================
    # Canvas 再描画
    # ============================================================

    def redraw_canvas(self):
        self.canvas.delete("all")
        self.rects = [[None]*GRID_SIZE for _ in range(GRID_SIZE)]

        self.canvas.config(
            width=GRID_SIZE * CELL_SIZE,
            height=GRID_SIZE * CELL_SIZE
        )

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x1 = c * CELL_SIZE
                y1 = r * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=ON_COLOR if self.grid_state[r][c] else OFF_COLOR,
                    outline="black"
                )
                self.rects[r][c] = rect

    # ============================================================
    # サイズ変更
    # ============================================================

    def change_size(self, new_size):
        global CELL_SIZE
        CELL_SIZE = new_size
        self.redraw_canvas()

    # ============================================================
    # マウスドラッグ処理
    # ============================================================

    def get_cell_from_event(self, event):
        c = event.x // CELL_SIZE
        r = event.y // CELL_SIZE
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            return r, c
        return None, None

    def start_drag(self, event):
        r, c = self.get_cell_from_event(event)
        if r is None:
            return
        self.dragging = True
        self.grid_state[r][c] = 1 - self.grid_state[r][c]
        self.drag_value = self.grid_state[r][c]
        self.update_cell(r, c)

    def drag(self, event):
        if not self.dragging:
            return
        r, c = self.get_cell_from_event(event)
        if r is None:
            return
        if self.grid_state[r][c] != self.drag_value:
            self.grid_state[r][c] = self.drag_value
            self.update_cell(r, c)

    def end_drag(self, event):
        self.dragging = False
        self.drag_value = None

    # ============================================================
    # GUI 更新
    # ============================================================

    def update_cell(self, r, c):
        color = ON_COLOR if self.grid_state[r][c] else OFF_COLOR
        self.canvas.itemconfig(self.rects[r][c], fill=color)

    def refresh_all(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self.update_cell(r, c)

    # ============================================================
    # 書き出し（行単位・左ビット先）
    # ============================================================

    def export_to_text(self):
        bytes_list = []

        for r in range(GRID_SIZE):
            bits = 0
            for c in range(GRID_SIZE):
                if self.grid_state[r][c] == 1:
                    bits |= (1 << (7 - c))
            bytes_list.append("B" + format(bits, "08b"))

        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, ",".join(bytes_list))

    # ============================================================
    # 読み込み（行単位・左ビット先）
    # ============================================================

    def load_from_text(self):
        raw = self.text.get("1.0", tk.END).strip()
        if not raw:
            return

        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if len(parts) != GRID_SIZE:
            messagebox.showerror("形式エラー", "8 個の Bxxxxxxxx が必要です")
            return

        new_state = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]

        try:
            for r, item in enumerate(parts):
                if not item.startswith("B") or len(item) != 9:
                    raise ValueError(f"形式エラー: {item}")

                bits_str = item[1:]

                for c in range(GRID_SIZE):
                    new_state[r][c] = int(bits_str[c])

        except Exception as e:
            messagebox.showerror("形式エラー", str(e))
            return

        self.grid_state = new_state
        self.refresh_all()

    # ============================================================
    # 操作ボタン（反転・回転・反転・シフト）
    # ============================================================

    def invert(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self.grid_state[r][c] = 1 - self.grid_state[r][c]
        self.refresh_all()

    def rotate_90(self):
        new_state = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                new_state[c][GRID_SIZE - 1 - r] = self.grid_state[r][c]
        self.grid_state = new_state
        self.refresh_all()

    def mirror_lr(self):
        new_state = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                new_state[r][GRID_SIZE - 1 - c] = self.grid_state[r][c]
        self.grid_state = new_state
        self.refresh_all()

    def flip_ud(self):
        new_state = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
        for r in range(GRID_SIZE):
            new_state[GRID_SIZE - 1 - r] = self.grid_state[r][:]
        self.grid_state = new_state
        self.refresh_all()

    # ============================================================
    # 方向シフト
    # ============================================================

    def shift_up(self):
        self.grid_state = self.grid_state[1:] + [self.grid_state[0]]
        self.refresh_all()

    def shift_down(self):
        self.grid_state = [self.grid_state[-1]] + self.grid_state[:-1]
        self.refresh_all()

    def shift_left(self):
        new_state = []
        for row in self.grid_state:
            new_state.append(row[1:] + [row[0]])
        self.grid_state = new_state
        self.refresh_all()

    def shift_right(self):
        new_state = []
        for row in self.grid_state:
            new_state.append([row[-1]] + row[:-1])
        self.grid_state = new_state
        self.refresh_all()

    # ============================================================
    # リセット / 全セット
    # ============================================================

    def reset_grid(self):
        self.grid_state = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
        self.refresh_all()
        self.text.delete("1.0", tk.END)

    def set_all(self):
        self.grid_state = [[1]*GRID_SIZE for _ in range(GRID_SIZE)]
        self.refresh_all()

    # ============================================================
    # 終了処理
    # ============================================================

    def close_all(self):
        """終了時に JSON 保存し、子ウィンドウも閉じる"""
        self.save_library()

        if self.stack_window is not None and tk.Toplevel.winfo_exists(self.stack_window):
            self.stack_window.destroy()

        if self.library_window is not None and tk.Toplevel.winfo_exists(self.library_window):
            self.library_window.destroy()

        self.root.destroy()


# ============================================================
# main
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = LedMatrixGUI(root)
    root.mainloop()


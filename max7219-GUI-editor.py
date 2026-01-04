import tkinter as tk
from tkinter import messagebox

GRID_SIZE = 8
CELL_SIZE = 30  # 初期サイズ

ON_COLOR = "black"
OFF_COLOR = "white"


class LedMatrixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MAX7219 8x8 LED GUI")

        self.grid_state = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]

        # ドラッグ状態
        self.dragging = False
        self.drag_value = None

        # --- Canvas 作成 ---
        self.canvas = tk.Canvas(root, bg="gray90")
        self.canvas.grid(row=1, column=1, padx=10, pady=10)

        # セル矩形ID
        self.rects = [[None]*GRID_SIZE for _ in range(GRID_SIZE)]

        # 初回描画
        self.redraw_canvas()

        # Canvas イベント
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)

        # --- 上下左右の三角形ボタン配置 ---
        tk.Button(root, text="▲", width=4, command=self.shift_up).grid(row=0, column=1)
        tk.Button(root, text="▼", width=4, command=self.shift_down).grid(row=2, column=1)
        tk.Button(root, text="◀", width=4, command=self.shift_left).grid(row=1, column=0)
        tk.Button(root, text="▶", width=4, command=self.shift_right).grid(row=1, column=2)

        # --- 右側 UI ---
        right = tk.Frame(root)
        right.grid(row=1, column=3, padx=10, pady=10, sticky="n")

        tk.Label(right, text="byte-array string").grid(row=0, column=0, sticky="w")
        self.text = tk.Text(right, width=40, height=4)
        self.text.grid(row=1, column=0, columnspan=3, pady=5)

        tk.Button(right, text="書き出し", command=self.export_to_text).grid(row=2, column=0, sticky="w")
        tk.Button(right, text="読み込み", command=self.load_from_text).grid(row=2, column=1, sticky="e")

        # --- サイズ変更ボタン ---
        size_frame = tk.Frame(right)
        size_frame.grid(row=3, column=0, columnspan=3, pady=10)

        tk.Button(size_frame, text="大", width=6, command=lambda: self.change_size(40)).grid(row=0, column=0, padx=5)
        tk.Button(size_frame, text="中", width=6, command=lambda: self.change_size(30)).grid(row=0, column=1, padx=5)
        tk.Button(size_frame, text="小", width=6, command=lambda: self.change_size(20)).grid(row=0, column=2, padx=5)

        # --- 操作ボタン ---
        ops = tk.Frame(right)
        ops.grid(row=4, column=0, columnspan=3, pady=10)

        tk.Button(ops, text="白黒反転", width=10, command=self.invert).grid(row=0, column=0, padx=5, pady=2)
        tk.Button(ops, text="時計回転", width=10, command=self.rotate_90).grid(row=0, column=1, padx=5, pady=2)
        tk.Button(ops, text="左右反転", width=10, command=self.mirror_lr).grid(row=1, column=0, padx=5, pady=2)
        tk.Button(ops, text="上下反転", width=10, command=self.flip_ud).grid(row=1, column=1, padx=5, pady=2)

        tk.Button(ops, text="リセット", width=10, command=self.reset_grid).grid(row=2, column=0, padx=5, pady=2)
        tk.Button(ops, text="全セット", width=10, command=self.set_all).grid(row=2, column=1, padx=5, pady=2)

    # ============================================================
    # Canvas 再描画（サイズ変更時にも使用）
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
    # 操作ボタン
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
    # ★★★ 方向シフト機能 ★★★
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


if __name__ == "__main__":
    root = tk.Tk()
    app = LedMatrixGUI(root)
    root.mainloop()

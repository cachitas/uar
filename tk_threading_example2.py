import tkinter as tk
from tkinter import ttk
import threading
import time


# TODO Redo using a Queue

class App(tk.Tk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calc_progress = tk.IntVar(0)
        self._init_ui()

    def _init_ui(self):

        self.title('Threading Example')
        self.minsize(300, 100)

        self.btn = tk.Button(text='Calculate', command=self.calc)
        self.btn.pack(fill='both', expand=True)

        self.btn = tk.Button(text='Thread Calculate', command=self.calc_thread)
        self.btn.pack(fill='both', expand=True)

        self.pb = ttk.Progressbar(variable=self.calc_progress, maximum=69)
        self.pb.pack(fill='x')


    def calc(self):
        for i in range(70):
            self.calc_progress.set(i)
            time.sleep(.1)

    def calc_thread(self):
        t = threading.Thread(target=self.calc)
        t.start()


if __name__ == '__main__':
    app = App()
    app.mainloop()

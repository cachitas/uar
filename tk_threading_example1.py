import tkinter as tk
from tkinter import ttk
import threading
import time


class App(tk.Tk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calc_progress = tk.IntVar(0)
        self._init_ui()

    def _init_ui(self):

        self.title('Threading Example')
        self.minsize(300, 100)

        self.btn1 = tk.Button(text='Calculate', command=self.calc)
        self.btn1.pack(fill='both', expand=True)

        self.btn2 = tk.Button(text='Calculate in another Thread',
                              command=self.calc_thread)
        self.btn2.pack(fill='both', expand=True)

        self.pb = ttk.Progressbar(variable=self.calc_progress, maximum=69)
        self.pb.pack(fill='x')

    def calc(self):
        for i in range(70):
            self.calc_progress.set(i)
            time.sleep(.05)

    def calc_thread(self):
        self.btn2.config(state='disabled')
        t = threading.Thread(target=self.calc)
        t.start()
        self.check_worker_thread(t, self.btn2)

    def check_worker_thread(self, thread, widget=None):
        if thread.is_alive():
            print('Thread is alive!')
            self.after(1000, self.check_worker_thread, thread, widget)
        else:
            print('Thread died :(')
            if widget is not None:
                widget.config(state='normal')


if __name__ == '__main__':
    app = App()
    app.mainloop()

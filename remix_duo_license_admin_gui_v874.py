"""RemiX Duo V8.74 ADMIN-ONLY License Manager (Tune-style issuance UI).

Never package this file, remix_duo_issuer_admin_v874.py, or any .dpapi
signer file inside the customer installer. No signing key enters client UI.
"""
from __future__ import annotations

import re
from pathlib import Path
from tkinter import Tk, StringVar, Text, END, messagebox, filedialog, ttk

from remix_duo_issuer_admin_v874 import admin_store, initialize, issue, key_path


class DuoLicenseManager(Tk):
    def __init__(self):
        super().__init__()
        self.title("RemiX Duo - Quan ly License / Key Active (Admin)")
        self.geometry("760x485")
        self.minsize(720, 450)
        self.configure(bg="#0B1520")
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#0B1520")
        self.style.configure("TLabel", background="#0B1520", foreground="#E2F2F9",
                             font=("Segoe UI", 10))
        self.style.configure("TButton", padding=7, font=("Segoe UI", 10))
        self.style.configure("TEntry", padding=5)
        self.machine_ids = StringVar()
        self.lic_id = StringVar()
        self.customer = StringVar()
        self.days = StringVar(value="365")
        self.output = StringVar(value=str(
            Path.home() / "Documents" / "RemiX Duo Licenses" / "license.lic"
        ))
        self.last_token = ""
        self._layout()

    def _layout(self):
        container = ttk.Frame(self, padding=18)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="RemiX Duo - Ed25519 License Signer",
                  font=("Segoe UI", 16, "bold")).grid(
                      row=0,column=0,columnspan=3,sticky="w",pady=(0,13))
        desc = ("Ky key LIC1 | Edition: DUO_PRO | Windows | "
                "Days = 0: Vinh vien | 1-2 Machine ID")
        ttk.Label(container,text=desc).grid(
            row=1,column=0,columnspan=3,sticky="w",pady=(0,12))
        entries=[
            ("Machine ID (1-2 ma):",self.machine_ids),
            ("License ID / Ma don:",self.lic_id),
            ("Ten khach hang:",self.customer),
            ("So ngay (0 = vinh vien):",self.days),
            ("Xuat file .lic:",self.output)
        ]
        for i,(text,var) in enumerate(entries,start=2):
            ttk.Label(container,text=text).grid(row=i,column=0,sticky="w",pady=5)
            ttk.Entry(container,textvariable=var,width=64).grid(
                row=i,column=1,sticky="ew",padx=(8,8),pady=5)
            if i == 6:
                ttk.Button(container,text="Chon...",command=self.choose_file).grid(
                    row=i,column=2,sticky="ew")
        container.grid_columnconfigure(1,weight=1)
        toolbar=ttk.Frame(container)
        toolbar.grid(row=7,column=0,columnspan=3,sticky="ew",pady=(12,5))
        ttk.Button(toolbar,text="Ky & Xuat key",command=self.sign).pack(side="left")
        ttk.Button(toolbar,text="Copy Key",command=self.copy).pack(
            side="left",padx=10)
        ttk.Button(toolbar,text="Public Key",command=self.show_public).pack(
            side="left")
        ttk.Label(container,text="Trang thai / License da cap:").grid(
            row=8,column=0,columnspan=3,sticky="w",pady=(10,5))
        self.preview=Text(container,height=4,wrap="word",bg="#102638",fg="#DDF7FD",
                          font=("Consolas",10),relief="flat")
        self.preview.grid(row=9,column=0,columnspan=3,sticky="nsew")
        container.grid_rowconfigure(9,weight=1)
        self._set_status("San sang. Private key duoc bao ve boi Windows DPAPI.")

    def _set_status(self,message):
        self.preview.delete("1.0",END)
        self.preview.insert("1.0",message)

    def choose_file(self):
        filename=filedialog.asksaveasfilename(
            title="Xuat RemiX Duo license",
            defaultextension=".lic",
            filetypes=[("RemiX License","*.lic")]
        )
        if filename:
            self.output.set(filename)

    def sign(self):
        try:
            if not key_path().is_file():
                raise RuntimeError("Chua co signer. Chay 'init' tren may Admin truoc.")
            machines=[m for m in re.split(r"[,;\s]+",self.machine_ids.get()) if m]
            days=int(self.days.get())
            output=Path(self.output.get())
            created=issue(machine_ids=machines,
                         lic_id=self.lic_id.get(),
                         name=self.customer.get(),
                         days=days,output_path=output)
            self.last_token=Path(created).read_text("utf-8").strip()
            self._set_status(
                f"Da ky: {Path(created).name}\n"
                f"Ma don: {self.lic_id.get().strip()}\n"
                f"Thoi han: {'Vinh vien' if days == 0 else str(days)+' ngay'}"
            )
            messagebox.showinfo("Thanh cong",f"Da xuat license:\n{created}")
        except Exception as exc:
            self._set_status("Khong the ky: "+str(exc))
            messagebox.showerror("Loi cap key",str(exc))

    def copy(self):
        if not self.last_token:
            messagebox.showwarning("Chua co key","Hay ky va xuat license truoc.")
            return
        self.clipboard_clear()
        self.clipboard_append(self.last_token)
        self.update()
        messagebox.showinfo("Copy","Da copy LIC1 token.")

    def show_public(self):
        try:
            from remix_duo_issuer_admin_v874 import _public_b64,_load_key
            public=_public_b64(_load_key())
            self._set_status("Public verification key (khong phai private):\n"+public)
        except Exception as exc:
            self._set_status("Khong doc duoc public key: "+str(exc))


if __name__ == "__main__":
    DuoLicenseManager().mainloop()

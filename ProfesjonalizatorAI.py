import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json, os, threading, urllib.request, urllib.error

APP_DIR=os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"),"ProfesjonalizatorAI")
CFG=os.path.join(APP_DIR,"config.json")
URL="https://api.openai.com/v1/responses"

MODES={
"Synonimy profesjonalne":"Zmieniaj głównie zwykłe, potoczne lub zbyt proste słowa i krótkie frazy na profesjonalne synonimy. Nie przepisuj całego tekstu bez potrzeby. Dobieraj zamianę wyłącznie na podstawie kontekstu. Zachowaj sens, fakty, liczby, nazwy i kolejność informacji. Jeśli słowo już brzmi profesjonalnie albo zmiana byłaby sztuczna, zostaw je bez zmian.",
"Przeredaguj całość":"Szerzej przeredaguj cały tekst na profesjonalny, klarowny i naturalny język polski. Zachowaj sens, fakty, liczby, nazwy i intencję. Nie dodawaj informacji."
}
TONES={"Profesjonalny":"profesjonalny i naturalny","Formalny":"formalny i oficjalny","Biznesowy":"biznesowy, konkretny i rzeczowy","Urzędowy":"urzędowy i precyzyjny","Naturalny":"naturalny i elegancki"}
LEVELS={"Delikatna":"tylko najbardziej oczywiste zamiany","Standardowa":"najważniejsze zamiany z zachowaniem naturalności","Mocna":"aktywnie szukaj profesjonalniejszych odpowiedników, ale nie twórz sztucznego języka"}

SYSTEM="""Jesteś profesjonalnym redaktorem języka polskiego. W trybie SYNONIMY skupiasz się na kontekstowej zamianie słów i krótkich fraz. Nie stosuj mechanicznych podmian. Przykładowo: zrobić→wykonać/zrealizować, dostać→otrzymać, powiedzieć→poinformować, sprawdzić→zweryfikować, wysłać→przesłać, pokazać→zaprezentować, problem→kwestia/zagadnienie, potrzebować→wymagać. Uwaga: 'zrobić zdjęcie' nie musi stać się 'zrealizować zdjęcie'. Odpowiadaj po polsku i tylko JSON zgodny ze schematem."""

SCHEMA={"type":"object","properties":{"rewritten_text":{"type":"string"},"changes":{"type":"array","items":{"type":"object","properties":{"original":{"type":"string"},"replacement":{"type":"string"},"reason":{"type":"string"}},"required":["original","replacement","reason"],"additionalProperties":False}}},"required":["rewritten_text","changes"],"additionalProperties":False}

def cfg_load():
    try:
        with open(CFG,encoding="utf-8") as f:return json.load(f)
    except:return {}
def cfg_save(x):
    os.makedirs(APP_DIR,exist_ok=True)
    with open(CFG,"w",encoding="utf-8") as f:json.dump(x,f,ensure_ascii=False,indent=2)

def api(text,mode,tone,level,model,key):
    payload={"model":model,"instructions":SYSTEM,"input":f"Tryb: {mode}\nTon: {tone}\nIntensywność: {level}\n\n{MODES[mode]}\n\nTEKST:\n{text}","text":{"format":{"type":"json_schema","name":"professional_edit","strict":True,"schema":SCHEMA}}}
    req=urllib.request.Request(URL,data=json.dumps(payload,ensure_ascii=False).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=120) as r:d=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw=e.read().decode(errors="replace")
        try: msg=json.loads(raw).get("error",{}).get("message",raw)
        except: msg=raw
        raise RuntimeError(f"OpenAI HTTP {e.code}: {msg}")
    except urllib.error.URLError as e: raise RuntimeError("Brak połączenia z OpenAI. Sprawdź internet.")
    out=d.get("output_text","")
    if not out:
        for it in d.get("output",[]):
            for c in it.get("content",[]):
                if c.get("type")=="output_text": out+=c.get("text","")
    if not out.strip(): raise RuntimeError("API zwróciło pustą odpowiedź.")
    try:r=json.loads(out)
    except: r={"rewritten_text":out,"changes":[]}
    return r.get("rewritten_text","").strip(), r.get("changes",[])

ctk.set_default_color_theme("blue")
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg=cfg_load(); self.changes=[]
        ctk.set_appearance_mode(self.cfg.get("theme","dark"))
        self.title("Profesjonalizator AI")
        self.geometry("1180x780"); self.minsize(900,640)
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)
        self.sidebar(); self.main()
        self.bind("<Control-Return>",lambda e:self.start())

    def sidebar(self):
        s=ctk.CTkFrame(self,width=235,corner_radius=0,fg_color=("#ECEFF5","#151821")); s.grid(row=0,column=0,sticky="nsew"); s.grid_propagate(False)
        ctk.CTkLabel(s,text="✦",width=44,height=44,corner_radius=12,fg_color="#6D5DFB",text_color="white",font=ctk.CTkFont(size=25,weight="bold")).pack(anchor="w",padx=22,pady=(28,8))
        ctk.CTkLabel(s,text="Profesjonalizator",font=ctk.CTkFont(size=17,weight="bold")).pack(anchor="w",padx=22)
        ctk.CTkLabel(s,text="AI • profesjonalny język",text_color=("#737A89","#8C93A3")).pack(anchor="w",padx=22,pady=(0,26))
        ctk.CTkLabel(s,text="TRYB",text_color=("#737A89","#8C93A3"),font=ctk.CTkFont(size=10,weight="bold")).pack(anchor="w",padx=22,pady=(5,7))
        self.mode=tk.StringVar(value="Synonimy profesjonalne")
        self.b1=ctk.CTkButton(s,text="✦  Synonimy profesjonalne",anchor="w",height=44,command=lambda:self.set_mode(self.b1,"Synonimy profesjonalne"))
        self.b1.pack(fill="x",padx=15,pady=3)
        self.b2=ctk.CTkButton(s,text="↻  Przeredaguj całość",anchor="w",height=44,fg_color="transparent",command=lambda:self.set_mode(self.b2,"Przeredaguj całość"))
        self.b2.pack(fill="x",padx=15,pady=3)
        ctk.CTkLabel(s,text="USTAWIENIA",text_color=("#737A89","#8C93A3"),font=ctk.CTkFont(size=10,weight="bold")).pack(anchor="w",padx=22,pady=(28,7))
        ctk.CTkButton(s,text="⚙  Klucz i model API",anchor="w",height=42,fg_color="transparent",command=self.settings).pack(fill="x",padx=15,pady=3)
        ctk.CTkButton(s,text="☾  Zmień motyw",anchor="w",height=42,fg_color="transparent",command=self.theme).pack(fill="x",padx=15,pady=3)
        ctk.CTkLabel(s,text="Ctrl + Enter  •  przetwarzanie\nKlucz API jest zapisany lokalnie.",justify="left",text_color=("#7A8190","#767D8E"),font=ctk.CTkFont(size=10)).pack(side="bottom",anchor="w",padx=22,pady=22)

    def main(self):
        m=ctk.CTkFrame(self,fg_color="transparent"); m.grid(row=0,column=1,sticky="nsew",padx=26,pady=25); m.grid_columnconfigure(0,weight=1); m.grid_rowconfigure(2,weight=1)
        h=ctk.CTkFrame(m,fg_color="transparent"); h.grid(row=0,column=0,sticky="ew"); h.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(h,text="Profesjonalizuj tekst",font=ctk.CTkFont(size=28,weight="bold")).grid(row=0,column=0,sticky="w")
        self.sub=ctk.CTkLabel(h,text="Zmieniaj zwykłe słowa na trafniejsze, profesjonalne synonimy.",text_color=("#6B7280","#969DAC")); self.sub.grid(row=1,column=0,sticky="w")
        ctk.CTkButton(h,text="Przykład",width=90,command=self.example).grid(row=0,column=1,rowspan=2,padx=4)
        ctk.CTkButton(h,text="Wyczyść",width=90,fg_color="transparent",border_width=1,command=self.clear).grid(row=0,column=2,rowspan=2,padx=4)
        c=ctk.CTkFrame(m,corner_radius=15,fg_color=("#FFFFFF","#181B24"),border_width=1,border_color=("#E4E7EE","#292D39")); c.grid(row=1,column=0,sticky="ew",pady=(20,14))
        self.badge=ctk.CTkLabel(c,text="SYNONIMY PROFESJONALNE",width=195,height=30,corner_radius=15,fg_color=("#EDEBFF","#29263D"),text_color=("#5C50D8","#B7B0FF"),font=ctk.CTkFont(size=10,weight="bold")); self.badge.pack(side="left",padx=12,pady=12)
        self.tone=ctk.CTkComboBox(c,values=list(TONES),width=150,height=35); self.tone.set("Profesjonalny"); self.tone.pack(side="left",padx=7)
        self.level=ctk.CTkComboBox(c,values=list(LEVELS),width=145,height=35); self.level.set("Standardowa"); self.level.pack(side="left",padx=7)
        self.go=ctk.CTkButton(c,text="✨  ZMIEŃ TEKST",width=160,height=37,font=ctk.CTkFont(size=12,weight="bold"),command=self.start); self.go.pack(side="right",padx=12)
        ed=ctk.CTkFrame(m,fg_color="transparent"); ed.grid(row=2,column=0,sticky="nsew"); ed.grid_columnconfigure((0,1),weight=1); ed.grid_rowconfigure(0,weight=1)
        self.original=self.editor(ed,"ORYGINAŁ",0); self.result=self.editor(ed,"WYNIK",1,state="disabled")
        f=ctk.CTkFrame(m,fg_color="transparent"); f.grid(row=3,column=0,sticky="ew",pady=(12,0)); f.grid_columnconfigure(1,weight=1)
        self.status=ctk.CTkLabel(f,text="Gotowy",text_color=("#6B7280","#8E95A5")); self.status.grid(row=0,column=0,sticky="w")
        self.ch=ctk.CTkButton(f,text="Zobacz zamiany · 0",width=160,fg_color="transparent",border_width=1,command=self.show_changes); self.ch.grid(row=0,column=1,sticky="e",padx=6)
        ctk.CTkButton(f,text="Kopiuj wynik",width=120,command=self.copy).grid(row=0,column=2)

    def editor(self,p,label,col,state="normal"):
        x=ctk.CTkFrame(p,corner_radius=15,fg_color=("#FFFFFF","#181B24"),border_width=1,border_color=("#E4E7EE","#292D39")); x.grid(row=0,column=col,sticky="nsew",padx=(0,7) if col==0 else (7,0)); x.grid_rowconfigure(1,weight=1); x.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(x,text=label,text_color=("#737A89","#9399A8"),font=ctk.CTkFont(size=10,weight="bold")).grid(row=0,column=0,sticky="w",padx=14,pady=12)
        t=ctk.CTkTextbox(x,corner_radius=10,fg_color=("#F9FAFC","#11141B"),font=ctk.CTkFont(size=13),wrap="word",state=state); t.grid(row=1,column=0,sticky="nsew",padx=12,pady=(0,12)); return t

    def set_mode(self,btn,mode):
        self.mode.set(mode); self.b1.configure(fg_color=("#FFFFFF","#252936") if mode==self.b1.cget("text").split("  ",1)[-1] else "transparent"); self.b2.configure(fg_color=("#FFFFFF","#252936") if mode=="Przeredaguj całość" else "transparent")
        if mode=="Synonimy profesjonalne": self.badge.configure(text="SYNONIMY PROFESJONALNE"); self.sub.configure(text="Zmieniaj zwykłe słowa na trafniejsze, profesjonalne synonimy.")
        else: self.badge.configure(text="PRZEREDAGUJ CAŁOŚĆ"); self.sub.configure(text="Przepisz tekst szerzej, zachowując sens i profesjonalny ton.")

    def example(self):
        self.original.delete("1.0","end"); self.original.insert("1.0","Chciałem zapytać, czy możecie szybko przesłać mi informacje dotyczące projektu. Musimy sprawdzić, co jeszcze trzeba zrobić."); self.set_mode(self.b1,"Synonimy profesjonalne")
    def clear(self):
        self.original.delete("1.0","end"); self.result.configure(state="normal"); self.result.delete("1.0","end"); self.result.configure(state="disabled"); self.changes=[]; self.ch.configure(text="Zobacz zamiany · 0"); self.status.configure(text="Wyczyszczono")
    def copy(self):
        s=self.result.get("1.0","end-1c").strip()
        if s: self.clipboard_clear(); self.clipboard_append(s); self.status.configure(text="Skopiowano ✓")
    def start(self):
        txt=self.original.get("1.0","end-1c").strip()
        if not txt: messagebox.showinfo("Brak tekstu","Wklej tekst do pola „Oryginał”."); return
        key=self.cfg.get("api_key","").strip()
        if not key: self.settings(); return
        self.go.configure(state="disabled",text="⏳  PRACUJĘ…"); self.status.configure(text="Analizuję kontekst i dobieram synonimy…")
        model=self.cfg.get("model","gpt-5.6-luna")
        threading.Thread(target=self.worker,args=(txt,self.mode.get(),self.tone.get(),self.level.get(),model,key),daemon=True).start()
    def worker(self,*args):
        try:r=api(*args); self.after(0,lambda:self.done(*r))
        except Exception as e:self.after(0,lambda:self.fail(str(e)))
    def done(self,out,changes):
        self.result.configure(state="normal"); self.result.delete("1.0","end"); self.result.insert("1.0",out); self.result.configure(state="disabled")
        self.changes=changes; self.ch.configure(text=f"Zobacz zamiany · {len(changes)}"); self.status.configure(text=f"Gotowe ✓  •  {len(changes)} zmian"); self.go.configure(state="normal",text="✨  ZMIEŃ TEKST")
    def fail(self,e):
        self.go.configure(state="normal",text="✨  ZMIEŃ TEKST"); self.status.configure(text="Błąd"); messagebox.showerror("Błąd",e)
    def show_changes(self):
        w=ctk.CTkToplevel(self); w.title("Zastosowane zamiany"); w.geometry("680x520")
        ctk.CTkLabel(w,text=f"Zastosowane zamiany · {len(self.changes)}",font=ctk.CTkFont(size=21,weight="bold")).pack(anchor="w",padx=22,pady=(20,5))
        s=ctk.CTkScrollableFrame(w); s.pack(fill="both",expand=True,padx=22,pady=12)
        if not self.changes: ctk.CTkLabel(s,text="Brak wykrytych zmian słownikowych.").pack(pady=40)
        for x in self.changes:
            c=ctk.CTkFrame(s,corner_radius=11); c.pack(fill="x",pady=5); ctk.CTkLabel(c,text=f'{x.get("original","")}  →  {x.get("replacement","")}',font=ctk.CTkFont(size=12,weight="bold")).pack(anchor="w",padx=13,pady=(10,2)); ctk.CTkLabel(c,text=x.get("reason",""),text_color=("#6D7482","#9399A8")).pack(anchor="w",padx=13,pady=(0,10))
    def settings(self):
        w=ctk.CTkToplevel(self); w.title("Ustawienia"); w.geometry("600x430"); w.resizable(False,False)
        ctk.CTkLabel(w,text="Ustawienia API",font=ctk.CTkFont(size=23,weight="bold")).pack(anchor="w",padx=25,pady=(25,12))
        ctk.CTkLabel(w,text="Klucz OpenAI API").pack(anchor="w",padx=25); key=ctk.CTkEntry(w,show="•",height=40); key.pack(fill="x",padx=25,pady=7); key.insert(0,self.cfg.get("api_key",""))
        ctk.CTkLabel(w,text="Model API").pack(anchor="w",padx=25,pady=(10,0)); model=ctk.CTkEntry(w,height=40); model.pack(fill="x",padx=25,pady=7); model.insert(0,self.cfg.get("model","gpt-5.6-luna"))
        ctk.CTkLabel(w,text="Domyślnie używany jest gpt-5.6-luna. Możesz wpisać inny model dostępny na swoim koncie API.",wraplength=540,text_color=("#737A89","#9299A8"),justify="left").pack(anchor="w",padx=25,pady=5)
        def save():
            self.cfg["api_key"]=key.get().strip(); self.cfg["model"]=model.get().strip() or "gpt-5.6-luna"; cfg_save(self.cfg); self.status.configure(text="Ustawienia zapisane ✓"); w.destroy()
        ctk.CTkButton(w,text="Zapisz",width=120,command=save).pack(anchor="e",padx=25,pady=18)
    def theme(self):
        x="light" if ctk.get_appearance_mode()=="Dark" else "dark"; ctk.set_appearance_mode(x); self.cfg["theme"]=x; cfg_save(self.cfg)

if __name__=="__main__": App().mainloop()

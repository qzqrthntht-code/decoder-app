from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import QLabel
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import threading
import os
import base64
import bz2
import gzip
import lzma
import zlib
import re
import html
from pathlib import Path
from urllib.parse import unquote

LIMIT = 20 * 1024 * 1024
MAX_DEPTH = 30

def decode_layers(data):
    results = []
    seen = {data}
    queue = [(data, 0)]

    while queue:
        current, depth = queue.pop(0)

        if depth >= MAX_DEPTH or len(current) > LIMIT:
            continue

        candidates = []

        # Compression formats
        for func in (zlib.decompress, gzip.decompress, bz2.decompress, lzma.decompress):
            try:
                candidates.append(func(current))
            except Exception:
                pass

        # Raw DEFLATE
        try:
            candidates.append(zlib.decompress(current, -zlib.MAX_WBITS))
        except Exception:
            pass

        # Text encodings
        try:
            text = current.decode("ascii").strip()
            compact = re.sub(r"\s+", "", text)

            if len(compact) >= 8:
                if re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", compact):
                    try:
                        candidates.append(base64.b64decode(compact, validate=True))
                    except Exception:
                        pass

                if re.fullmatch(r"[A-Za-z0-9_-]*={0,2}", compact):
                    try:
                        candidates.append(base64.urlsafe_b64decode(compact + "=" * (-len(compact) % 4)))
                    except Exception:
                        pass

                if re.fullmatch(r"[A-Z2-7]+=*", compact.upper()):
                    try:
                        candidates.append(base64.b32decode(compact.upper() + "=" * (-len(compact) % 8)))
                    except Exception:
                        pass

                if re.fullmatch(r"[0-9a-fA-F]+", compact) and len(compact) % 2 == 0:
                    try:
                        candidates.append(bytes.fromhex(compact))
                    except Exception:
                        pass

                try:
                    candidates.append(base64.b85decode(compact))
                except Exception:
                    pass

                try:
                    candidates.append(base64.a85decode(compact))
                except Exception:
                    pass

                unescaped = unquote(text).encode()
                if unescaped != current:
                    candidates.append(unescaped)

                unhtml = html.unescape(text).encode()
                if unhtml != current:
                    candidates.append(unhtml)

        except UnicodeDecodeError:
            pass

        reversed_data = current[::-1]
        if reversed_data != current:
            candidates.append(reversed_data)

        for item in candidates:
            if not item or item == current or len(item) > LIMIT:
                continue
            if item in seen:
                continue

            seen.add(item)
            results.append(item)
            queue.append((item, depth + 1))

    return results

class DecoderApp(App):
    def build(self):
        self.title = "Multi-Layer Decoder Tool"
        self.root_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # عرض واجهة البداية
        self.show_home_screen()
        return self.root_layout

    def show_home_screen(self):
        self.root_layout.clear_widgets()
        
        # شعار وتصميم البداية
        title_label = QLabel(
            text="[ ANONYMOUS DECODER ]\n🛡️",
            font_size=24,
            halign='center',
            markup=True
        )
        
        name_label = QLabel(
            text="صنع بواسطة: ابن وسام\n[color=00ff00]@ald_753[/color]",
            font_size=18,
            halign='center',
            markup=True
        )
        
        start_btn = Button(
            text="بدء التحليل وفك التشفير",
            background_color=(0.1, 0.7, 0.3, 1),
            font_size=18,
            size_hint=(1, 0.3)
        )
        start_btn.bind(on_press=self.show_main_screen)
        
        self.root_layout.add_widget(title_label)
        self.root_layout.add_widget(name_label)
        self.root_layout.add_widget(start_btn)

    def show_main_screen(self, instance):
        self.root_layout.clear_widgets()
        
        # معلومات الخوارزميات المدعومة
        info_label = QLabel(
            text="الخوارزميات المدعومة:\nBase64, Base32, Base85, Hex, URL, Zlib, Gzip, BZ2, LZMA",
            font_size=14,
            size_hint=(1, 0.2)
        )
        
        # حقل إدخال مسار الملف
        self.path_input = TextInput(
            text="/sdcard/Download/encrypted_file.txt",
            hint_text="أدخل مسار الملف هنا...",
            size_hint=(1, 0.2),
            multiline=False
        )
        
        # زر التنفيذ
        decode_btn = Button(
            text="فك طبقات الملف",
            background_color=(0.2, 0.5, 0.8, 1),
            size_hint=(1, 0.2)
        )
        decode_btn.bind(on_press=self.start_decoding_process)
        
        # شاشة عرض النتائج
        self.result_box = TextInput(
            text="النتائج ستظهر هنا...",
            readonly=True,
            size_hint=(1, 0.4)
        )
        
        self.root_layout.add_widget(info_label)
        self.root_layout.add_widget(self.path_input)
        self.root_layout.add_widget(decode_btn)
        self.root_layout.add_widget(self.result_box)

    def start_decoding_process(self, instance):
        file_path = self.path_input.text.strip().strip('"')
        self.result_box.text = "[*] جاري فحص وفك طبقات الملف..."
        
        # تشغيل العملية في خلفية (Thread) حتى لا يتوقف التطبيق
        threading.Thread(target=self.run_decoder_logic, args=(file_path,)).start()

    def run_decoder_logic(self, source):
        try:
            path = Path(source).expanduser()
            if not path.is_file():
                Clock.schedule_once(lambda dt: setattr(self.result_box, 'text', "الملف غير موجود."))
                return

            if path.stat().st_size > LIMIT:
                Clock.schedule_once(lambda dt: setattr(self.result_box, 'text', "حجم الملف أكبر من 20 MB."))
                return

            data = path.read_bytes()
            layers = decode_layers(data)

            output = Path.env_path if hasattr(Path, 'env_path') else Path.home() / "storage" / "downloads" / "نتائج_فك_الطبقات"
            output.mkdir(parents=True, exist_ok=True)

            (output / "layer_00_original.bin").write_bytes(data)

            for number, layer in enumerate(layers, 1):
                (output / f"layer_{number:03}.bin").write_bytes(layer)

            res_text = f"تم بنجاح!\nعدد الطبقات المكتشفة: {len(layers)}\nالنتائج محفوظة في:\n{output}"
            Clock.schedule_once(lambda dt: setattr(self.result_box, 'text', res_text))
            
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.result_box, 'text', f"حدث خطأ: {str(e)}"))

if __name__ == "__main__":
    DecoderApp().run()

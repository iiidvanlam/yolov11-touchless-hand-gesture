import threading
from typing import List


class SignLanguageTranslator:
    """
    Bộ ghép chữ cái Ngôn ngữ Ký hiệu (ASL A-Z) thành từ/câu hoàn chỉnh,
    hỗ trợ gợi ý từ nhanh (Autocomplete) và phát giọng nói (Text-to-Speech) đa luồng.
    """

    COMMON_WORDS_DICT: List[str] = [
        "HELLO", "HI", "HELP", "HOME", "HAPPY", "HOW", "HAVE",
        "THANK", "THANKS", "TIME", "TODAY", "TOMORROW",
        "YES", "YOU", "YOUR",
        "NO", "NAME", "NEED", "NICE",
        "PLEASE", "PLAY", "PAUSE",
        "GOOD", "GREAT", "GO",
        "WATER", "WORK", "WELCOME", "WORLD",
        "SORRY", "STOP", "START", "STUDY",
        "LOVE", "LEARN", "LIKE",
        "FRIEND", "FAMILY", "FOOD", "FINE",
        "VIETNAM", "AI", "YOLO", "PYTHON",
    ]

    def __init__(self):
        self.text_buffer: str = ""
        self._tts_lock = threading.Lock()

    def append_symbol(self, symbol: str) -> str:
        """
        Thêm một ký hiệu đã được xác nhận từ VotingBuffer vào chuỗi văn bản.
        Hỗ trợ các nhãn đặc biệt: SPACE, DEL, CLEAR, SPEAK.
        """
        sym = symbol.upper().strip()
        if not sym or sym == "NOTHING":
            return self.text_buffer

        if sym == "SPACE":
            if self.text_buffer and not self.text_buffer.endswith(" "):
                self.text_buffer += " "
        elif sym in ("DEL", "BACKSPACE"):
            if self.text_buffer:
                self.text_buffer = self.text_buffer[:-1]
        elif sym == "CLEAR":
            self.text_buffer = ""
        elif sym == "SPEAK":
            self.speak_async(self.text_buffer)
        elif len(sym) == 1 and sym.isalpha():
            self.text_buffer += sym

        return self.text_buffer

    def get_current_word_prefix(self) -> str:
        """Lấy từ cuối cùng đang được ghép dở dang."""
        if not self.text_buffer or self.text_buffer.endswith(" "):
            return ""
        parts = self.text_buffer.split(" ")
        return parts[-1].upper()

    def get_word_suggestions(self, max_results: int = 3) -> List[str]:
        """Gợi ý tối đa 3 từ thông dụng khớp với các chữ cái đầu người dùng vừa ký hiệu."""
        prefix = self.get_current_word_prefix()
        if not prefix:
            return ["HELLO", "THANK", "HELP"][:max_results]
        matches = [w for w in self.COMMON_WORDS_DICT if w.startswith(prefix) and w != prefix]
        return matches[:max_results]

    def apply_suggestion(self, chosen_word: str) -> str:
        """Thay thế từ đang ghép dở bằng từ gợi ý được chọn và thêm dấu cách."""
        if not self.text_buffer or self.text_buffer.endswith(" "):
            self.text_buffer += chosen_word.upper() + " "
            return self.text_buffer

        parts = self.text_buffer.split(" ")
        parts[-1] = chosen_word.upper()
        self.text_buffer = " ".join(parts) + " "
        return self.text_buffer

    def clear(self) -> None:
        self.text_buffer = ""

    def backspace(self) -> str:
        if self.text_buffer:
            self.text_buffer = self.text_buffer[:-1]
        return self.text_buffer

    def add_space(self) -> str:
        if self.text_buffer and not self.text_buffer.endswith(" "):
            self.text_buffer += " "
        return self.text_buffer

    def speak_async(self, text: str = "") -> None:
        """Phát âm thanh văn bản trên luồng riêng (không làm đứng hình Camera)."""
        target_text = (text or self.text_buffer).strip()
        if not target_text:
            return
        threading.Thread(target=self._speak_worker, args=(target_text,), daemon=True).start()

    def _speak_worker(self, text: str) -> None:
        with self._tts_lock:
            # Ưu tiên Windows SAPI.SpVoice có sẵn trong pywin32 trên Windows
            try:
                import pythoncom
                import win32com.client

                pythoncom.CoInitialize()
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(text)
                pythoncom.CoUninitialize()
                return
            except Exception:
                pass

            # Fallback sang pyttsx3 nếu có
            try:
                import pyttsx3

                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass


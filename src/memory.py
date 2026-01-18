from typing import Dict
from pathlib import Path
import json

class Memory:
    def __init__(self, path: str = "./memory.json"):
        self.path = Path(path)
        if not self.path.exists():
            self._write({"msg_history": [], "profile": []})
    

    def _read(self) -> Dict:
        return json.loads(self.path.read_text(encoding="utf-8"))


    def _write(self, data: Dict):
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


    def get_history(self, n: int = 3):
        mem_file = self._read()
        return mem_file["msg_history"][-n:]


    def update_history(self, user: str, assistant: str):
        mem_file = self._read()
        mem_file["msg_history"].append({"user": user, "assistant": assistant})
        self._write(mem_file)


    def get_from_profile(self, query: str, n: int = 3):
        mem_file = self._read()
        query = query.lower()
        scored_records = []

        for record in mem_file["profile_notes"]:
            score = 0
            if query in record.get("title", "").lower():
                score += 3
            if query in record.get("content", "").lower():
                score += 2
            if score > 0:
                scored_records.append((score, record))
        scored_records.sort(key=lambda x: -x[0])

        return [record for _, record in scored_records[:n]]


    def add_to_profile(self, title: str, content: str):
        mem_file = self._read()
        mem_file["profile_notes"].append({"title": title, "content": content})
        self._write(mem_file)

      
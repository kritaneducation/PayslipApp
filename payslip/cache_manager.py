import os
import hashlib
import pickle

class PDFCacheManager:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(self.cache_dir, "date_cache.pkl")
        self.date_cache = self.load_cache()

    def get_file_hash(self, file_path):
        try:
            file_stat = os.stat(file_path)
            key = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}"
            return hashlib.md5(key.encode()).hexdigest()
        except Exception:
            return hashlib.md5(file_path.encode()).hexdigest()

    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
        except Exception:
            pass
        return {}

    def save_cache(self):
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.date_cache, f)
        except Exception:
            pass

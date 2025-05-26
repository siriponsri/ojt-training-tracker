import pandas as pd
import pickle
import gzip
from sheets_connector import get_training_matrix, get_form_links, get_training_status

def save_data_as_pickle():
    data = {
        "matrix": get_training_matrix(),
        "links": get_form_links(),
        "status": get_training_status()
    }

    with gzip.open("data_cache.pkl.gz", "wb") as f:
        pickle.dump(data, f)

    print("✅ บันทึกข้อมูลลงไฟล์ data_cache.pkl.gz เรียบร้อยแล้ว")

if __name__ == "__main__":
    save_data_as_pickle()

"""
One-time script: import docs/data.json into Firestore.
Run: python backend/import_to_firestore.py path/to/serviceAccountKey.json
"""
import json
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/import_to_firestore.py path/to/serviceAccountKey.json")
        sys.exit(1)

    sa_path = sys.argv[1]
    if not os.path.exists(sa_path):
        print(f"File not found: {sa_path}")
        sys.exit(1)

    import firebase_admin
    from firebase_admin import credentials, firestore

    cred = credentials.Certificate(sa_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    data_path = os.path.join(os.path.dirname(__file__), "../docs/data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db.collection("insight").document("data").set(data)
    print(f"Done! Uploaded {len(data['competitors'])} competitors to Firestore.")

if __name__ == "__main__":
    main()

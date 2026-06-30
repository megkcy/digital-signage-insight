"""
Import docs/data.json into Firestore.
Usage:
  python backend/import_to_firestore.py              # uses FIREBASE_SERVICE_ACCOUNT env var
  python backend/import_to_firestore.py key.json     # uses a service account file
"""
import json
import os
import sys
import tempfile


def main():
    import firebase_admin
    from firebase_admin import credentials, firestore

    # Resolve service account: env var takes priority, then CLI arg
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if sa_json:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(sa_json)
            sa_path = f.name
    elif len(sys.argv) >= 2:
        sa_path = sys.argv[1]
        if not os.path.exists(sa_path):
            print(f"File not found: {sa_path}")
            sys.exit(1)
    else:
        print("Set FIREBASE_SERVICE_ACCOUNT env var or pass path/to/serviceAccountKey.json")
        sys.exit(1)

    cred = credentials.Certificate(sa_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    data_path = os.path.join(os.path.dirname(__file__), "../docs/data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db.collection("insight").document("data").set(data)
    print(f"Done! Uploaded {len(data.get('competitors', []))} competitors to Firestore.")


if __name__ == "__main__":
    main()

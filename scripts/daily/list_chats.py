# Lists your iMessage chats so you can grab the GUIDs for the two group chats.
# Reads ~/Library/Messages/chat.db (read-only). Requires the running terminal to
# have Full Disk Access (System Settings > Privacy & Security > Full Disk Access).
#
# Copy the `guid` of each group into scripts/daily/config.json -> chat_ids.

import os
import sqlite3
import sys

DB = os.path.expanduser("~/Library/Messages/chat.db")


def main():
    if not os.path.exists(DB):
        print("chat.db not found — is Messages set up?")
        return 1
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    except sqlite3.OperationalError as e:
        print(f"Could not open chat.db ({e}).")
        print("Grant Full Disk Access to your terminal app and retry.")
        return 1

    # Group chats = more than one participant; show name + last activity.
    q = """
    SELECT c.guid,
           COALESCE(NULLIF(c.display_name,''), '(unnamed)') AS name,
           COUNT(chj.handle_id) AS participants
    FROM chat c
    LEFT JOIN chat_handle_join chj ON chj.chat_id = c.ROWID
    GROUP BY c.ROWID
    ORDER BY participants DESC, name;
    """
    rows = con.execute(q).fetchall()
    groups = [r for r in rows if r[2] >= 2]
    print(f"{len(groups)} group chat(s):\n")
    for guid, name, n in groups:
        print(f"  [{n:2d}p] {name}")
        print(f"        {guid}")
    if not groups:
        print("  (none found)")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

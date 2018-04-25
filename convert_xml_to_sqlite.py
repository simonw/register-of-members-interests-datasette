import hashlib
from xml.etree import ElementTree as ET
import os
import sqlite3


def init_db(filename):
    if os.path.exists(filename):
        return

    conn = sqlite3.connect(filename)
    conn.executescript(
        """
    CREATE TABLE people (
        id VARCHAR(50) NOT NULL,
        name TEXT,
        PRIMARY KEY (id)
    );
    CREATE TABLE members (
        id VARCHAR(50) NOT NULL,
        name TEXT,
        person_id TEXT,
        PRIMARY KEY (id),
        FOREIGN KEY ("person_id") REFERENCES [people](id)
    );
    CREATE TABLE categories (
        id VARCHAR(8) NOT NULL,
        type INTEGER,
        name TEXT,
        PRIMARY KEY (id)
    );
    CREATE TABLE items (
        hash VARCHAR(40) NOT NULL,
        item TEXT,
        category_id TEXT,
        date TEXT,
        member_id TEXT,
        person_id TEXT,
        sort_order INTEGER,
        record_id TEXT,
        PRIMARY KEY (hash),
        FOREIGN KEY ("category_id") REFERENCES [categories](id),
        FOREIGN KEY ("member_id") REFERENCES [members](id),
        FOREIGN KEY ("person_id") REFERENCES [people](id)
    );
    CREATE INDEX items_date ON items("date");
    CREATE INDEX items_category_id ON items("category_id");
    CREATE INDEX items_member_id ON items("member_id");
    CREATE INDEX items_person_id ON items("person_id");
    CREATE INDEX items_record_id ON items("record_id");
    """
    )
    conn.close()


def best_fts_version():
    "Discovers the most advanced supported SQLite FTS version"
    conn = sqlite3.connect(":memory:")
    for fts in ("FTS5", "FTS4", "FTS3"):
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE v USING {} (t TEXT);".format(
                    fts
                )
            )
            return fts

        except sqlite3.OperationalError:
            continue

    return None


def create_and_populate_fts(conn):
    create_sql = """
        CREATE VIRTUAL TABLE "items_fts"
        USING {fts_version} (item, person_name, content="items")
    """.format(
        fts_version=best_fts_version()
    )
    conn.executescript(create_sql)
    conn.executescript(
        """
        INSERT INTO "items_fts" (rowid, item, person_name)
        SELECT items.rowid, items.item, people.name
        FROM items LEFT JOIN people ON items.person_id = people.id
    """
    )


def insert_or_replace(conn, table, record):
    pairs = record.items()
    columns = [p[0] for p in pairs]
    params = [p[1] for p in pairs]
    sql = "INSERT OR REPLACE INTO {table} ({column_list}) VALUES ({value_list});".format(
        table=table,
        column_list=", ".join(columns),
        value_list=", ".join(["?" for p in params]),
    )
    conn.execute(sql, params)


def parse_and_load(filepath, db):
    s = open(filepath, "rb").read().decode("latin-1")
    root = ET.fromstring(s)
    for regmem_el in root.findall("regmem"):
        date = regmem_el.attrib["date"]
        person_id = regmem_el.attrib["personid"]
        insert_or_replace(
            db,
            "people",
            {
                "id": person_id,
                "name": regmem_el.attrib["membername"],
            },
        )
        member_id = regmem_el.attrib.get("memberid")
        if member_id:
            insert_or_replace(
                db,
                "members",
                {
                    "id": member_id,
                    "name": regmem_el.attrib["membername"],
                    "person_id": person_id,
                },
            )
        # <category type="8" name="Land and Property">
        for category_el in regmem_el.findall("category"):
            category_name = category_el.attrib["name"]
            category_id = hashlib.sha1(
                category_name.encode("utf8")
            ).hexdigest()[
                :8
            ]
            category = {
                "id": category_id,
                "type": int(category_el.attrib["type"]),
                "name": category_name,
            }
            insert_or_replace(db, "categories", category)
            # Sometimes there are <record> - sometimes not
            records_and_items = []
            record_els = category_el.findall("record")
            if record_els:
                for i, record_el in enumerate(record_els):
                    records_and_items.append(
                        (i, record_el.findall("item"))
                    )
            else:
                records_and_items.append(
                    (0, category_el.findall("item"))
                )
            for record, item_els in records_and_items:
                for sort_order, item_el in enumerate(
                    item_els
                ):
                    # For items, we derive an ID based on a hash of key content
                    hashme = "{date}:{member_id}:{person_id}:{category_id}:{record}:{item}".format(
                        date=date,
                        member_id=member_id,
                        person_id=person_id,
                        category_id=category_id,
                        record=record,
                        item=item_el.text,
                    )
                    hashid = hashlib.sha1(
                        hashme.encode("utf8")
                    ).hexdigest()
                    item = {
                        "hash": hashid,
                        "item": item_el.text,
                        "category_id": category_id,
                        "date": date,
                        "person_id": person_id,
                        "member_id": member_id or "",
                        "record_id": "{date}-{category_id}-{person_id}-{record}".format(
                            date=date,
                            category_id=category_id,
                            person_id=person_id.split("/")[
                                -1
                            ],
                            record=record,
                        ),
                        "sort_order": sort_order,
                    }
                    insert_or_replace(db, "items", item)


if __name__ == "__main__":
    import sys

    dbfile = sys.argv[-1]
    assert dbfile.endswith(".db")
    init_db(dbfile)
    db = sqlite3.connect(dbfile)
    for arg in sys.argv:
        if arg.endswith(".xml"):
            parse_and_load(arg, db)
            print(arg)
    create_and_populate_fts(db)
    db.close()

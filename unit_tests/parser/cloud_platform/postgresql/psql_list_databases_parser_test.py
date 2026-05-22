from keywords.cloud_platform.postgresql.object.psql_list_databases_output import PsqlListDatabasesOutput

psql_list_databases_output = """\
                                  List of databases
   Name    |  Owner   | Encoding | Locale Provider |   Collate   |    Ctype    | Locale | ICU Rules |   Access privileges
-----------+----------+----------+-----------------+-------------+-------------+--------+-----------+-----------------------
 barbican  | admin    | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           |
 fm        | admin    | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           |
 keystone  | admin    | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           |
 postgres  | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           |
 sysinv    | admin    | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           |
 template0 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | =c/postgres          +
           |          |          |                 |             |             |        |           | postgres=CTc/postgres
 template1 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | =c/postgres          +
           |          |          |                 |             |             |        |           | postgres=CTc/postgres
(7 rows)
"""


def test_psql_list_databases_parser():
    """Tests that the psql -l output parser correctly extracts databases."""
    output = PsqlListDatabasesOutput(psql_list_databases_output)
    databases = output.get_databases()

    assert len(databases) == 7
    assert databases[0].get_name() == "barbican"
    assert databases[0].get_owner() == "admin"
    assert databases[0].get_encoding() == "UTF8"

    assert databases[3].get_name() == "postgres"
    assert databases[3].get_owner() == "postgres"


def test_psql_list_databases_lookup():
    """Tests database lookup by name."""
    output = PsqlListDatabasesOutput(psql_list_databases_output)

    assert output.is_database_present("keystone")
    assert not output.is_database_present("nonexistent")

    db = output.get_database_by_name("sysinv")
    assert db.get_owner() == "admin"
    assert db.get_encoding() == "UTF8"

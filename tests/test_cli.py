from citations import cli


def test_options_before_or_after_the_command(tmp_path):
    parser = cli.build_parser()
    a = parser.parse_args(["--db", str(tmp_path / "a.sqlite"), "status"])
    b = parser.parse_args(["status", "--db", str(tmp_path / "a.sqlite")])
    assert a.db == b.db == tmp_path / "a.sqlite"
    assert parser.parse_args(["harvest", "scholexplorer", "crossref"]).sources == ["scholexplorer", "crossref"]
    assert not parser.parse_args(["harvest"]).sources   # empty = every source


def test_status_on_an_empty_store(tmp_path, capsys):
    assert cli.main(["--db", str(tmp_path / "s.sqlite"), "status"]) == 0


def test_publish_without_any_harvest_is_blocked(tmp_path):
    code = cli.main(["--db", str(tmp_path / "s.sqlite"), "--results", str(tmp_path / "Results"), "publish"])
    assert code == 2
    assert not (tmp_path / "Results" / "v4").exists()

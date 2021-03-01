import json
import tempfile
from pathlib import Path
from ada_tools.create_index import main
from click.testing import CliRunner


def test_cli():
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)/"tile_index.geojson"
        result = runner.invoke(main, ["--data", "tests/res", "--dest", dest])
        with open(dest, "r") as f:
            output = json.load(f)

        with open("tests/res/tile_index.geojson", "r") as f:
            expected = json.load(f)

    assert result.exit_code == 0
    assert output == expected

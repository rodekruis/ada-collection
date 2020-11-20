import json
import tempfile
from pathlib import Path
from ada_tools.create_index import main
from click.testing import CliRunner

expected_output = """
{
  "12.1814.1237": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1814.1238": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1814.1239": {
    "pre-event": [
      "10300100AA8C8400.tif",
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1814.1240": {
    "pre-event": [
      "10300100AA8C8400.tif",
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1814.1241": {
    "pre-event": [
      "10300100AA8C8400.tif",
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  },
  "12.1814.1242": {
    "pre-event": [
      "10300100AA8C8400.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  },
  "12.1815.1237": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1815.1238": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1815.1239": {
    "pre-event": [
      "10300100AA8C8400.tif",
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1815.1240": {
    "pre-event": [
      "10300100AA8C8400.tif",
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1815.1241": {
    "pre-event": [
      "10300100AA8C8400.tif",
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  },
  "12.1815.1242": {
    "pre-event": [
      "10300100AA8C8400.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  },
  "12.1816.1237": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1816.1238": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1816.1239": {
    "pre-event": [
      "10300100AA8C8400.tif",
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1816.1240": {
    "pre-event": [
      "10300100AA8C8400.tif",
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1816.1241": {
    "pre-event": [
      "10300100AA8C8400.tif",
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  },
  "12.1816.1242": {
    "pre-event": [
      "10300100AA8C8400.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  },
  "12.1817.1237": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1817.1238": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1817.1239": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1817.1240": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1817.1241": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  },
  "12.1818.1237": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1818.1238": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1818.1239": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1818.1240": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1818.1241": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  },
  "12.1819.1237": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1819.1238": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1819.1239": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1819.1240": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1819.1241": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  },
  "12.1820.1237": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1820.1238": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1820.1239": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1820.1240": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "104001006131E200.tif"
    ]
  },
  "12.1820.1241": {
    "pre-event": [
      "10300100AA94E000.tif"
    ],
    "post-event": [
      "105001001FA87E00.tif"
    ]
  }
}
"""

def test_cli():
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)/"tile_index.json"
        result = runner.invoke(main, ["--data", "tests/res", "--dest", dest])
        with open(dest) as f:
            output = json.load(f)

    assert result.exit_code == 0
    assert output == json.loads(expected_output)

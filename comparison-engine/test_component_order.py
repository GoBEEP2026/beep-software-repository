import importlib.util
import tempfile
from pathlib import Path


def load_comparison_engine():
    path = Path(__file__).with_name("compare.py")
    spec = importlib.util.spec_from_file_location("compare", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_hpxml(walls):
    wall_xml = "\n".join(
        f"""
        <Wall>
          <SystemIdentifier id="{wall_id}"/>
          <Area>{area}</Area>
          <Azimuth>{azimuth}</Azimuth>
          <Insulation>
            <NominalRValue>{r_value}</NominalRValue>
          </Insulation>
        </Wall>
        """
        for wall_id, area, azimuth, r_value in walls
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<HPXML xmlns="http://hpxmlonline.com/2019/10">
  <Building>
    <BuildingDetails>
      <Enclosure>
        <Walls>
          {wall_xml}
        </Walls>
      </Enclosure>
    </BuildingDetails>
  </Building>
</HPXML>
"""


def test_component_order():
    compare = load_comparison_engine()

    north = ("wall-north", 200, 0, 15)
    south = ("wall-south", 180, 180, 13)

    with tempfile.TemporaryDirectory() as directory:
        file_a = Path(directory) / "vendor_a.xml"
        file_b = Path(directory) / "vendor_b.xml"

        file_a.write_text(
            make_hpxml([north, south]), encoding="utf-8"
        )
        file_b.write_text(
            make_hpxml([south, north]), encoding="utf-8"
        )

        result = compare.compare_files(file_a, file_b)

        assert result["differences_found"] == 0, result
        print("PASS: Reordered walls produce zero differences.")

        changed_south = ("wall-south", 180, 180, 19)

        file_b.write_text(
            make_hpxml([changed_south, north]), encoding="utf-8"
        )

        result = compare.compare_files(file_a, file_b)

        assert result["differences_found"] == 1, result
        assert result["differences"][0]["field"] == (
            "walls[1].nominal_r_value"
        ), result

        print("PASS: Changed wall insulation detected.")


if __name__ == "__main__":
    test_component_order()

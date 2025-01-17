import json
from dataclasses import asdict
from pathlib import Path

import numpy
import pytest

from synnet.data.datasets import SynTreeChopper
from synnet.utils.datastructures import SyntheticTree


def syntree_from_json(file):
    return SyntheticTree.from_dict(dict(json.loads(Path(file).read_text())))


SYNTREE_FILES = [
    "tests/assets/syntree-small-simple-1.json",
    "tests/assets/syntree-small-simple-2.json",
    "tests/assets/syntree-small-simple-3.json",
]
REFERENCE_FILES = [
    "tests/assets/syntree-small-simple-1-chopped.json",
    "tests/assets/syntree-small-simple-2-chopped.json",
    "tests/assets/syntree-small-simple-3-chopped.json",
]

testdata = [*zip(SYNTREE_FILES, REFERENCE_FILES)]


@pytest.mark.parametrize("syntree_file,syntree_chopped_file", testdata)
def test_chop_syntrees(syntree_file, syntree_chopped_file):
    syntree = syntree_from_json(syntree_file)
    ref_chopped = json.loads(Path(syntree_chopped_file).read_text())

    assert isinstance(syntree, SyntheticTree)

    chunks = SynTreeChopper.chop(syntree)
    chunks_json = [asdict(chunk) for chunk in chunks]
    assert syntree_file == ref_chopped["meta"]["original_file"]

    numpy.testing.assert_equal(chunks_json, ref_chopped["data"])

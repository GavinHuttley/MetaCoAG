import pathlib
import pytest

from click.testing import CliRunner

from metacoag.cli import main


__author__ = "Vijini Mallawaarachchi"
__credits__ = ["Vijini Mallawaarachchi"]


DATADIR = pathlib.Path(__file__).parent / "data"

@pytest.fixture(scope="session")
def tmp_dir(tmpdir_factory):
    return tmpdir_factory.mktemp("tmp")


@pytest.fixture(autouse=True)
def workingdir(tmp_dir, monkeypatch):
    """set the working directory for all tests"""
    monkeypatch.chdir(tmp_dir)


@pytest.fixture(scope="session")
def runner():
    """exportrc works correctly."""
    return CliRunner()


def test_metacoag_spades_run(runner, tmp_dir):
    outpath = tmp_dir
    dir_name = DATADIR / "5G_metaspades"
    graph = dir_name / "assembly_graph_with_scaffolds.gfa"
    contigs = dir_name / "contigs.fasta"
    paths = dir_name / "contigs.paths"
    abundance = dir_name / "coverm_mean_coverage.tsv"
    args = f"--assembler spades --graph {graph} --contigs {contigs} --paths {paths} --abundance {abundance} --output {outpath}".split()
    r = runner.invoke(main, args, catch_exceptions=False)
    assert r.exit_code == 0, r.output


def test_metacoag_megahit_run(runner, tmp_dir):
    outpath = tmp_dir
    dir_name = DATADIR / "5G_MEGAHIT"
    graph = dir_name / "final.gfa"
    contigs = dir_name / "final.contigs.fa"
    abundance = dir_name / "abundance.tsv"
    args = f"--assembler megahit --graph {graph} --contigs {contigs} --abundance {abundance} --output {outpath}".split()
    r = runner.invoke(main, args, catch_exceptions=False)
    assert r.exit_code == 0, r.output
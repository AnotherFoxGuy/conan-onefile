import cProfile
import os
import pstats
import time
from pstats import SortKey
import pytest

from conan.test.assets.genconanfile import GenConanfile
from conan.test.utils.tools import TestClient


@pytest.mark.skip(reason="This is a performance test, skip for normal runs")
def test_large_graph():
    c = TestClient(cache_folder=os.path.join(os.path.dirname(__file__), "cache"))
    num_test = 40
    num_pkgs = 40

    """for i in range(num_test):
        conanfile = GenConanfile(f"test{i}", "0.1")
        if i > 0:
            conanfile.with_requires(f"test{i-1}/0.1")
        c.save({"conanfile.py": conanfile})
        c.run("create .")

    for i in range(num_pkgs):
        conanfile = GenConanfile(f"pkg{i}", "0.1").with_test_requires(f"test{num_test-1}/0.1")
        if i > 0:
            conanfile.with_requires(f"pkg{i-1}/0.1")
        c.save({"conanfile.py": conanfile})
        c.run("create .")

    """
    t = time.time()
    pr = cProfile.Profile()
    pr.enable()
    c.run(f"install --requires=pkg{num_pkgs - 1}/0.1")
    pr.disable()
    print(time.time()-t)

    sortby = SortKey.CUMULATIVE
    ps = pstats.Stats(pr).sort_stats(sortby)
    ps.print_stats()

    #graph = json.loads(c.stdout)
    #assert len(graph["graph"]["nodes"]) == 1 + num_pkgs + num_test * num_pkgs


@pytest.mark.skip(reason="This is a performance test, skip for normal runs")
def test_large_graph2():
    c = TestClient(cache_folder=os.path.join(os.path.dirname(__file__), "cache"))
    num_test = 20
    num_pkgs = 20
    branches = ["a", "b", "c"]

    c.save({"conanfile.py": GenConanfile("testbase", "0.1")})
    c.run("export .")
    for i in range(num_test):
        for branch in branches:
            conanfile = GenConanfile(f"test{branch}{i}", "0.1")
            if i > 0:
                conanfile.with_requires(f"test{branch}{i-1}/0.1", "testbase/0.1")
            else:
                conanfile.with_requires("testbase/0.1")
            c.save({"conanfile.py": conanfile})
            c.run("export .")

    for i in range(num_pkgs):
        conanfile = GenConanfile(f"pkg{i}", "0.1")
        for branch in branches:
            conanfile.with_test_requires(f"test{branch}{num_test-1}/0.1")
        if i > 0:
            conanfile.with_requires(f"pkg{i-1}/0.1")
        c.save({"conanfile.py": conanfile})
        c.run("export .")

    t = time.time()
    pr = cProfile.Profile()
    pr.enable()
    c.run(f"graph info --requires=pkg{num_pkgs - 1}/0.1")
    pr.disable()
    print(time.time()-t)

    sortby = SortKey.CUMULATIVE
    ps = pstats.Stats(pr).sort_stats(sortby)
    ps.print_stats()

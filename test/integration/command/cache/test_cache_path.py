import json
import os
import platform

import pytest

from conan.api.model import RecipeReference, PkgReference
from conan.test.assets.genconanfile import GenConanfile
from conan.test.utils.tools import TestClient


@pytest.fixture(scope="module")
def created_package():
    t = TestClient(light=True)
    t.save({"conanfile.py": GenConanfile()})
    t.run("create . --name foo --version 1.0")
    recipe_layout = t.exported_layout()
    pkg_layout = t.created_layout()
    return t, recipe_layout, pkg_layout


def test_cache_path(created_package):
    t, recipe_layout, pkg_layout = created_package

    # Basic recipe paths, without specifying revision

    recipe_revision = recipe_layout.reference.revision
    pref = pkg_layout.reference
    t.run("cache path foo/1.0")
    assert recipe_layout.export() == str(t.out).rstrip()
    t.run("cache path foo/1.0#latest")
    assert recipe_layout.export() == str(t.out).rstrip()
    t.run("cache path foo/1.0 --folder=export_source")
    assert recipe_layout.export_sources() == str(t.out).rstrip()
    t.run("cache path foo/1.0 --folder=source")
    assert recipe_layout.source() == str(t.out).rstrip()

    # Basic recipe paths, with revision
    t.run(f"cache path foo/1.0#{recipe_revision}")
    assert recipe_layout.export() == str(t.out).rstrip()
    t.run(f"cache path foo/1.0#{recipe_revision} --folder=export_source")
    assert recipe_layout.export_sources() == str(t.out).rstrip()
    t.run(f"cache path foo/1.0#{recipe_revision} --folder=source")
    assert recipe_layout.source() == str(t.out).rstrip()

    # Basic package paths, without specifying revision
    t.run(f"cache path foo/1.0:{pref.package_id}")
    assert pkg_layout.package() == str(t.out).rstrip()
    t.run(f"cache path foo/1.0:{pref.package_id} --folder=build")
    assert pkg_layout.build() == str(t.out).rstrip()

    # Basic package paths, with recipe-revision
    t.run(f"cache path foo/1.0#{recipe_revision}:{pref.package_id}")
    assert pkg_layout.package() == str(t.out).rstrip()
    t.run(f"cache path foo/1.0#{recipe_revision}:{pref.package_id}#latest")
    assert pkg_layout.package() == str(t.out).rstrip()
    t.run(f"cache path foo/1.0#{recipe_revision}:{pref.package_id} --folder=build")
    assert pkg_layout.build() == str(t.out).rstrip()

    # Basic package paths, with both revisions
    t.run(f"cache path foo/1.0#{recipe_revision}:{pref.package_id}#{pref.revision}")
    assert pkg_layout.package() == str(t.out).rstrip()
    t.run(f"cache path foo/1.0#{recipe_revision}:{pref.package_id}#{pref.revision} --folder=build")
    assert pkg_layout.build() == str(t.out).rstrip()


def test_cache_path_exist_errors(created_package):
    t, recipe_layout, pkg_layout = created_package
    recipe_revision = recipe_layout.reference.revision
    pref = pkg_layout.reference

    t.run("cache path nonexist/1.0", assert_error=True)
    assert "ERROR: Recipe 'nonexist/1.0' not found" in t.out

    t.run("cache path nonexist/1.0#rev", assert_error=True)
    assert "ERROR: Recipe 'nonexist/1.0#rev' not found" in t.out

    t.run("cache path foo/1.0#rev", assert_error=True)
    # TODO: Improve this error message
    assert "ERROR: Recipe 'foo/1.0#rev' not found" in t.out

    t.run(f"cache path foo/1.0:pid1", assert_error=True)
    assert f"ERROR: 'foo/1.0#{recipe_revision}:pid1' not found in cache" in t.out

    t.run(f"cache path foo/1.0#{recipe_revision}:pid1", assert_error=True)
    assert f"ERROR: 'foo/1.0#{recipe_revision}:pid1' not found in cache" in t.out

    t.run(f"cache path foo/1.0#{recipe_revision}:{pref.package_id}#rev2", assert_error=True)
    assert f"ERROR: No entry for package 'foo/1.0#{recipe_revision}:{pref.package_id}#rev2" in t.out


def test_cache_path_arg_errors():
    t = TestClient()
    # build, cannot obtain build without pref
    t.run("cache path foo/1.0 --folder build", assert_error=True)
    assert "ERROR: '--folder build' requires a valid package reference" in t.out

    # Invalid reference
    t.run("cache path patata", assert_error=True)
    assert "ERROR: patata is not a valid recipe reference" in t.out

    # source, cannot obtain build without pref
    t.run("cache path foo/1.0:pid --folder source", assert_error=True)
    assert "ERROR: '--folder source' requires a recipe reference" in t.out


def test_cache_path_does_not_exist_folder():
    client = TestClient(default_server_user=True)
    conanfile = GenConanfile()
    client.save({"conanfile.py": conanfile})
    client.run("create . --name=mypkg --version=0.1")
    pref = client.created_package_reference("mypkg/0.1")
    client.run("upload * --confirm -r default")
    client.run("remove * -c")

    client.run(f"install --requires mypkg/0.1")
    client.run(f"cache path {pref} --folder build", assert_error=True)
    assert f"ERROR: 'build' folder does not exist for the reference {pref}" in client.out


def test_cache_path_output_json():
    client = TestClient()
    conanfile = GenConanfile("mypkg", "0.1")
    client.save({"conanfile.py": conanfile})
    client.run("export .")
    layout = client.exported_layout()
    client.run("cache path mypkg/0.1 --format=json")
    output = json.loads(client.stdout)
    assert output == {"cache_path": os.path.join(layout.base_folder, "e")}


class TestCacheRef:

    def test_cache_path(self, created_package):
        t, recipe_layout, pkg_layout = created_package

        t.run(f'cache ref "{os.path.dirname(recipe_layout.export())}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

        t.run(f'cache ref "{recipe_layout.export()}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

        t.run(f'cache ref "{recipe_layout.source()}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

        t.run(f'cache ref "{os.path.dirname(pkg_layout.package())}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

        t.run(f'cache ref "{pkg_layout.build()}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

        t.run(f'cache ref "{pkg_layout.package()}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

    def test_downloaded_paths(self):
        t = TestClient(light=True, default_server_user=True)
        t.save({"conanfile.py": GenConanfile()})
        t.run("create . --name foo --version 1.0")
        t.run("upload * -c -r=default")
        t.run("remove * -c")
        t.run("install --requires=foo/1.0")
        ref = RecipeReference.loads("foo/1.0#4d670581ccb765839f2239cc8dff8fbd")
        pref = PkgReference(ref, "da39a3ee5e6b4b0d3255bfef95601890afd80709")
        recipe_layout = t.get_latest_ref_layout(ref)
        pkg_layout = t.get_latest_pkg_layout(pref)

        t.run(f'cache ref "{os.path.dirname(recipe_layout.export())}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

        t.run(f'cache ref "{recipe_layout.export()}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

        t.run(f'cache ref "{os.path.dirname(pkg_layout.package())}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

        t.run(f'cache ref "{pkg_layout.package()}"')
        assert f"foo/1.0#{recipe_layout.reference.revision}" in t.out

    def test_errors(self):
        t = TestClient(light=True)
        t.run('cache ref "/some/non/existing/path"', assert_error=True)
        assert "ERROR: Reference for this path not found in cache" in t.out

        if platform.system() == "Windows":
            t.run("cache ref J:/not/path", assert_error=True)
            assert "ERROR: Invalid path: J:/not/path" in t.out

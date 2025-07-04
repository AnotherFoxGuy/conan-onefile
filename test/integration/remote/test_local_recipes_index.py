import json
import os
import textwrap

import pytest

from conan.test.assets.genconanfile import GenConanfile
from conan.test.utils.test_files import temp_folder
from conan.test.utils.tools import TestClient
from conan.internal.util.files import mkdir, save, save_files


@pytest.fixture(scope="module")
def c3i_folder():
    folder = temp_folder()
    recipes_folder = os.path.join(folder, "recipes")
    zlib_config = textwrap.dedent("""
        versions:
          "1.2.8":
            folder: all
          "1.2.11":
            folder: all
        """)
    zlib = textwrap.dedent("""
        from conan import ConanFile
        from conan.tools.files import load
        class Zlib(ConanFile):
            name = "zlib"
            exports_sources = "*"
            def build(self):
                self.output.info(f"CONANDATA: {self.conan_data}")
                self.output.info(f"BUILDING: {load(self, 'file.h')}")
            """)
    save_files(recipes_folder,
               {"zlib/config.yml": zlib_config,
                "zlib/all/conanfile.py": zlib,
                "zlib/all/conandata.yml": "",
                "zlib/all/file.h": "//myheader"})
    mkdir(os.path.join(recipes_folder, "openssl", "1.X"))
    mkdir(os.path.join(recipes_folder, "openssl", "2.X"))
    save(os.path.join(recipes_folder, "openssl", "config.yml"), textwrap.dedent("""
        versions:
          "1.0":
            folder: "1.X"
          "1.1":
            folder: "1.X"
          "2.0":
            folder: "2.X"
        """))
    save(os.path.join(recipes_folder, "openssl", "1.X", "conanfile.py"),
         str(GenConanfile().with_require("zlib/1.2.8")))
    save(os.path.join(recipes_folder, "openssl", "2.X", "conanfile.py"),
         str(GenConanfile().with_require("zlib/1.2.11")))
    mkdir(os.path.join(recipes_folder, "libcurl", "all"))
    save(os.path.join(recipes_folder, "libcurl", "config.yml"), textwrap.dedent("""
            versions:
              "1.0":
                folder: "all"
            """))
    save(os.path.join(recipes_folder, "libcurl", "all", "conanfile.py"),
         str(GenConanfile().with_require("openssl/2.0")))

    save(os.path.join(recipes_folder, ".DS_Store", "foo"), "")

    return folder


class TestSearchList:
    def test_basic_search(self, c3i_folder):
        client = TestClient(light=True)
        client.run(f"remote add local '{c3i_folder}' --type=local-recipes-index")  # Keep --type test
        assert "WARN" not in client.out  # Make sure it does not complain about url
        client.run("search *")
        assert textwrap.dedent("""\
            local
              libcurl
                libcurl/1.0
              openssl
                openssl/1.0
                openssl/1.1
                openssl/2.0
              zlib
                zlib/1.2.8
                zlib/1.2.11
            """) in client.out

    def test_list_refs(self, c3i_folder):
        client = TestClient(light=True)
        client.run(f"remote add local '{c3i_folder}'")
        client.run("list *#* -r=local --format=json")
        listjson = json.loads(client.stdout)
        revs = listjson["local"]["libcurl/1.0"]["revisions"]
        assert len(revs) == 1 and "e468388f0e4e098d5b62ad68979aebd5" in revs
        revs = listjson["local"]["openssl/1.0"]["revisions"]
        assert len(revs) == 1 and "b35ffb31b6d5a9d8af39f5de3cf4fd63" in revs
        revs = listjson["local"]["openssl/1.1"]["revisions"]
        assert len(revs) == 1 and "b35ffb31b6d5a9d8af39f5de3cf4fd63" in revs
        revs = listjson["local"]["openssl/2.0"]["revisions"]
        assert len(revs) == 1 and "e50e871efca149f160fa6354c8534449" in revs
        revs = listjson["local"]["zlib/1.2.8"]["revisions"]
        assert len(revs) == 1 and "6f5c31bb1219e9393743d1fbf2ee1b52" in revs
        revs = listjson["local"]["zlib/1.2.11"]["revisions"]
        assert len(revs) == 1 and "6f5c31bb1219e9393743d1fbf2ee1b52" in revs

    def test_list_revisions_notfound(self, c3i_folder):
        client = TestClient(light=True)
        client.run(f"remote add local '{c3i_folder}'")
        client.run("list potato/1.0#* -r=local")
        # More like remotes than cache
        assert "ERROR: Recipe not found: 'potato/1.0'"

    def test_list_rrevs(self, c3i_folder):
        client = TestClient(light=True)
        client.run(f"remote add local '{c3i_folder}'")
        client.run("list libcurl/1.0#* -r=local --format=json")
        listjson = json.loads(client.stdout)
        revs = listjson["local"]["libcurl/1.0"]["revisions"]
        assert len(revs) == 1 and "e468388f0e4e098d5b62ad68979aebd5" in revs

    def test_list_binaries(self, c3i_folder):
        client = TestClient(light=True)
        client.run(f"remote add local '{c3i_folder}'")
        client.run("list libcurl/1.0:* -r=local --format=json")
        listjson = json.loads(client.stdout)
        rev = listjson["local"]["libcurl/1.0"]["revisions"]["e468388f0e4e098d5b62ad68979aebd5"]
        assert rev["packages"] == {}


class TestInstall:
    def test_install(self, c3i_folder):
        c = TestClient(light=True)
        c.run(f"remote add local '{c3i_folder}'")
        c.run("install --requires=libcurl/1.0 --build missing")
        assert "zlib/1.2.11: CONANDATA: {}" in c.out
        assert "zlib/1.2.11: BUILDING: //myheader" in c.out
        bins = {"libcurl/1.0": ("aa69c1e1e39a18fe70001688213dbb7ada95f890", "Build"),
                "openssl/2.0": ("594ed0eb2e9dfcc60607438924c35871514e6c2a", "Build"),
                "zlib/1.2.11": ("da39a3ee5e6b4b0d3255bfef95601890afd80709", "Build")}
        c.assert_listed_binary(bins)

        # Already installed in the cache
        c.run("install --requires=libcurl/1.0")
        assert "zlib/1.2.11: Already installed!" in c.out
        assert "openssl/2.0: Already installed!" in c.out
        assert "libcurl/1.0: Already installed!" in c.out

        # Update doesn't fail, but doesn't update revision time
        c.run("install --requires libcurl/1.0 --update")
        bins = {"libcurl/1.0": "Cache (Updated date) (local)",
                "openssl/2.0": "Cache (Updated date) (local)",
                "zlib/1.2.11": "Cache (Updated date) (local)"}

        c.assert_listed_require(bins)
        assert "zlib/1.2.11: Already installed!" in c.out
        assert "openssl/2.0: Already installed!" in c.out
        assert "libcurl/1.0: Already installed!" in c.out

        # Doing local changes creates a new revision
        # New recipe revision for the zlib library
        save(os.path.join(c3i_folder, "recipes", "zlib", "all", "conanfile.py"),
             str(GenConanfile()) + "\n")
        c.run("install --requires=libcurl/1.0 --build missing --update")
        # it is updated
        assert "zlib/1.2.11#dd82451a95902c89bb66a2b980c72de5 - Updated (local)" in c.out

    def test_install_with_exported_files(self):
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        boost_config = textwrap.dedent("""
            versions:
              "1.0":
                folder: all
            """)
        boost = textwrap.dedent("""
            import os
            from conan.tools.files import load
            from conan import ConanFile
            class Boost(ConanFile):
                name = "boost"
                version = "1.0"
                exports = "*"
                def source(self):
                    myfile = os.path.join(self.recipe_folder, "dependencies", "myfile.json")
                    self.output.info(load(self, myfile))
                """)
        deps_json = '{"potato": 42}'
        save_files(recipes_folder,
                   {"boost/config.yml": boost_config,
                    "boost/all/conanfile.py": boost,
                    "boost/all/dependencies/myfile.json": deps_json})
        c = TestClient(light=True)
        c.run(f"remote add local '{folder}'")
        c.run("install --requires=boost/[*] --build missing")
        assert 'boost/1.0: {"potato": 42}' in c.out

    def test_trim_conandata_yaml(self):
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        config = textwrap.dedent("""
            versions:
              "1.0":
                folder: all
            """)
        conandata = textwrap.dedent("""\
            sources:
              "1.0":
                url:
                sha256: "ff0ba4c292013dbc27530b3a81e1f9a813cd39de01ca5e0f8bf355702efa593e"
            patches:
              "1.0":
                - patch_file: "patches/1.3/0001-fix-cmake.patch"
            """)
        save_files(recipes_folder,
                   {"pkg/config.yml": config,
                    "pkg/all/conanfile.py": str(GenConanfile("pkg")),
                    "pkg/all/conandata.yml": conandata})
        c = TestClient(light=True)
        c.run(f"remote add local '{folder}'")
        c.run("install --requires=pkg/1.0 --build missing -vvv")
        assert "pkg/1.0#86b609916bbdfe63c579f034ad0edfe7" in c.out

        # User modifies conandata.yml to add new version
        new_conandata = textwrap.dedent("""\
            sources:
              "1.0":
                url:
                sha256: "ff0ba4c292013dbc27530b3a81e1f9a813cd39de01ca5e0f8bf355702efa593e"
              "1.1":
                url:
            patches:
              "1.0":
                - patch_file: "patches/1.3/0001-fix-cmake.patch"
            """)
        save_files(recipes_folder, {"pkg/all/conandata.yml": new_conandata})
        c.run("install --requires=pkg/1.0 --build missing --update -vvv")
        assert "pkg/1.0#86b609916bbdfe63c579f034ad0edfe7" in c.out

    def test_export_patches(self):
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        zlib_config = textwrap.dedent("""
            versions:
              "0.1":
                folder: all
            """)
        zlib = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import export_conandata_patches, apply_conandata_patches
            class Zlib(ConanFile):
                name = "zlib"
                exports_sources = "*.cpp"
                def export_sources(self):
                    export_conandata_patches(self)

                def source(self):
                    apply_conandata_patches(self)
                    """)
        conandata_yml = textwrap.dedent("""\
            versions:
              "0.1":
            patches:
              "0.1":
                - patch_file: "patches/patch1"
                    """)
        patch = textwrap.dedent("""\
            --- a/main.cpp
            +++ b/main.cpp
            @@ -0,0 +1 @@
            +hello
            """)
        save_files(recipes_folder,
                   {"zlib/config.yml": zlib_config,
                    "zlib/all/conanfile.py": zlib,
                    "zlib/all/conandata.yml": conandata_yml,
                    "zlib/all/patches/patch1": patch,
                    "zlib/all/main.cpp": "\n"})
        client = TestClient(light=True)
        client.run(f"remote add local '{folder}'")
        client.run("install --requires=zlib/0.1 --build=missing -vv")
        assert "zlib/0.1: Copied 1 file: patch1" in client.out
        assert "zlib/0.1: Apply patch (file): patches/patch1" in client.out

    def test_export_user_channel(self):
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        zlib_config = textwrap.dedent("""
            versions:
              "0.1":
                folder: all
            """)
        zlib = GenConanfile("zlib").with_class_attribute("user='myuser'")\
                                   .with_class_attribute("channel='mychannel'")
        conandata_yml = textwrap.dedent("""\
            versions:
              "0.1":
            """)
        save_files(recipes_folder, {"zlib/config.yml": zlib_config,
                                    "zlib/all/conanfile.py": str(zlib),
                                    "zlib/all/conandata.yml": conandata_yml})
        client = TestClient()
        client.run(f"remote add local '{folder}'")
        client.run("install --requires=zlib/0.1@myuser/mychannel --build=missing")
        assert "zlib/0.1@myuser/mychannel:" in client.out
        client.run("list * -r=local")
        assert "zlib/0.1@myuser/mychannel" in client.out


class TestRestrictedOperations:
    def test_upload(self):
        folder = temp_folder()
        c3i_folder = os.path.join(folder, "recipes")
        mkdir(c3i_folder)
        c = TestClient(light=True)
        c.run(f"remote add local '{c3i_folder}'")
        c.save({"conanfile.py": GenConanfile("pkg", "0.1")})
        c.run("create .")
        c.run("upload pkg/0.1 -r=local", assert_error=True)
        assert "ERROR: Remote local-recipes-index 'local' doesn't support upload" in c.out


class TestErrorsUx:
    def test_errors(self):
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        zlib_config = textwrap.dedent("""
            versions:
              "1.2.11":
                folder: all
            """)
        zlib = textwrap.dedent("""
            class Zlib(ConanFile):
                name = "zlib"
                """)
        save_files(recipes_folder,
                   {"zlib/config.yml": zlib_config,
                    "zlib/all/conanfile.py": zlib})
        c = TestClient(light=True)
        c.run(f"remote add local '{folder}'")
        c.run("install --requires=zlib/[*] --build missing", assert_error=True)
        assert "NameError: name 'ConanFile' is not defined" in c.out

    def test_require_revision(self):
        # https://github.com/conan-io/conan/issues/17814
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        zlib_config = textwrap.dedent("""
           versions:
             "1.2.11":
               folder: all
           """)
        save_files(recipes_folder,
                   {"zlib/config.yml": zlib_config,
                    "zlib/all/conanfile.py": str(GenConanfile("zlib"))})
        c = TestClient(light=True)
        c.run(f"remote add local '{folder}'")
        c.run("install --requires=zlib/1.2.11#rev1", assert_error=True)
        assert "A specific revision 'zlib/1.2.11#rev1' was requested" in c.out

    def test_no_user_channel(self):
        # https://github.com/conan-io/conan/issues/18142
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        zlib_config = textwrap.dedent("""
          versions:
            "0.1":
              folder: all
          """)
        zlib = GenConanfile("zlib")
        conandata_yml = textwrap.dedent("""\
          versions:
            "0.1":
          """)
        save_files(recipes_folder, {"zlib/config.yml": zlib_config,
                                    "zlib/all/conanfile.py": str(zlib),
                                    "zlib/all/conandata.yml": conandata_yml})
        c = TestClient()
        c.run(f"remote add local '{folder}'")
        c.run("install --requires=zlib/0.1@myuser/mychannel", assert_error=True)
        assert "ERROR: Package 'zlib/0.1@myuser/mychannel' not resolved" in c.out

        c = TestClient(default_server_user=True)
        c.save({"conanfile.py": GenConanfile("zlib", "0.1")})
        c.run("create . --user=myuser --channel=mychannel")
        c.run("upload * -r=default -c")
        c.run(f"remote add local '{folder}' --index=0")
        c.run("install --requires=zlib/0.1@myuser/mychannel")
        c.assert_listed_require({"zlib/0.1@myuser/mychannel": "Cache"})

        # Force resolving in remotes
        c.run("remove * -c")
        c.run("install --requires=zlib/0.1@myuser/mychannel")
        c.assert_listed_require({"zlib/0.1@myuser/mychannel": "Downloaded (default)"})

    def test_errors_missing_folder(self):
        folder = temp_folder()
        repo = os.path.join(folder, "repo")
        mkdir(repo)
        c = TestClient(light=True)
        c.run(f"remote add local '{repo}'")
        # shutil.rmtree(repo)
        c.run("install --requires=zlib/[*] --build missing", assert_error=True)
        assert "Cannot connect to 'local-recipes-index' repository, missing 'recipes'" in c.out


class TestPythonRequires:
    @pytest.fixture(scope="class")
    def c3i_pyrequires_folder(self):
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        config = textwrap.dedent("""
            versions:
              "1.0":
                folder: all
            """)
        pkg = str(GenConanfile("pkg").with_python_requires("pyreq/1.0"))
        save_files(recipes_folder,
                   {"pkg/config.yml": config,
                    "pkg/all/conanfile.py": pkg,
                    "pyreq/config.yml": config,
                    "pyreq/all/conanfile.py": str(GenConanfile("pyreq", "1.0"))})
        return folder

    def test_install(self, c3i_pyrequires_folder):
        c = TestClient(light=True)
        c.run(f"remote add local '{c3i_pyrequires_folder}'")
        c.run("list * -r=local")
        assert "pyreq/1.0" in c.out
        assert "pkg/1.0" in c.out
        c.run("install --requires=pkg/1.0 --build missing -vvv")
        assert "pyreq/1.0#a0d63ca853edefa33582a24a1bb3c75f - Downloaded (local)" in c.out
        assert "pkg/1.0: Created package" in c.out


class TestUserChannel:
    @pytest.fixture(scope="class")
    def c3i_user_channel_folder(self):
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        config = textwrap.dedent("""
                versions:
                  "1.0":
                    folder: all
                  "2.0":
                    folder: other
                """)
        pkg = str(GenConanfile("pkg").with_class_attribute("user='myuser'")
                                     .with_class_attribute("channel='mychannel'"))
        save_files(recipes_folder,
                   {"pkg/config.yml": config,
                    "pkg/all/conanfile.py": pkg,
                    "pkg/other/conanfile.py": str(GenConanfile("pkg"))})
        return folder

    def test_user_channel_requirement(self, c3i_user_channel_folder):
        tc = TestClient(light=True)
        tc.run(f"remote add local '{c3i_user_channel_folder}'")
        tc.run("graph info --requires=pkg/[*]@myuser/mychannel")
        assert "Version range '*' from requirement 'pkg/[*]@myuser/mychannel'" not in tc.out
        assert "pkg/[*]@myuser/mychannel: pkg/1.0@myuser/mychannel" in tc.out
        assert "pkg/1.0@myuser/mychannel#0b23a5938afb0457079e41aac8991595 - Downloaded (local)" in tc.out

    @pytest.mark.parametrize("user_channel", ["@foo/bar", "@foo"])
    def test_user_channel_requirement_no_match(self, c3i_user_channel_folder, user_channel):
        tc = TestClient(light=True)
        tc.run(f"remote add local '{c3i_user_channel_folder}'")
        tc.run(f"graph info --requires=pkg/[*]{user_channel}", assert_error=True)
        assert f"Version range '*' from requirement 'pkg/[*]{user_channel}' required by 'None' could not be resolved." in tc.out

    def test_user_channel_requirement_only_at(self, c3i_user_channel_folder):
        tc = TestClient(light=True)
        tc.run(f"remote add local '{c3i_user_channel_folder}'")
        tc.run(f"graph info --requires=pkg/[*]@")
        assert f"pkg/[*]: pkg/2.0" in tc.out

        tc.run(f"graph info --requires=pkg/[<2]@", assert_error=True)
        assert f" Package 'pkg/[<2]' not resolved" in tc.out

        tc.run(f"graph info --requires=pkg/[<2]", assert_error=True)
        assert f" Package 'pkg/[<2]' not resolved" in tc.out


class TestResetRemote:
    def test_resetting_remote_error(self):
        # https://github.com/conan-io/conan/issues/18371
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        zlib_config = textwrap.dedent("""
            versions:
              "1.2.11":
                folder: all
            """)
        zlib = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import load
            class Zlib(ConanFile):
                name = "zlib"
                exports_sources = "*"
                """)
        save_files(recipes_folder,
                   {"zlib/config.yml": zlib_config,
                    "zlib/all/conanfile.py": zlib,
                    "zlib/all/conandata.yml": "",
                    "zlib/all/file.h": "//myheader"})

        client = TestClient(light=True)
        client.run(f"remote add local '{folder}'")
        client.run("graph info --requires=zlib/[*]")

        # This second --force destroys the previous remote database
        client.run(f"remote add local '{folder}' --force")
        client.run("install --requires=zlib/[*] --build=missing")
        # It doesn't fail or crash anymore

    def test_changing_revisions(self):
        # https://github.com/conan-io/conan/issues/18371
        folder = temp_folder()
        recipes_folder = os.path.join(folder, "recipes")
        zlib_config = textwrap.dedent("""
            versions:
              "1.2.11":
                folder: all
            """)
        zlib = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import load
            class Zlib(ConanFile):
                name = "zlib"
                exports_sources = "*"
                def build(self):
                    self.output.info(f"BUILDING: {load(self, 'file.h')}")
            """)
        save_files(recipes_folder,
                   {"zlib/config.yml": zlib_config,
                    "zlib/all/conanfile.py": zlib,
                    "zlib/all/conandata.yml": "",
                    "zlib/all/file.h": "//myheader"})

        c = TestClient(light=True)
        c.run(f"remote add local '{folder}'")
        c.run("graph info --requires=zlib/[*]")
        rev1 = "bd69839cb4c933336fceb32302aaf91f"

        # Modify zlib code
        save_files(recipes_folder, {"zlib/all/file.h": "//myheader 222"})
        c.run("graph info --requires=zlib/[*] --update")
        rev2 = "c912566276abca17d2fb5fb6fc957852"

        c.run(f"remote add local '{folder}' --force")
        c.run(f"install --requires=zlib/1.2.11#{rev2} --build=missing")  # works
        c.run(f"install --requires=zlib/1.2.11#{rev1} --build=missing", assert_error=True)
        assert ("WARN: A specific revision 'zlib/1.2.11#bd69839cb4c933336fceb32302aaf91f' was "
                "requested, but it doesn't match the current available revision in source") in c.out
        assert ("ERROR: The 'zlib/1.2.11' package has 'exports_sources' but sources "
                "not found in local cache") in c.out

import json
import os
import textwrap

import pytest

from conan.test.assets.genconanfile import GenConanfile
from conan.test.utils.tools import TestClient


def test_info_build_order():
    c = TestClient()
    c.save({"dep/conanfile.py": GenConanfile(),
            "pkg/conanfile.py": GenConanfile().with_requires("dep/0.1"),
            "consumer/conanfile.txt": "[requires]\npkg/0.1"})
    c.run("export dep --name=dep --version=0.1")
    c.run("export pkg --name=pkg --version=0.1")
    c.run("graph build-order consumer --build=missing --format=json")
    bo_json = json.loads(c.stdout)

    result = [
        [
            {
                "ref": "dep/0.1#4d670581ccb765839f2239cc8dff8fbd",
                "depends": [],
                "packages": [[
                    {
                        "package_id": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                        'prev': None,
                        'filenames': [],
                        'info': {},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=dep/0.1 --build=dep/0.1',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            }
        ],
        [
            {
                "ref": "pkg/0.1#1ac8dd17c0f9f420935abd3b6a8fa032",
                "depends": [
                    "dep/0.1#4d670581ccb765839f2239cc8dff8fbd"
                ],
                "packages": [[
                    {
                        "package_id": "59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                        'prev': None,
                        'filenames': [],
                        'info': {'requires': ['dep/0.1']},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=pkg/0.1 --build=pkg/0.1',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            }
        ]
    ]

    assert bo_json == result

    c.run("graph build-order consumer --order-by=recipe --build=missing --format=json")
    bo_json = json.loads(c.stdout)
    assert bo_json["order_by"] == "recipe"
    assert bo_json["order"] == result

    c.run("graph build-order consumer --build=missing --order-by=recipe --reduce --format=json")
    bo_json = json.loads(c.stdout)
    assert bo_json["order_by"] == "recipe"
    assert bo_json["order"] == result

    # test html format
    c.run("graph build-order consumer --build=missing --format=html")
    assert "<body>" in c.stdout
    c.run("graph build-order consumer --order-by=recipe --build=missing --format=html")
    assert "<body>" in c.stdout
    c.run("graph build-order consumer --order-by=configuration --build=missing --format=html")
    assert "<body>" in c.stdout


def test_info_build_order_configuration():
    c = TestClient()
    c.save({"dep/conanfile.py": GenConanfile(),
            "pkg/conanfile.py": GenConanfile().with_requires("dep/0.1"),
            "consumer/conanfile.txt": "[requires]\npkg/0.1"})
    c.run("export dep --name=dep --version=0.1")
    c.run("export pkg --name=pkg --version=0.1")
    c.run("graph build-order consumer --build=missing --order=configuration --format=json")
    bo_json = json.loads(c.stdout)
    assert bo_json["order_by"] == "configuration"

    result = [
        [
            {
                "ref": "dep/0.1#4d670581ccb765839f2239cc8dff8fbd",
                "pref": "dep/0.1#4d670581ccb765839f2239cc8dff8fbd:da39a3ee5e6b4b0d3255bfef95601890afd80709",
                "depends": [],
                "package_id": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                'prev': None,
                'filenames': [],
                'info': {},
                "context": "host",
                "binary": "Build",
                'build_args': '--requires=dep/0.1 --build=dep/0.1',
                "options": [],
                "overrides": {}
            }
        ],
        [
            {
                "ref": "pkg/0.1#1ac8dd17c0f9f420935abd3b6a8fa032",
                "pref": "pkg/0.1#1ac8dd17c0f9f420935abd3b6a8fa032:59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                "depends": [
                    "dep/0.1#4d670581ccb765839f2239cc8dff8fbd:da39a3ee5e6b4b0d3255bfef95601890afd80709"
                ],
                "package_id": "59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                'prev': None,
                'filenames': [],
                'info': {'requires': ['dep/0.1']},
                "context": "host",
                "binary": "Build",
                'build_args': '--requires=pkg/0.1 --build=pkg/0.1',
                "options": [],
                "overrides": {}

            }
        ]
    ]

    assert bo_json["order"] == result

    c.run("graph build-order consumer --build=missing --order=configuration --reduce --format=json")
    bo_json = json.loads(c.stdout)
    assert bo_json["order"] == result


def test_info_build_order_configuration_text_formatter():
    c = TestClient()
    c.save({"dep/conanfile.py": GenConanfile(),
            "pkg/conanfile.py": GenConanfile().with_requires("dep/0.1"),
            "consumer/conanfile.txt": "[requires]\npkg/0.1"})
    c.run("export dep --name=dep --version=0.1")
    c.run("export pkg --name=pkg --version=0.1")
    c.run("graph build-order consumer --build=missing --order=configuration --format=text")
    assert textwrap.dedent("""\
    ======== Computing the build order ========
    dep/0.1#4d670581ccb765839f2239cc8dff8fbd:da39a3ee5e6b4b0d3255bfef95601890afd80709 - Build
    pkg/0.1#1ac8dd17c0f9f420935abd3b6a8fa032:59205ba5b14b8f4ebc216a6c51a89553021e82c1 - Build
    """) in c.out


def test_info_build_order_build_require():
    c = TestClient()
    c.save({"dep/conanfile.py": GenConanfile(),
            "pkg/conanfile.py": GenConanfile().with_tool_requires("dep/0.1"),
            "consumer/conanfile.txt": "[requires]\npkg/0.1"})
    c.run("export dep --name=dep --version=0.1")
    c.run("export pkg --name=pkg --version=0.1")
    c.run("graph build-order  consumer --build=missing --format=json")
    bo_json = json.loads(c.stdout)
    result = [
        [
            {
                "ref": 'dep/0.1#4d670581ccb765839f2239cc8dff8fbd',
                "depends": [],
                "packages": [[
                    {
                        "package_id": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                        'prev': None,
                        'filenames': [],
                        'info': {},
                        "context": "build",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--tool-requires=dep/0.1 --build=dep/0.1',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            }
        ],
        [
            {
                "ref": "pkg/0.1#b5a40d7314ce57ebdcf8fa31257f3de1",
                "depends": [
                    "dep/0.1#4d670581ccb765839f2239cc8dff8fbd"
                ],
                "packages": [[
                    {
                        "package_id": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                        'prev': None,
                        'filenames': [],
                        'info': {},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=pkg/0.1 --build=pkg/0.1',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            }
        ]
    ]

    assert bo_json == result


def test_info_build_order_options():
    c = TestClient()
    # The normal default_options do NOT propagate to build_requires, it is necessary to use
    # self.requires(..., options=xxx)
    c.save({"tool/conanfile.py": GenConanfile().with_option("myopt", [1, 2, 3]),
            "dep1/conanfile.py": GenConanfile().with_tool_requirement("tool/0.1",
                                                                      options={"myopt": 1}),
            "dep2/conanfile.py": GenConanfile().with_tool_requirement("tool/0.1",
                                                                      options={"myopt": 2}),
            "consumer/conanfile.txt": "[requires]\ndep1/0.1\ndep2/0.1"})
    c.run("export tool --name=tool --version=0.1")
    c.run("export dep1 --name=dep1 --version=0.1")
    c.run("export dep2 --name=dep2 --version=0.1")

    c.run("graph build-order  consumer --build=missing --format=json")
    bo_json = json.loads(c.stdout)
    result = [
        [
            {'ref': 'tool/0.1#b4c19a1357b43877a2019dd2804336a9',
             'depends': [],
             'packages': [[
                 {'package_id': '1124b99dc8cd3c8bbf79121c7bf86ce40c725a40', 'prev': None,
                  'context': 'build', 'depends': [], "overrides": {},
                  'binary': 'Build', 'options': ['tool/0.1:myopt=2'], 'filenames': [],
                  'info': {'options': {'myopt': '2'}},
                  'build_args': '--tool-requires=tool/0.1 --build=tool/0.1 -o:b="tool/0.1:myopt=2"'},
                 {'package_id': 'a9035d84c5880b26c4b44acf70078c9a7dd37412', 'prev': None,
                  'context': 'build', 'depends': [], "overrides": {},
                  'info': {'options': {'myopt': '1'}},
                  'binary': 'Build', 'options': ['tool/0.1:myopt=1'],
                  'filenames': [],
                  'build_args': '--tool-requires=tool/0.1 --build=tool/0.1 -o:b="tool/0.1:myopt=1"'}
             ]]}
        ],
        [
            {'ref': 'dep1/0.1#7f0d80f9cb8c6bab06def7f6fb8f3b86',
             'depends': ['tool/0.1#b4c19a1357b43877a2019dd2804336a9'],
             'packages': [[
                 {'package_id': 'da39a3ee5e6b4b0d3255bfef95601890afd80709', 'prev': None,
                  'context': 'host', 'depends': [], 'binary': 'Build', 'options': [],
                  'filenames': [], 'info': {}, "overrides": {},
                  'build_args': '--requires=dep1/0.1 --build=dep1/0.1'}
             ]]},
            {'ref': 'dep2/0.1#23c789d2b36f0461e52cd6f139f97f5e',
             'depends': ['tool/0.1#b4c19a1357b43877a2019dd2804336a9'],
             'packages': [[
                 {'package_id': 'da39a3ee5e6b4b0d3255bfef95601890afd80709', 'prev': None,
                  'context': 'host', 'depends': [], 'binary': 'Build', 'options': [],
                  'filenames': [], 'info': {}, "overrides": {},
                  'build_args': '--requires=dep2/0.1 --build=dep2/0.1'}
             ]]}
        ]
    ]
    assert bo_json == result


def test_info_build_order_merge_multi_product():
    c = TestClient()
    c.save({"dep/conanfile.py": GenConanfile(),
            "pkg/conanfile.py": GenConanfile().with_requires("dep/0.1"),
            "consumer1/conanfile.txt": "[requires]\npkg/0.1",
            "consumer2/conanfile.txt": "[requires]\npkg/0.2"})
    c.run("export dep --name=dep --version=0.1")
    c.run("export pkg --name=pkg --version=0.1")
    c.run("export pkg --name=pkg --version=0.2")
    c.run("graph build-order consumer1  --build=missing --format=json", redirect_stdout="bo1.json")
    c.run("graph build-order consumer2  --build=missing --format=json", redirect_stdout="bo2.json")
    c.run("graph build-order-merge --file=bo1.json --file=bo2.json --format=json",
          redirect_stdout="bo3.json")

    bo_json = json.loads(c.load("bo3.json"))

    result = [
        [
            {
                "ref": "dep/0.1#4d670581ccb765839f2239cc8dff8fbd",
                "depends": [],
                "packages": [[
                    {
                        "package_id": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                        'prev': None,
                        'filenames': ["bo1", "bo2"],
                        'info': {},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=dep/0.1 --build=dep/0.1',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            }
        ],
        [
            {
                "ref": "pkg/0.1#1ac8dd17c0f9f420935abd3b6a8fa032",
                "depends": [
                    "dep/0.1#4d670581ccb765839f2239cc8dff8fbd"
                ],
                "packages": [[
                    {
                        "package_id": "59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                        'prev': None,
                        'filenames': ["bo1"],
                        'info': {'requires': ['dep/0.1']},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=pkg/0.1 --build=pkg/0.1',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            },
            {
                "ref": "pkg/0.2#1ac8dd17c0f9f420935abd3b6a8fa032",
                "depends": [
                    "dep/0.1#4d670581ccb765839f2239cc8dff8fbd"
                ],
                "packages": [[
                    {
                        "package_id": "59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                        'prev': None,
                        'filenames': ["bo2"],
                        'info': {'requires': ['dep/0.1']},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=pkg/0.2 --build=pkg/0.2',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            }
        ]
    ]

    assert bo_json == result

    # test that html format for build-order-merge generates something
    c.run("graph build-order-merge --file=bo1.json --file=bo2.json --format=html")
    assert "<body>" in c.stdout


def test_info_build_order_merge_multi_product_configurations():
    c = TestClient()
    c.save({"dep/conanfile.py": GenConanfile(),
            "pkg/conanfile.py": GenConanfile().with_requires("dep/0.1"),
            "consumer1/conanfile.txt": "[requires]\npkg/0.1",
            "consumer2/conanfile.txt": "[requires]\npkg/0.2"})
    c.run("export dep --name=dep --version=0.1")
    c.run("export pkg --name=pkg --version=0.1")
    c.run("export pkg --name=pkg --version=0.2")
    c.run("graph build-order consumer1  --build=missing --order=configuration --format=json",
          redirect_stdout="bo1.json")
    c.run("graph build-order consumer2  --build=missing --order=configuration --format=json",
          redirect_stdout="bo2.json")
    c.run("graph build-order-merge --file=bo1.json --file=bo2.json --format=json",
          redirect_stdout="bo3.json")

    bo_json = json.loads(c.load("bo3.json"))
    assert bo_json["order_by"] == "configuration"
    result = [
        [
            {
                "ref": "dep/0.1#4d670581ccb765839f2239cc8dff8fbd",
                "pref": "dep/0.1#4d670581ccb765839f2239cc8dff8fbd:da39a3ee5e6b4b0d3255bfef95601890afd80709",
                "package_id": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                "prev": None,
                "context": "host",
                "binary": "Build",
                "options": [],
                "filenames": [
                    "bo1",
                    "bo2"
                ],
                'info': {},
                "depends": [],
                "overrides": {},
                "build_args": "--requires=dep/0.1 --build=dep/0.1"
            }
        ],
        [
            {
                "ref": "pkg/0.1#1ac8dd17c0f9f420935abd3b6a8fa032",
                "pref": "pkg/0.1#1ac8dd17c0f9f420935abd3b6a8fa032:59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                "package_id": "59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                "prev": None,
                "context": "host",
                "binary": "Build",
                "options": [],
                "filenames": [
                    "bo1"
                ],
                'info': {'requires': ['dep/0.1']},
                "depends": [
                    "dep/0.1#4d670581ccb765839f2239cc8dff8fbd:da39a3ee5e6b4b0d3255bfef95601890afd80709"
                ],
                "overrides": {},
                "build_args": "--requires=pkg/0.1 --build=pkg/0.1"
            },
            {
                "ref": "pkg/0.2#1ac8dd17c0f9f420935abd3b6a8fa032",
                "pref": "pkg/0.2#1ac8dd17c0f9f420935abd3b6a8fa032:59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                "package_id": "59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                "prev": None,
                "context": "host",
                "binary": "Build",
                "options": [],
                "filenames": [
                    "bo2"
                ],
                'info': {'requires': ['dep/0.1']},
                "depends": [
                    "dep/0.1#4d670581ccb765839f2239cc8dff8fbd:da39a3ee5e6b4b0d3255bfef95601890afd80709"
                ],
                "overrides": {},
                "build_args": "--requires=pkg/0.2 --build=pkg/0.2"
            }
        ]
    ]

    assert bo_json["order"] == result


def test_info_build_order_merge_conditionals():
    c = TestClient()
    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class Pkg(ConanFile):
            settings = "os"
            def requirements(self):
                if self.settings.os == "Windows":
                    self.requires("depwin/[>0.0 <1.0]")
                else:
                    self.requires("depnix/[>0.0 <1.0]")
        """)
    c.save({"dep/conanfile.py": GenConanfile(),
            "pkg/conanfile.py": conanfile,
            "consumer/conanfile.txt": "[requires]\npkg/0.1"})
    c.run("export dep --name=depwin --version=0.1")
    c.run("export dep --name=depnix --version=0.1")
    c.run("export pkg --name=pkg --version=0.1")
    c.run("graph build-order consumer --format=json --build=missing -s os=Windows",
          redirect_stdout="bo_win.json")
    c.run("graph build-order consumer --format=json --build=missing -s os=Linux",
          redirect_stdout="bo_nix.json")
    c.run("graph build-order-merge --file=bo_win.json --file=bo_nix.json --format=json",
          redirect_stdout="bo3.json")

    bo_json = json.loads(c.load("bo3.json"))

    result = [
        [
            {
                "ref": "depwin/0.1#4d670581ccb765839f2239cc8dff8fbd",
                "depends": [],
                "packages": [[
                    {
                        "package_id": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                        'prev': None,
                        'filenames': ["bo_win"],
                        'info': {},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=depwin/0.1 --build=depwin/0.1',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            },
            {
                "ref": "depnix/0.1#4d670581ccb765839f2239cc8dff8fbd",
                "depends": [],
                "packages": [[
                    {
                        "package_id": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                        'prev': None,
                        'filenames': ["bo_nix"],
                        'info': {},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=depnix/0.1 --build=depnix/0.1',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            }
        ],
        [
            {
                "ref": "pkg/0.1#b615ac4c7cd16631cd9e924b68596fce",
                "depends": [
                    "depwin/0.1#4d670581ccb765839f2239cc8dff8fbd",
                    "depnix/0.1#4d670581ccb765839f2239cc8dff8fbd"
                ],
                "packages": [[
                    {
                        "package_id": "b23846b9b10455081d89a9dfacd01f7712d04b95",
                        'prev': None,
                        'filenames': ["bo_win"],
                        'info': {'requires': ['depwin/0.1'],
                                 'settings': {'os': 'Windows'}},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=pkg/0.1 --build=pkg/0.1',
                        "options": [],
                        "overrides": {}
                    },
                    {
                        "package_id": "dc29fa55ec82fab6bd820398c7a152ae5f7d4e28",
                        'prev': None,
                        'filenames': ["bo_nix"],
                        'info': {'requires': ['depnix/0.1'],
                                 'settings': {'os': 'Linux'}},
                        "context": "host",
                        'depends': [],
                        "binary": "Build",
                        'build_args': '--requires=pkg/0.1 --build=pkg/0.1',
                        "options": [],
                        "overrides": {}
                    }
                ]]
            }
        ]
    ]

    assert bo_json == result


def test_info_build_order_lockfile_location():
    """ the lockfile should be in the caller cwd
    https://github.com/conan-io/conan/issues/13850
    """
    c = TestClient()
    c.save({"dep/conanfile.py": GenConanfile("dep", "0.1"),
            "pkg/conanfile.py": GenConanfile("pkg", "0.1").with_requires("dep/0.1")})
    c.run("create dep")
    c.run("lock create pkg --lockfile-out=myconan.lock")
    assert os.path.exists(os.path.join(c.current_folder, "myconan.lock"))
    c.run("graph build-order pkg --lockfile=myconan.lock --lockfile-out=myconan2.lock")
    assert os.path.exists(os.path.join(c.current_folder, "myconan2.lock"))


def test_build_order_missing_package_check_error():
    c = TestClient()
    c.save({"dep/conanfile.py": GenConanfile(),
            "pkg/conanfile.py": GenConanfile().with_requires("dep/0.1"),
            "consumer/conanfile.txt": "[requires]\npkg/0.1"})
    c.run("export dep --name=dep --version=0.1")
    c.run("export pkg --name=pkg --version=0.1")

    exit_code = c.run("graph build-order consumer --build='pkg/*' --order=configuration --format=json", assert_error=True)
    bo_json = json.loads(c.stdout)
    assert bo_json["order_by"] == "configuration"
    assert exit_code != 0
    assert "dep/0.1:da39a3ee5e6b4b0d3255bfef95601890afd80709: Missing binary" in c.out

    result = [
        [
            {
                "ref": "dep/0.1#4d670581ccb765839f2239cc8dff8fbd",
                "pref": "dep/0.1#4d670581ccb765839f2239cc8dff8fbd:da39a3ee5e6b4b0d3255bfef95601890afd80709",
                "package_id": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                "prev": None,
                "context": "host",
                "binary": "Missing",
                "options": [],
                "filenames": [],
                'info': {},
                "depends": [],
                "overrides": {},
                "build_args": None,
            }
        ],
        [
            {
                "ref": "pkg/0.1#1ac8dd17c0f9f420935abd3b6a8fa032",
                "pref": "pkg/0.1#1ac8dd17c0f9f420935abd3b6a8fa032:59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                "package_id": "59205ba5b14b8f4ebc216a6c51a89553021e82c1",
                "prev": None,
                "context": "host",
                "binary": "Build",
                "options": [],
                "filenames": [],
                'info': {'requires': ['dep/0.1']},
                "depends": [
                    "dep/0.1#4d670581ccb765839f2239cc8dff8fbd:da39a3ee5e6b4b0d3255bfef95601890afd80709"
                ],
                "overrides": {},
                "build_args": "--requires=pkg/0.1 --build=pkg/0.1",
            }
        ],
    ]

    assert bo_json["order"] == result


def test_info_build_order_broken_recipe():
    # https://github.com/conan-io/conan/issues/14104
    c = TestClient()
    dep = textwrap.dedent("""
        from conan import ConanFile
        from conan.tools.files import replace_in_file
        class Pkg(ConanFile):
            name = "dep"
            version = "0.1"
            def export(self):
                replace_in_file(self, "conanfile.py", "from conan", "from conans")
        """)
    c.save({"conanfile.py": dep})
    c.run("export .")
    c.run("graph build-order --requires=dep/0.1 --format=json", assert_error=True)
    assert "ImportError" in c.out
    assert "It is possible that this recipe is not Conan 2.0 ready" in c.out


class TestBuildOrderReduce:
    @pytest.mark.parametrize("order", ["recipe", "configuration"])
    def test_build_order_reduce(self, order):
        c = TestClient()
        c.save({"liba/conanfile.py": GenConanfile("liba", "0.1"),
                "libb/conanfile.py": GenConanfile("libb", "0.1").with_requires("liba/0.1"),
                "libc/conanfile.py": GenConanfile("libc", "0.1").with_requires("libb/0.1"),
                "consumer/conanfile.txt": "[requires]\nlibc/0.1"})
        c.run("create liba")
        c.run("create libb")
        c.run("create libc")
        c.run("remove liba:* -c")
        c.run("remove libc:* -c")
        c.run(f"graph build-order consumer --order={order} --build=missing --reduce --format=json")
        bo_json = json.loads(c.stdout)
        order_json = bo_json["order"]
        assert len(order_json) == 2  # 2 levels
        level0, level1 = order_json
        assert len(level0) == 1
        assert level0[0]["ref"] == "liba/0.1#a658e7beaaae5d6be0b6f67dcc9859e2"
        # then libc -> directly on liba, no libb involved
        assert len(level1) == 1
        assert level1[0]["ref"] == "libc/0.1#c04c370ad966390e67388565b56f019a"
        depends = "liba/0.1#a658e7beaaae5d6be0b6f67dcc9859e2"
        if order == "configuration":
            depends += ":da39a3ee5e6b4b0d3255bfef95601890afd80709"
        assert level1[0]["depends"] == [depends]

    @pytest.mark.parametrize("order", ["recipe", "configuration"])
    def test_build_order_merge_reduce(self, order):
        c = TestClient()
        c.save({"liba/conanfile.py": GenConanfile("liba", "0.1").with_settings("os"),
                "libb/conanfile.py": GenConanfile("libb", "0.1").with_settings("os")
                                                                .with_requires("liba/0.1"),
                "libc/conanfile.py": GenConanfile("libc", "0.1").with_settings("os")
                                                                .with_requires("libb/0.1"),
                "consumer/conanfile.txt": "[requires]\nlibc/0.1"})
        for _os in ("Windows", "Linux"):
            c.run(f"create liba -s os={_os}")
            c.run(f"create libb -s os={_os}")
            c.run(f"create libc -s os={_os}")

        c.run("remove liba:* -c")
        c.run("remove libc:* -c")
        c.run(f"graph build-order consumer --order={order} --build=missing -s os=Windows "
              "--format=json", redirect_stdout="windows.json")
        c.run(f"graph build-order consumer --order={order} --build=missing -s os=Linux "
              "--format=json", redirect_stdout="linux.json")

        c.run(f"graph build-order-merge --file=windows.json --file=linux.json --reduce "
              "--format=json")
        bo_json = json.loads(c.stdout)
        order_json = bo_json["order"]
        assert len(order_json) == 2  # 2 levels
        level0, level1 = order_json
        if order == "recipe":
            assert len(level0) == 1
            assert level0[0]["ref"] == "liba/0.1#8c6ed89c12ab2ce78b239224bd7cb79e"
            # then libc -> directly on liba, no libb involved
            assert len(level1) == 1
            assert level1[0]["ref"] == "libc/0.1#66db2600b9d6a2a61c9051fcf47da4a3"
            depends = "liba/0.1#8c6ed89c12ab2ce78b239224bd7cb79e"
            assert level1[0]["depends"] == [depends]
        else:
            assert len(level0) == 2
            liba1 = "liba/0.1#8c6ed89c12ab2ce78b239224bd7cb79e:" \
                    "ebec3dc6d7f6b907b3ada0c3d3cdc83613a2b715"
            liba2 = "liba/0.1#8c6ed89c12ab2ce78b239224bd7cb79e:" \
                    "9a4eb3c8701508aa9458b1a73d0633783ecc2270"
            assert level0[0]["pref"] == liba1
            assert level0[1]["pref"] == liba2
            # then libc -> directly on liba, no libb involved
            assert len(level1) == 2
            assert level1[0]["ref"] == "libc/0.1#66db2600b9d6a2a61c9051fcf47da4a3"
            assert level1[0]["depends"] == [liba1]
            assert level1[1]["ref"] == "libc/0.1#66db2600b9d6a2a61c9051fcf47da4a3"
            assert level1[1]["depends"] == [liba2]

    def test_error_reduced(self):
        c = TestClient()
        c.save({"conanfile.py": GenConanfile("liba", "0.1")})
        c.run("graph build-order . --format=json", redirect_stdout="bo1.json")
        c.run("graph build-order . --order-by=recipe --reduce --format=json",
              redirect_stdout="bo2.json")
        c.run(f"graph build-order-merge --file=bo1.json --file=bo2.json", assert_error=True)
        assert "ERROR: Reduced build-order file cannot be merged: bo2.json"
        # different order
        c.run(f"graph build-order-merge --file=bo2.json --file=bo1.json", assert_error=True)
        assert "ERROR: Reduced build-order file cannot be merged: bo2.json"

    def test_error_different_orders(self):
        c = TestClient()
        c.save({"conanfile.py": GenConanfile("liba", "0.1")})
        c.run("graph build-order . --format=json", redirect_stdout="bo1.json")
        c.run("graph build-order . --order-by=recipe --format=json", redirect_stdout="bo2.json")
        c.run("graph build-order . --order-by=configuration --format=json",
              redirect_stdout="bo3.json")
        c.run(f"graph build-order-merge --file=bo1.json --file=bo2.json")
        # Not error
        c.run(f"graph build-order-merge --file=bo1.json --file=bo3.json", assert_error=True)
        assert "ERROR: Cannot merge build-orders of recipe!=configuration" in c.out
        c.run(f"graph build-order-merge --file=bo2.json --file=bo3.json", assert_error=True)
        assert "ERROR: Cannot merge build-orders of recipe!=configuration" in c.out
        # different order
        c.run(f"graph build-order-merge --file=bo3.json --file=bo2.json", assert_error=True)
        assert "ERROR: Cannot merge build-orders of configuration!=recipe" in c.out

    def test_merge_missing_error(self):
        tc = TestClient(light=True)
        tc.save({"dep/conanfile.py": GenConanfile("dep", "1.0")})
        tc.run("export dep")
        tc.run("graph build-order --order=recipe --requires=dep/1.0 --format=json", assert_error=True, redirect_stdout="order.json")
        tc.run("graph build-order-merge --file=order.json --file=order.json --format=json", assert_error=True)
        assert "dep/1.0:da39a3ee5e6b4b0d3255bfef95601890afd80709: Missing binary" in tc.out
        assert "IndexError: list index out of range" not in tc.out

    def test_merge_invalid_error(self):
        tc = TestClient(light=True)
        conanfile = textwrap.dedent("""
        from conan import ConanFile
        from conan.errors import ConanInvalidConfiguration
        class Pkg(ConanFile):
            name = "dep"
            version = "1.0"
            def validate(self):
                raise ConanInvalidConfiguration("This configuration is not valid")
        """)
        tc.save({"dep/conanfile.py": conanfile})
        tc.run("export dep")
        tc.run("graph build-order --order=recipe --requires=dep/1.0 --format=json", assert_error=True, redirect_stdout="order.json")
        tc.run("graph build-order-merge --file=order.json --file=order.json --format=json", assert_error=True)
        assert "dep/1.0:da39a3ee5e6b4b0d3255bfef95601890afd80709: Invalid configuration" in tc.out
        assert "IndexError: list index out of range" not in tc.out

    def test_reduce_should_remove_recipe(self):
        tc = TestClient()
        tc.save({"dep/conanfile.py": GenConanfile("dep", "1.0").with_settings("os")})
        tc.run("export dep")
        tc.run("create dep -s os=Windows")
        tc.run("graph build-order -s os=Windows --build=missing --order=recipe --requires=dep/1.0 "
               "--format=json", redirect_stdout="windows.json")
        tc.run("graph build-order -s os=Linux --build=missing --order=recipe --requires=dep/1.0 "
               "--format=json", redirect_stdout="linux.json")
        tc.run("graph build-order-merge --file=windows.json --file=linux.json --reduce "
               "--format=json")
        order = json.loads(tc.stdout)
        assert order["order"][0][0]["ref"] == "dep/1.0#1674c18bb63f0c9778d2811c21f581a0"
        assert len(order["order"][0][0]["packages"][0]) == 1
        assert order["order"][0][0]["packages"][0][0]["binary"] == "Build"


def test_multi_configuration_profile_args():
    c = TestClient()
    c.save({"pkg/conanfile.py": GenConanfile().with_settings("os"),
            "consumer/conanfile.txt": "[requires]\npkg/0.1",
            "mypr": ""})
    c.run("export pkg --name=pkg --version=0.1")
    args = "-pr=mypr -s:b os=Linux -o:h *:shared=True -c:h user.my:conf=1"
    c.run(f"graph build-order consumer --format=json --build=missing -s os=Windows {args} "
          "--order-by=recipe", redirect_stdout="bo_win.json")
    c.run(f"graph build-order consumer --format=json --build=missing -s os=Linux {args} "
          "--order-by=recipe", redirect_stdout="bo_nix.json")
    c.run("graph build-order-merge --file=bo_win.json --file=bo_nix.json --format=json",
          redirect_stdout="bo3.json")
    bo_json = json.loads(c.load("bo3.json"))
    win = '-pr:h="mypr" -s:h="os=Windows" -o:h="*:shared=True" -c:h="user.my:conf=1" -s:b="os=Linux"'
    nix = '-pr:h="mypr" -s:h="os=Linux" -o:h="*:shared=True" -c:h="user.my:conf=1" -s:b="os=Linux"'
    assert bo_json["profiles"] == {"bo_win": {"args": win}, "bo_nix": {"args": nix}}


def test_build_order_space_in_options():
    tc = TestClient(light=True)
    tc.save({"dep/conanfile.py": GenConanfile("dep", "1.0").with_option("flags", ["ANY", None])
                                                           .with_option("extras", ["ANY", None]),
             "conanfile.txt": textwrap.dedent("""
             [requires]
             dep/1.0

             [options]
             dep/*:flags=define=FOO define=BAR define=BAZ
             dep/*:extras=cxx="yes" gnuext='no'
             """)})

    tc.run("create dep")
    tc.run("graph build-order . --order-by=configuration --build=dep/1.0 -f=json", redirect_stdout="order.json")
    order = json.loads(tc.load("order.json"))
    assert order["order"][0][0]["build_args"] == '''--requires=dep/1.0 --build=dep/1.0 -o="dep/*:extras=cxx="yes" gnuext='no'" -o="dep/*:flags=define=FOO define=BAR define=BAZ"'''


def test_build_order_build_context_compatible():
    c = TestClient()
    foo = textwrap.dedent("""
        from conan import ConanFile
        from conan.tools.build import check_min_cppstd

        class Pkg(ConanFile):
            name = "foo"
            version = "1.0"
            settings = "os", "compiler"
            def validate_build(self):
                check_min_cppstd(self, 17)

            def validate(self):
                check_min_cppstd(self, 14)
        """)
    bar = GenConanfile("bar", "1.0").with_settings("os", "compiler").with_tool_requirement("foo/1.0")

    profile = textwrap.dedent("""
        [settings]
        compiler=gcc
        compiler.cppstd=gnu14
        compiler.libcxx=libstdc++11
        compiler.version=11
        os=Linux
        """)
    c.save({"conanfile_foo.py": foo,
            "conanfile_bar.py": bar,
            "profile": profile})
    c.run("export conanfile_foo.py")
    c.run("export conanfile_bar.py")

    #  "--require/bar.1.0" and "require=foo/1.0" along with `--build=missing` would cause both
    # packages to be built in the host context - with foo being built with cppstd=17
    # (because the default cppstd=14 is not enough) bar requires foo in the "build" context -
    # where cppstd=14 - but it can reuse the one built for cppstd=17
    # (via compatibility plugin)

    # The three approaches are equivalent:
    #  - Using "--build=missing" and forcing  "-s foo/*:compiler.cppstd=17", means, build missing
    #    binaries, and for foo I want the compiler.cppstd=17 binary. This approach could build other
    #    missing binaries too
    #  - Using "--build=compatible:foo/*" and "--build=missing:bar/*" means, build only missing
    #    binary for bar, and for "foo", build a compatible one if the main one is missing. This
    #    approach prevents other packages (not foo/bar) from accidentally being built.
    #  - Last approach, passing both "--build=missing:foo/*" and "--build=compatible:foo/*" is
    #    similar to the other two in final behavior, but the --build=missing:foo avoids doing the
    #    compatibility check for consumption of "foo", and goes directly to the build check

    for approach in ("--build=missing -s foo/*:compiler.cppstd=17",
                     '--build="compatible:foo/*" --build="missing:bar/*"',
                     '--build="missing:foo/*" --build="compatible:foo/*" --build="missing:bar/*"'):
        c.run(f'graph build-order --require=foo/1.0 --require=bar/1.0 -pr:a profile {approach}')
        c.assert_listed_binary({"foo/1.0": ["4e2ae338231ae18d0d43b9e119404d2b2c416758", "Build"],
                                "bar/1.0": ["5e4ffcc1ff33697a4ee96f66f0d2228ec458f25c", "Build"]})
        c.assert_listed_binary({"foo/1.0": ["4e2ae338231ae18d0d43b9e119404d2b2c416758", "Build"]},
                               build=True)


def test_info_build_order_editable():
    c = TestClient()
    c.save({"dep/conanfile.py": GenConanfile("dep", "0.1"),
            "pkg/conanfile.py": GenConanfile("pkg", "0.1").with_requires("dep/0.1"),
            "consumer/conanfile.txt": "[requires]\npkg/0.1"})
    c.run("editable add dep")
    c.run("export pkg")
    
    c.run("graph build-order consumer --build=missing --build=editable -f=json --order-by=recipe")
    bo_json = json.loads(c.stdout)
    pkg = bo_json["order"][0][0]["packages"][0][0]
    assert pkg["binary"] == "EditableBuild"
    assert pkg["build_args"] == "--requires=dep/0.1 --build=dep/0.1"

    c.run("graph build-order consumer --build=missing --build=editable -f=json "
          "--order-by=configuration")
    bo_json = json.loads(c.stdout)
    pkg = bo_json["order"][0][0]
    assert pkg["binary"] == "EditableBuild"
    assert pkg["build_args"] == "--requires=dep/0.1 --build=dep/0.1"

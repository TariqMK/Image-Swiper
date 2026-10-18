# Manual releases

Push the workflow and source to GitHub's default branch first. In **Actions >
Build release > Run workflow**, select the source branch and both required inputs:

- **release_type:** `draft` (default) or `public`.
- **bump:** `major`, `minor` or `patch` (default).

There are no push, pull-request, tag or scheduled triggers. The form is the
pre-build confirmation; the workflow does not pause for a second confirmation.

## Version allocation

The preparation job pages through all authenticated GitHub releases (including
drafts) and repository tags, and compares them with `pyproject.toml`. It takes
the highest numeric major/minor/patch tuple, then applies the selected bump.
Prerelease tags reserve their numeric base too. Unrelated tag names are ignored.

Examples: a highest version of `1.4.8` becomes `2.0.0`, `1.5.0` or `1.4.9`.
A draft `v1.5.0` makes the next patch `v1.5.1`, even if the latest public release
is still `v1.4.8`.

The job commits the new `pyproject.toml` and `image_swiper/version.py` to a release
commit, pushes a `vMAJOR.MINOR.PATCH` tag pointing to it and reserves a draft
release before starting the matrix. The source branch is not changed; the tagged
source and packaged application contain the incremented version. Subsequent runs
use tags/releases so branch version numbers do not cause reuse. Runs are serialized.

Failed builds leave a reserved tag and draft. A new manual run allocates a new
version; do not rerun the preparation job for the same workflow run. The draft is
published only when all platform builds and asset uploads succeed and `public`
was selected. Draft builds remain drafts. Tags are visible even for draft releases
in a public repository; GitHub drafts are not a way to hide tagged source code.

## Downloads

PyInstaller packages the application and Python dependencies on each native runner:

| Target | Runner | Download |
| --- | --- | --- |
| Windows x64 | `windows-2022` | ZIP containing `ImageSwiper/ImageSwiper.exe` and dependencies |
| macOS Apple Silicon | `macos-15`, ARM64 Python, explicit ARM64 assertion | ZIP containing `ImageSwiper.app` |
| Linux x64 | `ubuntu-22.04` | tar.gz containing `ImageSwiper/ImageSwiper` and dependencies |

No Intel macOS or universal macOS build is produced. Extract the complete archive,
keeping its dependencies beside the executable. The muted header label shows the
release version. Each build runs storage/version tests and launches the bundled
executable with `--version` without opening a window.

The builds are not signed/notarized for distribution; macOS uses PyInstaller's
ad-hoc signing. FFmpeg/ffprobe remain optional external dependencies and are not
bundled. Linux requires a graphical desktop and a compatible system (Ubuntu 22.04
or newer is the build baseline, not a guarantee for every distribution).

Windows retains Recycle Bin undo. macOS/Linux send files to native Trash and
require restoring them through the system file manager; in-app undo is disabled.
Frozen applications store private data in:

- Windows: `%LOCALAPPDATA%/ImageSwiper/data/`.
- macOS: `~/Library/Application Support/ImageSwiper/data/`.
- Linux: `$XDG_DATA_HOME/image-swiper/data/`, defaulting to
  `~/.local/share/image-swiper/data/`.

Source runs retain the project's ignored `data/` folder. Personal data is not
included by the build script. Do not add private media as Python package resources.

The workflow uses `GITHUB_TOKEN` with `contents: write` only in the preparation
and release jobs. Repository tag rules must permit the release tag push; no
personal access token or branch-writing permission exception is needed.

References: [GitHub runner architectures](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[manual workflow inputs](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
and [PyInstaller platform packaging](https://pyinstaller.org/en/stable/usage.html).

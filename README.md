# ModDesk

A private notebook for Roblox / Discord moderation work: users, accounts, notes, lookups. Data stays on your computer.

**Use it only for legitimate moderation.** Read the terms inside the app (Settings > Terms). Matches are leads, not proof.

## Install
Download **ModDesk-Setup.exe** from the [Releases](../../releases) page, run it, pick a folder.

## Update
Open ModDesk > Settings > Updates > *Check for updates* (set this repo as `owner/name`).
No reinstall is needed; only `moddesk.py` changes. Re-run the Setup only when the Setup itself changes.

## For the maintainer
1. Set `DEFAULT_UPDATE_REPO = "owner/name"` near the top of `moddesk.py`.
2. Change the code and bump `APP_VERSION`; commit and push to `main`. Everyone's app notices the new version.
3. For a new installer: `git tag v5.0.1 && git push --tags`. GitHub Actions builds `ModDesk-Setup.exe` and attaches it to the release.
   You can also build locally by running `build.bat` (needs Python).

The repo must be **public** for the raw-file update check to work.


# Raises the app version in pubspec.yaml. push_apk.ps1 runs it before every
# build, so no two builds share a version.
#
# The version is MAJOR.MINOR.PATCH, starting at 0.0.1. The first release is 1.0.0.
# How much it rises depends on how many lines of app code changed since the
# last build:
#   fewer than 100 lines      PATCH + 1      0.0.1  -> 0.0.2
#   100 lines or more         MINOR + 1      0.1.34 -> 0.2.0   (PATCH starts again at 0)
# Even a build with no change raises PATCH, so every build is a new version.
#
# The build number (the number after "+", Android's versionCode) is worked out
# from the version, MAJOR*10000 + MINOR*100 + PATCH, so it always rises too and
# Android always treats a new build as an update. 0.2.0 is build 200.
#
# Lines are counted in apps/mobile, not counting tests, generated files
# (*.g.dart), images, fonts, golden images, pubspec files and the build folder.
# "Changed" means lines added plus lines removed.
#
# The last build is remembered in the local git ref refs/priveo/last-build. It
# is not pushed, so it is per computer.
#
#   powershell -ExecutionPolicy Bypass -File apps\mobile\tool\bump_version.ps1
#   ... bump_version.ps1 -DryRun     (say what it would do, change nothing)
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$mobile = Split-Path -Parent $PSScriptRoot
$repo = (& git -C $mobile rev-parse --show-toplevel).Trim()
$pubspec = Join-Path $mobile "pubspec.yaml"
$ref = "refs/priveo/last-build"

# The app code as it is now, including files that are not committed yet, as a git tree.
function Get-AppTree {
    $index = [System.IO.Path]::GetTempFileName()
    Remove-Item $index
    $old = $env:GIT_INDEX_FILE
    try {
        $env:GIT_INDEX_FILE = $index
        & git -C $repo read-tree HEAD
        & git -C $repo add -A -- apps/mobile
        return (& git -C $repo write-tree).Trim()
    }
    finally {
        $env:GIT_INDEX_FILE = $old
        if (Test-Path $index) { Remove-Item $index -Force }
    }
}

$text = Get-Content $pubspec -Raw
if ($text -notmatch '(?m)^version:\s*(\d+)\.(\d+)\.(\d+)(\+\d+)?\s*$') {
    throw "pubspec.yaml has no version like 0.0.1 or 0.0.1+1."
}
$major = [int]$Matches[1]; $minor = [int]$Matches[2]; $patch = [int]$Matches[3]
$current = "$major.$minor.$patch"

$here = Get-AppTree
$last = (& git -C $repo rev-parse --verify --quiet $ref)
$lines = 0
if ($last) {
    $skip = @(
        ":(exclude)apps/mobile/test", ":(exclude)apps/mobile/build", ":(exclude)apps/mobile/.dart_tool",
        ":(exclude)*.g.dart", ":(exclude)*.png", ":(exclude)*.jpg", ":(exclude)*.ttf", ":(exclude)*.otf",
        ":(exclude)apps/mobile/pubspec.yaml", ":(exclude)apps/mobile/pubspec.lock"
    )
    foreach ($row in (& git -C $repo diff --numstat $last.Trim() $here -- apps/mobile @skip)) {
        $part = $row -split "`t"
        # Binary files show "-" and are not counted.
        if ($part[0] -match '^\d+$' -and $part[1] -match '^\d+$') { $lines += [int]$part[0] + [int]$part[1] }
    }
}

if ($lines -ge 100) { $minor += 1; $patch = 0 } else { $patch += 1 }
$next = "$major.$minor.$patch"
$build = $major * 10000 + $minor * 100 + $patch
$basis = if ($last) { "$lines changed lines since the last build" } else { "no earlier build is remembered, so it counts as a small change" }
Write-Host "Version $current -> $next (build $build): $basis."

if ($DryRun) { Write-Host "Dry run: nothing was changed."; return }

$new = [regex]::Replace($text, '(?m)^version:\s*\d+\.\d+\.\d+(\+\d+)?\s*$', "version: $next+$build")
[System.IO.File]::WriteAllText($pubspec, $new)
# Remember the code as built, with the new version in it (pubspec is not counted anyway).
& git -C $repo update-ref $ref (Get-AppTree)

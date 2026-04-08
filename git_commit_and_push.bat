@echo off
REM Git commit script for PathFinder updates
REM Run this file to commit and push all changes

echo ============================================================
echo PathFinder - Commit and Push Script
echo ============================================================
echo.

echo Step 1: Checking git status...
git status
echo.

echo Step 2: Staging all changes...
git add .
echo.

echo Step 3: Committing changes...
git commit -m "feat: Add Avoid Floods and Avoid Landslides criteria" -m "- Added dfs_no_floods/3 predicate to avoid flooded roads" -m "- Added dfs_no_landslides/3 predicate to avoid landslide roads" -m "- Added query_dfs_no_floods() and query_dfs_no_landslides() bridge methods" -m "- Added both criteria to ALGORITHM_MAP for UI dropdown" -m "- Fixed naming consistency: renamed all DFS predicates to snake_case" -m "  - dfs_noBrokencisterns -> dfs_no_cisterns" -m "  - dfs_nopotholes -> dfs_no_potholes" -m "  - dfs_noLandslides -> dfs_no_landslides" -m "  - dfs_noFloods -> dfs_no_floods" -m "- Updated README.md with new criteria" -m "- Created test_pathfinding.py for verification" -m "- Created CODE_REVIEW.md documenting all changes" -m "" -m "All 10 pathfinding criteria now fully functional." -m "" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
echo.

echo Step 4: Pushing to remote repository...
git push origin main
echo.

echo ============================================================
echo Done! Check output above for any errors.
echo ============================================================
pause

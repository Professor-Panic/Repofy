import subprocess

class Misc:
    def getConflicts(self):
        """Returns a list of filenames that currently have unresolved conflicts"""
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            capture_output=True,
            text=True
        )
        # splits the output into a clean list
        if not result.stdout:
            return []
        return result.stdout.strip().splitlines()
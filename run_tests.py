"""
Convenience runner for the ScanMe test suite.
Run with: python run_tests.py
Or directly: pytest
"""
import sys
import subprocess


def main():
    """Run pytest with coverage and return exit code."""
    cmd = [sys.executable, '-m', 'pytest', '--tb=short', '--cov=app', '--cov-report=term-missing']
    print('Running ScanMe test suite...')
    print(' '.join(cmd))
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())

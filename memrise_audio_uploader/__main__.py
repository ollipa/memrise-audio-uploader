"""Entrypoint for command-line application."""

if __name__ == "__main__":
    try:
        from memrise_audio_uploader.cli import main
    except ImportError:
        # Allow running from source without installing the package
        import os
        import sys
        from pathlib import Path

        dir_path = Path(os.path.dirname(os.path.realpath(__file__))).parent
        sys.path.append(str(dir_path))
        from memrise_audio_uploader.cli import main

    main()

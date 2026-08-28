"""Headless integration test to verify app.py functions, candidate discovery, and document loading."""

from pathlib import Path
from app import discover_candidates, load_text_file


def main():
    print("=" * 80)
    print("           TESTING APP.PY CANDIDATE DISCOVERY & FILE LOADING")
    print("=" * 80)

    sample_dir = Path(__file__).parent / "sample_data"
    candidates = discover_candidates(sample_dir)

    print(f"\nDiscovered Candidates Count: {len(candidates)}")
    for label, folder in candidates.items():
        print(f"\n -> Candidate Label: {label}")
        print(f"    Folder Path:     {folder}")

        resume_path = folder / "resume.txt"
        transcript_path = folder / "transcript.txt"

        assert resume_path.exists(), f"Missing resume.txt in {folder}"
        assert transcript_path.exists(), f"Missing transcript.txt in {folder}"

        r_text = load_text_file(resume_path)
        t_text = load_text_file(transcript_path)

        print(f"    Resume Chars:     {len(r_text)}")
        print(f"    Transcript Chars: {len(t_text)}")

    print("\n[SUCCESS] App flow variable scoping and file resolution verified!")


if __name__ == "__main__":
    main()

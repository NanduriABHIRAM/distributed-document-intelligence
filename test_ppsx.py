from pathlib import Path
from ingestion.loaders import load_document

files = [
    "Computational Mechanics 2 - Lecture 4.ppsx",
    "Computational Mechanics 2 - Lecture 5.ppsx",
    "Modelling, Simulation & Analysis - Lecture 1.pptx.ppsx",
    "Modelling, Simulation & Analysis - Lecture 2.ppsx",
]

def main():
    for filename in files:
        path = Path("data/raw") / filename

        try:
            document = load_document(path)
            print(f"SUCCESS: {filename} | Sections: {len(document.sections)}")
        except Exception as error:
            print(f"FAILED: {filename} | {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
